<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { commentApi, favoriteApi, listApi, movieApi, ratingApi, recommendApi, watchlistApi } from '../api'
import { useUserStore } from '../stores/user'
import { useRatingsStore } from '../stores/ratings'
import MediaPlayer from '../components/MediaPlayer.vue'
import MovieRow from '../components/MovieRow.vue'
import PlaybackFallbackButton from '../components/PlaybackFallbackButton.vue'
import {
  applyLocalTrailerIfExists,
  getCachedTrailer,
  initLocalTrailerIds,
  prefetchTrailer,
} from '../utils/trailerCache'

const LOAD_SLOW_MS = 3000

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const ratingsStore = useRatingsStore()
const movie = ref(null)
const similar = ref([])
const myScore = ref(0)
const savedScore = ref(0)
const playback = ref(null)
const trailer = ref(null)
const loadingPlayback = ref(false)
const loadingTrailer = ref(false)
const showTrailerLoadFallback = ref(false)
const showPlaybackLoadFallback = ref(false)
const activeTab = ref('trailer')
const expandedReviews = ref({})
const userComments = ref([])
const commentText = ref('')
const commentScore = ref(0)
const submittingComment = ref(false)
const pageLoading = ref(true)
const movieWantAutoplay = ref(false)
const moviePlaybackError = ref(false)

const REVIEW_COLLAPSE_CHARS = 120

let trailerSlowTimer = null
let playbackSlowTimer = null

const moviePlaybackSource = computed(() => {
  if (playback.value?.type !== 'mp4' || !playback.value.stream_url) return null
  return { type: 'mp4', embed_url: playback.value.stream_url, stream_url: playback.value.stream_url }
})

const hasLocalMovie = computed(() => playback.value?.source === 'local')

const movieAutoplay = computed(() => movieWantAutoplay.value || route.query.play === '1')

const sourceLabel = computed(() => {
  const map = { local: '正片', archive: '公版正片', remote: '在线正片' }
  return map[playback.value?.source] || '正片'
})

const trailerLabel = computed(() => {
  const map = { mp4: 'TMDB 官方预告', youtube: 'TMDB 官方预告' }
  return map[trailer.value?.type] || '预告片'
})

const externalDetailLabel = computed(() => {
  const map = { douban: '前往豆瓣', tmdb: '前往 TMDB' }
  return map[movie.value?.source] || '查看外部详情'
})

const hasExternalDetail = computed(() => Boolean(movie.value?.detail_url))

const myComment = computed(() => userComments.value.find((item) => item.is_mine) || null)

function clearTrailerSlowTimer() {
  if (trailerSlowTimer) {
    clearTimeout(trailerSlowTimer)
    trailerSlowTimer = null
  }
}

function clearPlaybackSlowTimer() {
  if (playbackSlowTimer) {
    clearTimeout(playbackSlowTimer)
    playbackSlowTimer = null
  }
}

function startTrailerSlowTimer() {
  clearTrailerSlowTimer()
  showTrailerLoadFallback.value = false
  trailerSlowTimer = setTimeout(() => {
    if (loadingTrailer.value) {
      showTrailerLoadFallback.value = true
    }
  }, LOAD_SLOW_MS)
}

function startPlaybackSlowTimer() {
  clearPlaybackSlowTimer()
  showPlaybackLoadFallback.value = false
  playbackSlowTimer = setTimeout(() => {
    if (loadingPlayback.value) {
      showPlaybackLoadFallback.value = true
    }
  }, LOAD_SLOW_MS)
}

const heroOverlay = computed(() => movie.value?.hero_theme?.overlay || '')

async function load() {
  const id = route.params.id
  pageLoading.value = true
  trailer.value = null
  playback.value = null
  similar.value = []
  movieWantAutoplay.value = false
  moviePlaybackError.value = false
  try {
    const { data } = await movieApi.detail(id)
    movie.value = data
    savedScore.value = data.my_rating || 0
    myScore.value = savedScore.value
    expandedReviews.value = {}
    commentText.value = ''
    commentScore.value = savedScore.value
    activeTab.value = 'trailer'
    pageLoading.value = false

    loadSimilar(id)
    loadComments()
    loadPlayback()
    loadTrailerAsync()
  } catch {
    pageLoading.value = false
  }
}

async function loadSimilar(id) {
  try {
    const sim = await recommendApi.similar(id)
    similar.value = sim.data.items
  } catch {
    similar.value = []
  }
}

async function loadTrailerAsync() {
  const movieId = Number(movie.value?.movie_id || route.params.id)
  await initLocalTrailerIds()

  const instant = applyLocalTrailerIfExists(movieId)
  if (instant) {
    trailer.value = instant
    return
  }

  const cached = getCachedTrailer(movieId)
  if (cached && (cached.type === 'mp4' || cached.type === 'youtube' || cached.type === 'bilibili')) {
    trailer.value = cached
    return
  }

  loadingTrailer.value = true
  startTrailerSlowTimer()
  try {
    trailer.value = await prefetchTrailer(movieId, { refresh: false })
  } catch {
    trailer.value = { type: 'none', message: '预告加载失败' }
  } finally {
    loadingTrailer.value = false
    clearTrailerSlowTimer()
    showTrailerLoadFallback.value = false
  }
}

function scrollToInfo() {
  document.getElementById('movie-info')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function playTrailer() {
  movieWantAutoplay.value = false
  moviePlaybackError.value = false
  activeTab.value = 'trailer'
  document.getElementById('movie-player')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function switchToMovieTab() {
  movieWantAutoplay.value = true
  moviePlaybackError.value = false
  activeTab.value = 'movie'
  if (!playback.value || playback.value.type === 'none') {
    loadPlayback()
  }
  document.getElementById('movie-player')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onMoviePlaybackFailed() {
  moviePlaybackError.value = true
  movieWantAutoplay.value = false
}

function requireLogin() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return false
  }
  return true
}

function formatReviewRating(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return ''
  return Number.isInteger(n) ? `${n}/10` : `${n.toFixed(1)}/10`
}

function reviewStarScore(value) {
  const n = Number(value)
  if (Number.isNaN(n) || n <= 0) return 0
  return n
}

function isReviewLong(content) {
  return (content || '').length > REVIEW_COLLAPSE_CHARS
}

function isReviewExpanded(key) {
  return Boolean(expandedReviews.value[key])
}

function toggleReviewExpand(key) {
  expandedReviews.value = {
    ...expandedReviews.value,
    [key]: !expandedReviews.value[key],
  }
}

function formatCommentTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function loadComments() {
  const id = movie.value?.movie_id || route.params.id
  const { data } = await commentApi.list(id)
  userComments.value = data.items || []
  const mine = userComments.value.find((item) => item.is_mine)
  if (mine) {
    commentText.value = mine.content
    commentScore.value = mine.score || savedScore.value
  }
}

async function submitComment() {
  if (!requireLogin()) return
  const content = commentText.value.trim()
  if (content.length < 5) {
    ElMessage.warning('评论至少 5 个字')
    return
  }
  submittingComment.value = true
  try {
    const payload = {
      movie_id: movie.value.movie_id,
      content,
    }
    if (commentScore.value >= 0.5) {
      payload.score = commentScore.value
    }
    const { data } = await commentApi.submit(payload)
    ElMessage.success(data.message || '评论发表成功')
    if (payload.score) {
      savedScore.value = commentScore.value
      myScore.value = commentScore.value
      ratingsStore.byMovieId[movie.value.movie_id] = commentScore.value
    }
    if (data.item) {
      const others = userComments.value.filter((item) => !item.is_mine)
      userComments.value = [data.item, ...others]
    } else {
      await loadComments()
    }
  } finally {
    submittingComment.value = false
  }
}

async function deleteComment() {
  if (!requireLogin() || !myComment.value) return
  await commentApi.remove(movie.value.movie_id)
  commentText.value = ''
  ElMessage.success('评论已删除')
  await loadComments()
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

function openExternalDetail() {
  const url = movie.value?.detail_url
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

async function loadPlayback() {
  loadingPlayback.value = true
  moviePlaybackError.value = false
  startPlaybackSlowTimer()
  try {
    const { data } = await movieApi.play(movie.value?.movie_id || route.params.id, { search_archive: 0 })
    playback.value = data
    if (data?.source === 'local' && data?.type === 'mp4') {
      activeTab.value = 'movie'
    } else if (route.query.play === '1' && data?.type === 'mp4') {
      activeTab.value = 'movie'
      movieWantAutoplay.value = true
    }
  } finally {
    loadingPlayback.value = false
    clearPlaybackSlowTimer()
    showPlaybackLoadFallback.value = false
  }
}

async function loadTrailer(refresh = false) {
  const movieId = Number(movie.value?.movie_id || route.params.id)
  if (!refresh) {
    const instant = applyLocalTrailerIfExists(movieId)
    if (instant) {
      trailer.value = instant
      return
    }
    const cached = getCachedTrailer(movieId)
    if (cached) {
      trailer.value = cached
      return
    }
  }
  loadingTrailer.value = true
  startTrailerSlowTimer()
  try {
    trailer.value = await prefetchTrailer(movieId, { refresh })
  } catch {
    trailer.value = { type: 'none', message: '预告加载失败' }
  } finally {
    loadingTrailer.value = false
    clearTrailerSlowTimer()
    showTrailerLoadFallback.value = false
  }
}

async function submitRating() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录后再评分')
    return
  }
  if (myScore.value < 0.5) {
    ElMessage.warning('请先点击星星评分')
    return
  }
  await ratingApi.rate({ movie_id: movie.value.movie_id, score: myScore.value })
  savedScore.value = myScore.value
  ratingsStore.byMovieId[movie.value.movie_id] = myScore.value
  ElMessage.success('评分成功，推荐结果已刷新')
}

async function deleteRating() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  if (savedScore.value <= 0) {
    myScore.value = 0
    return
  }
  await ratingApi.remove(movie.value.movie_id)
  myScore.value = 0
  savedScore.value = 0
  delete ratingsStore.byMovieId[movie.value.movie_id]
  ElMessage.success('评分已删除')
}

async function onStarChange(value) {
  if (value === 0 && savedScore.value > 0) {
    await deleteRating()
  }
}

async function toggleFavorite() {
  if (!requireLogin()) return
  if (movie.value.is_favorite) {
    await favoriteApi.remove(movie.value.movie_id)
    movie.value.is_favorite = false
    ElMessage.success('已取消收藏')
  } else {
    await favoriteApi.add(movie.value.movie_id)
    movie.value.is_favorite = true
    ElMessage.success('已标记为收藏')
  }
}

async function toggleWatchlist() {
  if (!requireLogin()) return
  if (movie.value.is_watchlist) {
    await watchlistApi.remove(movie.value.movie_id)
    movie.value.is_watchlist = false
    ElMessage.success('已从待看片单移除')
  } else {
    await watchlistApi.add(movie.value.movie_id)
    movie.value.is_watchlist = true
    ElMessage.success('已添加到待看片单')
  }
}

async function toggleList() {
  if (!requireLogin()) return
  if (movie.value.in_list) {
    await listApi.remove(movie.value.movie_id)
    movie.value.in_list = false
    ElMessage.success('已从片单移除')
  } else {
    await listApi.add(movie.value.movie_id)
    movie.value.in_list = true
    ElMessage.success('已添加到片单')
  }
}

watch(activeTab, (tab) => {
  if (tab !== 'movie') {
    movieWantAutoplay.value = false
    moviePlaybackError.value = false
  }
})

watch(() => route.params.id, load)
onMounted(load)
</script>

<template>
  <div v-if="pageLoading" class="detail-page-loading">
    <div class="detail-page-loading__hero" />
  </div>
  <div v-else-if="movie">
    <section id="movie-info" class="detail-hero">
      <div
        class="detail-hero__backdrop"
        :style="{ backgroundImage: `url(${movie.poster_url})` }"
        aria-hidden="true"
      />
      <div
        class="detail-hero__overlay"
        :style="heroOverlay ? { background: heroOverlay } : undefined"
        aria-hidden="true"
      />
      <div class="relative mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-[240px_1fr] lg:px-8">
        <img
          :src="movie.poster_url"
          :alt="movie.title"
          class="detail-hero__poster mx-auto w-56 md:w-full"
          fetchpriority="high"
          decoding="async"
        />
        <div class="detail-hero__main space-y-4">
          <h1 class="detail-hero__title">{{ movie.title }}</h1>
          <p v-if="movie.aliases" class="detail-hero__muted">{{ movie.aliases }}</p>
          <div class="detail-hero__meta-row">
            <span v-if="movie.rating" class="detail-hero__rating-badge">
              {{ Number(movie.rating).toFixed(1) }}
            </span>
            <span v-if="movie.release_year">{{ movie.release_year }}</span>
            <span v-if="movie.duration">{{ movie.duration }}</span>
            <span v-if="movie.countries">{{ movie.countries }}</span>
          </div>

          <div class="detail-actions">
            <button
              type="button"
              class="detail-action-btn"
              :class="{ 'detail-action-btn--active': movie.in_list }"
              title="添加到片单"
              @click="toggleList"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 5h18v2H3V5zm0 6h12v2H3v-2zm0 6h18v2H3v-2z"/></svg>
            </button>
            <button
              type="button"
              class="detail-action-btn"
              :class="{ 'detail-action-btn--active': movie.is_favorite }"
              title="标记为收藏"
              @click="toggleFavorite"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
            </button>
            <button
              type="button"
              class="detail-action-btn"
              :class="{ 'detail-action-btn--active': movie.is_watchlist }"
              title="添加到待看片单"
              @click="toggleWatchlist"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>
            </button>
            <button
              v-if="hasLocalMovie"
              type="button"
              class="detail-play-trailer detail-play-trailer--movie"
              @click="switchToMovieTab"
            >
              <span class="detail-play-trailer__icon" aria-hidden="true">▶</span>
              播放正片
            </button>
            <button type="button" class="detail-play-trailer" @click="playTrailer">
              <span class="detail-play-trailer__icon" aria-hidden="true">▶</span>
              播放预告片
            </button>
          </div>

          <p class="detail-hero__summary">{{ movie.summary }}</p>
          <div class="detail-hero__credits">
            <p v-if="movie.directors"><span class="detail-hero__label">导演：</span>{{ movie.directors }}</p>
            <p v-if="movie.actors"><span class="detail-hero__label">主演：</span>{{ movie.actors }}</p>
            <p v-if="movie.genres"><span class="detail-hero__label">类型：</span>{{ movie.genres }}</p>
            <p v-if="movie.languages"><span class="detail-hero__label">语言：</span>{{ movie.languages }}</p>
          </div>
          <div class="detail-hero__rate-row">
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-sm detail-hero__label">我的评分</span>
              <el-rate
                v-model="myScore"
                allow-half
                clearable
                :max="10"
                :colors="['#01B4E4', '#01B4E4', '#01B4E4']"
                class="detail-hero__stars"
                @change="onStarChange"
              />
              <span v-if="myScore > 0" class="text-sm font-semibold text-[#01B4E4]">{{ myScore.toFixed(1) }}</span>
            </div>
            <button class="detail-hero__btn detail-hero__btn--primary" @click="submitRating">
              提交评分
            </button>
            <button
              v-if="savedScore > 0"
              class="detail-hero__btn detail-hero__btn--ghost"
              @click="deleteRating"
            >
              删除评分
            </button>
            <button
              v-if="hasExternalDetail"
              class="detail-hero__btn detail-hero__btn--ghost"
              @click="openExternalDetail"
            >
              {{ externalDetailLabel }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <div class="detail-page-body">
    <div id="movie-player" class="mx-auto max-w-6xl px-4 py-7 lg:px-8">
      <section class="movie-player">
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <button
            class="tab-btn"
            :class="activeTab === 'movie' ? 'tab-btn--active' : 'tab-btn--idle'"
            @click="switchToMovieTab"
          >
            播放正片
          </button>
          <button
            class="tab-btn"
            :class="activeTab === 'trailer' ? 'tab-btn--active' : 'tab-btn--idle'"
            @click="playTrailer"
          >
            预告片
          </button>
          <span class="ml-auto text-xs text-muted">
            {{ activeTab === 'movie' ? sourceLabel : trailerLabel }}
          </span>
        </div>

        <div class="movie-player__screen relative overflow-hidden bg-black">
          <div
            v-if="loadingPlayback && activeTab === 'movie'"
            class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-black"
          >
            <p v-if="!showPlaybackLoadFallback" class="text-sm text-white/70">正在加载正片…</p>
            <PlaybackFallbackButton
              v-if="showPlaybackLoadFallback && hasExternalDetail"
              :label="externalDetailLabel"
              @click="openExternalDetail"
            />
            <PlaybackFallbackButton
              v-else-if="showPlaybackLoadFallback"
              label="查看影片信息"
              @click="scrollToInfo"
            />
            <p v-if="showPlaybackLoadFallback" class="px-6 text-center text-xs text-white/50">
              {{ hasExternalDetail ? '加载较慢，可前往原站查看详情' : '加载较慢，可先查看上方影片详情' }}
            </p>
          </div>

          <div
            v-else-if="loadingTrailer && activeTab === 'trailer' && !trailer"
            class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-black/80"
          >
            <img
              :src="movie.poster_url"
              alt=""
              class="absolute inset-0 h-full w-full object-cover opacity-25 blur-sm"
            />
            <p v-if="!showTrailerLoadFallback" class="relative z-10 text-sm text-white/70">正在加载预告…</p>
            <PlaybackFallbackButton
              v-if="showTrailerLoadFallback && hasExternalDetail"
              :label="externalDetailLabel"
              @click="openExternalDetail"
            />
            <PlaybackFallbackButton
              v-else-if="showTrailerLoadFallback"
              label="查看影片信息"
              @click="scrollToInfo"
            />
            <p v-if="showTrailerLoadFallback" class="px-6 text-center text-xs text-white/50">
              {{ hasExternalDetail ? '预告加载较慢，可前往原站查看详情' : '预告加载较慢，可先查看上方影片详情' }}
            </p>
          </div>

          <template v-else-if="activeTab === 'movie'">
            <div v-if="moviePlaybackSource" class="movie-player__video-shell relative h-full">
              <MediaPlayer
                :source="moviePlaybackSource"
                :autoplay="movieAutoplay"
                controls
                :cover="false"
                preload="metadata"
                :play-check-ms="15000"
                :enable-fallback="false"
                @playback-failed="onMoviePlaybackFailed"
              />
              <p v-if="moviePlaybackError" class="movie-player__error">
                正片暂时无法播放，请稍后重试或点击「重新加载」
              </p>
            </div>
            <div v-else class="flex h-full flex-col items-center justify-center gap-4 px-6 text-center text-sm text-white/70">
              <p>{{ playback?.message || '暂无正片' }}</p>
              <PlaybackFallbackButton
                v-if="hasExternalDetail"
                :label="externalDetailLabel"
                @click="openExternalDetail"
              />
            </div>
          </template>

          <template v-else>
            <div v-if="trailer && trailer.type !== 'none'" class="relative h-full">
              <MediaPlayer
                :source="trailer"
                :autoplay="true"
                muted
                :cover="false"
                controls
                :play-check-ms="3000"
                :fallback-label="externalDetailLabel"
                @open-detail="openExternalDetail"
              />
            </div>
            <div v-else class="flex h-full flex-col items-center justify-center gap-4 px-6 text-center text-sm text-white/70">
              <p>{{ trailer?.message || '暂无预告片' }}</p>
              <PlaybackFallbackButton
                v-if="hasExternalDetail"
                :label="externalDetailLabel"
                @click="openExternalDetail"
              />
            </div>
          </template>
        </div>

        <div class="flex flex-wrap items-center gap-2 pt-2 text-sm">
          <button
            class="rounded-full border px-4 py-1.5"
            style="border-color: var(--fywz-border)"
            @click="activeTab === 'movie' ? loadPlayback() : loadTrailer(true)"
          >
            重新加载
          </button>
          <p v-if="activeTab === 'movie' ? playback?.type !== 'none' && playback?.message : trailer?.message" class="text-xs text-muted">
            {{ activeTab === 'movie' ? playback?.message : trailer?.message }}
          </p>
        </div>
      </section>
    </div>

    <div class="mx-auto max-w-5xl space-y-8 px-4 py-7 lg:px-8">
      <section class="detail-reviews">
        <h2 class="detail-section-title">短评</h2>

        <div v-if="userStore.isLoggedIn" class="comment-compose">
          <div class="comment-compose__meta">
            <span class="review-item__author">{{ userStore.user?.username }}</span>
            <span class="review-item__tag">写短评</span>
            <el-rate
              v-model="commentScore"
              allow-half
              clearable
              :max="10"
              :colors="['#f5a623', '#f5a623', '#f5a623']"
              void-color="#c0c4cc"
              class="review-item__stars"
            />
            <span v-if="commentScore > 0" class="review-item__score">{{ formatReviewRating(commentScore) }}</span>
          </div>
          <textarea
            v-model="commentText"
            class="comment-compose__input"
            rows="4"
            maxlength="2000"
            placeholder="写下你的观感…"
          />
          <div class="comment-compose__actions">
            <button
              type="button"
              class="comment-compose__submit"
              :disabled="submittingComment"
              @click="submitComment"
            >
              {{ myComment ? '更新评论' : '发表评论' }}
            </button>
            <button
              v-if="myComment"
              type="button"
              class="comment-compose__delete"
              :disabled="submittingComment"
              @click="deleteComment"
            >
              删除我的评论
            </button>
          </div>
        </div>
        <p v-else class="comment-login-hint">
          <button type="button" class="review-item__toggle" @click="goLogin">登录</button>
          后参与短评讨论
        </p>

        <div v-if="userComments.length" class="review-list review-list--user">
          <h3 class="detail-subsection-title">站友短评</h3>
          <article
            v-for="item in userComments"
            :key="`u-${item.id}`"
            class="review-item"
            :class="{ 'review-item--mine': item.is_mine }"
          >
            <div class="review-item__meta">
              <span class="review-item__author">{{ item.username }}</span>
              <span v-if="item.is_mine" class="review-item__tag review-item__tag--mine">我的</span>
              <span v-else class="review-item__tag">看过</span>
              <el-rate
                v-if="item.score != null"
                class="review-item__stars"
                :model-value="reviewStarScore(item.score)"
                disabled
                allow-half
                :max="10"
                :colors="['#f5a623', '#f5a623', '#f5a623']"
                disabled-void-color="#c0c4cc"
              />
              <span v-if="item.score != null" class="review-item__score">{{ formatReviewRating(item.score) }}</span>
              <span v-if="item.created_at" class="review-item__time">{{ formatCommentTime(item.created_at) }}</span>
            </div>
            <p
              class="review-item__body"
              :class="{ 'review-item__body--collapsed': isReviewLong(item.content) && !isReviewExpanded(`u-${item.id}`) }"
            >
              {{ item.content }}
            </p>
            <button
              v-if="isReviewLong(item.content)"
              type="button"
              class="review-item__toggle"
              @click="toggleReviewExpand(`u-${item.id}`)"
            >
              {{ isReviewExpanded(`u-${item.id}`) ? '收起' : '(展开)' }}
            </button>
          </article>
        </div>
        <p v-else-if="userStore.isLoggedIn" class="comment-empty">还没有站友短评，来写第一条吧。</p>
      </section>

      <section v-if="movie.crawled_review_list?.length" class="detail-reviews">
        <h2 class="detail-section-title">精选短评</h2>
        <div class="review-list">
          <article
            v-for="(item, idx) in movie.crawled_review_list"
            :key="idx"
            class="review-item"
          >
            <div class="review-item__meta">
              <span class="review-item__author">{{ item.author }}</span>
              <span class="review-item__tag">看过</span>
              <el-rate
                v-if="item.rating != null"
                class="review-item__stars"
                :model-value="reviewStarScore(item.rating)"
                disabled
                allow-half
                :max="10"
                :colors="['#f5a623', '#f5a623', '#f5a623']"
                disabled-void-color="#c0c4cc"
              />
              <span v-if="item.rating != null" class="review-item__score">{{ formatReviewRating(item.rating) }}</span>
            </div>
            <p
              class="review-item__body"
              :class="{ 'review-item__body--collapsed': isReviewLong(item.content) && !isReviewExpanded(`c-${idx}`) }"
            >
              {{ item.content }}
            </p>
            <button
              v-if="isReviewLong(item.content)"
              type="button"
              class="review-item__toggle"
              @click="toggleReviewExpand(`c-${idx}`)"
            >
              {{ isReviewExpanded(`c-${idx}`) ? '收起' : '(展开)' }}
            </button>
          </article>
        </div>
      </section>
    </div>

    <div class="mx-auto max-w-7xl px-4 pb-8 lg:px-8">
      <MovieRow title="同类相似推荐" :movies="similar" />
    </div>
    </div>
  </div>
</template>

<style scoped>
.detail-hero {
  position: relative;
  overflow: hidden;
  color: var(--fywz-hero-text);
}

.detail-hero__backdrop {
  position: absolute;
  inset: -20%;
  background-color: #031d31;
  background-size: cover;
  background-position: center center;
  filter: blur(32px) saturate(1.2) brightness(0.62);
  transform: translateZ(0);
  pointer-events: none;
  contain: strict;
}

.detail-hero__overlay {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: var(--fywz-hero-overlay);
  pointer-events: none;
}

.detail-hero::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
  height: 5rem;
  background: linear-gradient(to bottom, transparent, var(--fywz-bg));
  pointer-events: none;
}

.detail-hero__main,
.detail-hero__poster {
  position: relative;
  z-index: 1;
}

.detail-hero__poster {
  border-radius: 12px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.35);
}

.detail-hero__title {
  font-size: clamp(1.75rem, 4vw, 2.5rem);
  font-weight: 800;
  line-height: 1.15;
  color: var(--fywz-hero-text);
}

.detail-hero__muted,
.detail-hero__summary,
.detail-hero__credits {
  color: var(--fywz-hero-text-muted);
}

.detail-hero__summary {
  max-width: 48rem;
  line-height: 1.75;
}

.detail-hero__meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.9rem;
  color: var(--fywz-hero-meta);
}

.detail-hero__rating-badge {
  border-radius: 999px;
  background: rgba(1, 180, 228, 0.18);
  padding: 0.15rem 0.55rem;
  font-weight: 700;
  color: var(--fywz-accent);
}

.detail-hero__credits {
  display: grid;
  gap: 0.35rem;
  font-size: 0.9rem;
}

@media (min-width: 768px) {
  .detail-hero__credits {
    grid-template-columns: 1fr 1fr;
  }
}

.detail-hero__label {
  font-weight: 600;
  color: var(--fywz-hero-text);
}

.detail-hero__rate-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  padding-top: 0.25rem;
}

.detail-hero__stars :deep(.el-rate__icon),
.detail-hero__stars :deep(.el-rate__decimal) {
  font-size: 1rem;
  margin-right: 0;
}

.detail-hero__btn {
  border-radius: 999px;
  padding: 0.45rem 1.15rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.2s;
}

.detail-hero__btn--primary {
  border: none;
  background: var(--fywz-accent);
  color: var(--fywz-accent-text);
}

.detail-hero__btn--ghost {
  border: 1px solid var(--fywz-border);
  background: transparent;
  color: var(--fywz-hero-text);
}

.detail-hero__btn:hover {
  filter: brightness(1.05);
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
}

.detail-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--fywz-detail-action-bg);
  color: var(--fywz-detail-action-color);
  cursor: pointer;
  transition: transform 0.15s, background 0.15s, color 0.15s;
}

.detail-action-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.detail-action-btn:hover {
  transform: scale(1.05);
  filter: brightness(1.08);
}

.detail-action-btn--active {
  background: var(--fywz-detail-action-active-bg);
  color: var(--fywz-detail-action-active-color);
}

.detail-play-trailer {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 0.25rem;
  border: none;
  background: transparent;
  font-size: 1rem;
  font-weight: 600;
  color: var(--fywz-play-trailer-text);
  cursor: pointer;
}

.detail-play-trailer__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--fywz-play-trailer-icon-bg);
  color: var(--fywz-play-trailer-icon-color);
  font-size: 0.75rem;
}

.movie-player__screen {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
}

.movie-player__video-shell {
  position: relative;
  height: 100%;
  min-height: 0;
}

.movie-player__error {
  position: absolute;
  inset: 0;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  text-align: center;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #fff;
  background: rgba(0, 0, 0, 0.72);
}

.detail-subsection-title {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.detail-play-trailer--movie {
  color: var(--fywz-accent);
}

.review-item__tag--mine {
  color: var(--fywz-accent);
  font-weight: 600;
}

.detail-section-title {
  margin: 0 0 0.65rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.detail-reviews .detail-reviews .comment-compose__input {
  min-height: 4.5rem;
  font-size: 0.875rem;
  line-height: 1.55;
  padding: 0.6rem 0.75rem;
}

.detail-reviews .comment-compose__meta {
  margin-bottom: 0.5rem;
}

.review-list {
  padding-top: 0;
}

.detail-reviews .review-item {
  padding: 0.65rem 0;
}

.detail-reviews .review-item__meta {
  margin-bottom: 0.35rem;
  gap: 0.25rem 0.5rem;
}

.detail-reviews .review-item__author {
  font-size: 0.875rem;
}

.detail-reviews .review-item__tag,
.detail-reviews .review-item__score {
  font-size: 0.8rem;
}

.detail-reviews .review-item__stars :deep(.el-rate__icon),
.detail-reviews .review-item__stars :deep(.el-rate__decimal) {
  font-size: 0.72rem;
  margin-right: 0;
}

.detail-reviews .review-item__body {
  font-size: 0.875rem;
  line-height: 1.55;
}

.detail-reviews .review-item__body--collapsed {
  -webkit-line-clamp: 3;
}

.detail-reviews .review-item__toggle {
  margin-top: 0.2rem;
  font-size: 0.8rem;
}

.detail-reviews .comment-compose__meta {
  margin-bottom: 0.5rem;
}

.detail-reviews .comment-compose__input {
  min-height: 4.5rem;
  font-size: 0.875rem;
  line-height: 1.55;
  padding: 0.6rem 0.75rem;
}

.review-list {
  padding-top: 0.25rem;
}

.review-list--user {
  margin-top: 1.25rem;
}

.comment-compose {
  margin-bottom: 0.5rem;
}

.comment-compose__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.65rem;
  margin-bottom: 0.65rem;
}

.comment-compose__input {
  width: 100%;
  resize: vertical;
  min-height: 6rem;
  border-radius: 8px;
  border: 1px solid var(--fywz-border);
  background: var(--fywz-surface-2);
  padding: 0.75rem 0.85rem;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--fywz-text);
}

.comment-compose__input:focus {
  outline: none;
  border-color: #01b4e4;
}

.comment-compose__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.75rem;
}

.comment-compose__submit {
  border-radius: 999px;
  border: none;
  background: #01b4e4;
  padding: 0.45rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #042541;
  cursor: pointer;
}

.comment-compose__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.comment-compose__delete {
  border-radius: 999px;
  border: 1px solid var(--fywz-border);
  background: transparent;
  padding: 0.45rem 1.1rem;
  font-size: 0.9rem;
  color: var(--fywz-muted);
  cursor: pointer;
}

.comment-login-hint,
.comment-empty {
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
  color: var(--fywz-muted);
}

.review-item__time {
  margin-left: auto;
  font-size: 0.8rem;
  color: var(--fywz-muted);
}

.review-item {
  padding: 1.15rem 0;
  border-bottom: 1px solid var(--fywz-border);
}

.review-item:last-child {
  border-bottom: none;
}

.review-item__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.65rem;
  margin-bottom: 0.55rem;
}

.review-item__author {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--fywz-link);
}

.review-item__toggle {
  margin-top: 0.35rem;
  border: none;
  background: none;
  padding: 0;
  font-size: 0.9rem;
  color: var(--fywz-link);
  cursor: pointer;
}

.review-item__tag {
  font-size: 0.85rem;
  color: var(--fywz-muted);
}

.review-item__stars {
  height: auto;
}

.review-item__stars :deep(.el-rate__icon),
.review-item__stars :deep(.el-rate__decimal) {
  font-size: 0.72rem;
  margin-right: 0;
}

.review-item__score {
  font-size: 0.85rem;
  color: var(--fywz-muted);
}

.review-item__body {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--fywz-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.review-item__body--collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: normal;
}

.review-item__toggle:hover {
  text-decoration: underline;
}

.detail-page-loading {
  min-height: 60vh;
  background: #031d31;
}

.detail-page-loading__hero {
  min-height: 60vh;
  background: linear-gradient(
    to right,
    rgba(3, 37, 65, 0.96) 0%,
    rgba(13, 37, 63, 0.88) 42%,
    rgba(20, 33, 61, 0.72) 100%
  );
}
</style>
