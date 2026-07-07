/**
 * 【详情页·逻辑层】全部状态与 API 调用
 * 代码搜索: load / toggleFavorite / loadTrailer / submitComment / loadSimilar
 * 连接: api/index.js → backend/app.py → services/*.py
 */
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { commentApi, favoriteApi, listApi, movieApi, ratingApi, recommendApi, translateApi, watchlistApi } from '../../api'
import { useUserStore } from '../../stores/user'
import { useRatingsStore } from '../../stores/ratings'
import { useThemeStore } from '../../stores/theme'
import { useDelayedFallback } from '../useDelayedFallback'
import {
  applyLocalTrailerIfExists,
  getCachedTrailer,
  initLocalTrailerIds,
  prefetchTrailer,
} from '../../utils/trailerCache'
import {
  detailLinkLabel,
  resolveDetailInfoLinks,
  resolveStreamingLinks,
} from '../../utils/watchLinks'
import { buildHeroFlowStyle, buildHeroScrimStyle } from '../../utils/heroTheme'
import { formatSummaryDisplay } from '../../utils/summary'
import { buildPersonRoute, buildMoviesGenreRoute, buildMoviesLanguageRoute, parseCreditNames } from '../../utils/credits'

const LOAD_SLOW_MS = 3000
const VALID_TRAILER_TYPES = new Set(['mp4', 'youtube', 'bilibili'])

export function useMovieDetailPage() {
  const route = useRoute()
  const router = useRouter()
  const userStore = useUserStore()
  const ratingsStore = useRatingsStore()
  const themeStore = useThemeStore()

  // ─── 响应式状态 ─────────────────────────────────────────────────────────────
  const movie = ref(null)              // GET /api/movies/:id 主数据
  const similar = ref([])              // 相似推荐列表
  const myScore = ref(0)               // 当前编辑中的评分（10 分制）
  const savedScore = ref(0)            // 已保存评分
  const playback = ref(null)           // 正片播放源
  const trailer = ref(null)            // 预告播放源
  const loadingPlayback = ref(false)
  const loadingTrailer = ref(false)
  const { showFallback: showTrailerLoadFallback, start: startTrailerSlowTimer, reset: resetTrailerFallback } =
    useDelayedFallback(LOAD_SLOW_MS)
  const { showFallback: showPlaybackLoadFallback, start: startPlaybackSlowTimer, reset: resetPlaybackFallback } =
    useDelayedFallback(LOAD_SLOW_MS)
  const activeTab = ref('trailer')
  const expandedReviews = ref({})
  const reviewOverflow = ref({})
  const reviewTranslations = ref({})
  const summaryExpanded = ref(false)
  const userComments = ref([])
  const commentText = ref('')
  const commentScore = ref(0)
  const submittingComment = ref(false)
  const pageLoading = ref(true)
  const movieWantAutoplay = ref(false)
  const moviePlaybackError = ref(false)
  const watchLinks = ref(null)

  // ─── 计算属性（展示 / 链接 / Hero 主题） ───────────────────────────────────
  const displaySummary = computed(() => formatSummaryDisplay(movie.value?.summary))

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

  const streamingLinks = computed(() => resolveStreamingLinks(watchLinks.value, movie.value))
  const detailInfoLinks = computed(() => resolveDetailInfoLinks(watchLinks.value, movie.value))
  const hasDetailInfo = computed(() => detailInfoLinks.value.length > 0)
  const primaryDetailLabel = computed(() => detailLinkLabel(detailInfoLinks.value[0]))

  const commentStarScore = computed({
    get: () => commentScore.value / 2,
    set: (value) => {
      commentScore.value = value > 0 ? value * 2 : 0
    },
  })

  const starScore = computed({
    get: () => myScore.value / 2,
    set: (value) => {
      myScore.value = value > 0 ? value * 2 : 0
    },
  })

  const myComment = computed(() => userComments.value.find((item) => item.is_mine) || null)
  const heroFlowStyle = computed(() => buildHeroFlowStyle(movie.value?.hero_theme))
  const heroScrimStyle = computed(() => buildHeroScrimStyle(movie.value?.hero_theme))

  const directorNames = computed(() =>
    movie.value?.director_list?.length
      ? movie.value.director_list
      : parseCreditNames(movie.value?.directors),
  )
  const actorNames = computed(() =>
    movie.value?.actor_list?.length ? movie.value.actor_list : parseCreditNames(movie.value?.actors),
  )
  const writerNames = computed(() =>
    movie.value?.writer_list?.length ? movie.value.writer_list : parseCreditNames(movie.value?.writers),
  )
  const genreNames = computed(() =>
    movie.value?.genre_list?.length ? movie.value.genre_list : parseCreditNames(movie.value?.genres),
  )
  const languageNames = computed(() => parseCreditNames(movie.value?.languages))

  const creditRows = computed(() => [
    { label: '导演', names: directorNames.value, to: (name) => buildPersonRoute(name, 'director') },
    { label: '编剧', names: writerNames.value, to: (name) => buildPersonRoute(name, 'writer') },
    { label: '主演', names: actorNames.value, to: (name) => buildPersonRoute(name, 'actor') },
    { label: '类型', names: genreNames.value, to: (name) => buildMoviesGenreRoute(name) },
    { label: '语言', names: languageNames.value, to: (name) => buildMoviesLanguageRoute(name) },
  ].filter((row) => row.names.length))

  // ─── 数据加载 ───────────────────────────────────────────────────────────────
  /** 【API】详情页入口 → GET /api/movies/:id */
  async function load() {
    const id = route.params.id
    pageLoading.value = true
    trailer.value = null
    playback.value = null
    watchLinks.value = null
    similar.value = []
    movieWantAutoplay.value = false
    moviePlaybackError.value = false
    try {
      const { data } = await movieApi.detail(id)
      movie.value = data
      savedScore.value = data.my_rating || 0
      myScore.value = savedScore.value
      expandedReviews.value = {}
      reviewOverflow.value = {}
      reviewTranslations.value = {}
      summaryExpanded.value = false
      commentText.value = ''
      commentScore.value = savedScore.value
      activeTab.value = 'trailer'
      pageLoading.value = false

      loadSimilar(id)
      await loadComments()
      loadWatchLinks()
      loadPlayback()
      loadTrailer(false, { initLocal: true, strictCachedTypes: true })
    } catch {
      pageLoading.value = false
    }
  }

  /** 【API】相似推荐 → GET /api/recommend/similar/:id */
  async function loadSimilar(id) {
    try {
      const sim = await recommendApi.similar(id)
      similar.value = sim.data.items
    } catch {
      similar.value = []
    }
  }

  // ─── UI 交互（滚动 / Tab 切换） ─────────────────────────────────────────────
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

  // ─── 短评展示 / 翻译 ───────────────────────────────────────────────────────
  function isReviewCollapsible(key) {
    return Boolean(reviewOverflow.value[key])
  }

  function measureReviewBody(el, key) {
    if (!el) return
    requestAnimationFrame(() => {
      el.classList.add('review-item__body--collapsed')
      const overflows = el.scrollHeight > el.clientHeight + 1
      if (reviewOverflow.value[key] !== overflows) {
        reviewOverflow.value = { ...reviewOverflow.value, [key]: overflows }
      }
      if (!overflows || isReviewExpanded(key)) {
        el.classList.remove('review-item__body--collapsed')
      }
    })
  }

  function toggleSummaryExpand() {
    summaryExpanded.value = !summaryExpanded.value
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

  function displayReviewText(key, original) {
    const state = reviewTranslations.value[key]
    if (state?.showingTranslation && state.translated) {
      return state.translated
    }
    return original
  }

  function reviewTranslationLabel(key) {
    const state = reviewTranslations.value[key]
    if (state?.loading) return '翻译中…'
    if (state?.showingTranslation) return '原文'
    return '翻译'
  }

  function isReviewTranslationLoading(key) {
    return Boolean(reviewTranslations.value[key]?.loading)
  }

  function canTranslateReview(content) {
    return (content || '').trim().length >= 5
  }

  /** 【API】评论翻译 → POST /api/translate */
  async function toggleReviewTranslation(key, content) {
    const text = (content || '').trim()
    if (!text) return

    const current = reviewTranslations.value[key]
    if (current?.showingTranslation) {
      reviewTranslations.value = {
        ...reviewTranslations.value,
        [key]: { ...current, showingTranslation: false },
      }
      return
    }

    if (current?.translated) {
      reviewTranslations.value = {
        ...reviewTranslations.value,
        [key]: { ...current, showingTranslation: true },
      }
      expandedReviews.value = { ...expandedReviews.value, [key]: true }
      return
    }

    reviewTranslations.value = {
      ...reviewTranslations.value,
      [key]: { loading: true },
    }

    try {
      const { data } = await translateApi.translate({ text })
      reviewTranslations.value = {
        ...reviewTranslations.value,
        [key]: {
          translated: data.translated,
          target: data.target,
          loading: false,
          showingTranslation: true,
        },
      }
      expandedReviews.value = { ...expandedReviews.value, [key]: true }
    } catch (err) {
      const status = err.response?.status
      const apiError = err.response?.data?.error
      let message = apiError || '翻译失败，请稍后重试'
      if (status === 404 || status === 405) {
        message = '翻译接口未生效，请重启后端服务后再试'
      } else if (status === 502) {
        message = apiError || '翻译服务暂时不可用，请检查网络或代理'
      }
      ElMessage.error(message)
      const next = { ...reviewTranslations.value }
      delete next[key]
      reviewTranslations.value = next
    }
  }

  /** 【API】短评列表 → GET /api/movies/:id/comments */
  async function loadComments() {
    const id = movie.value?.movie_id || route.params.id
    const { data } = await commentApi.list(id)
    userComments.value = data.items || []
    const mine = userComments.value.find((item) => item.is_mine)
    if (mine) {
      commentText.value = mine.content
      commentScore.value = mine.score || savedScore.value
    }
    await scrollToTargetComment()
  }

  function expandReviewForHash(hash) {
    if (!hash) return
    const userMatch = hash.match(/^#comment-user-(\d+)$/)
    if (userMatch) {
      expandedReviews.value = {
        ...expandedReviews.value,
        [`u-${userMatch[1]}`]: true,
      }
      return
    }
    const crawledMatch = hash.match(/^#comment-crawled-\d+-(\d+)$/)
    if (crawledMatch) {
      expandedReviews.value = {
        ...expandedReviews.value,
        [`c-${crawledMatch[1]}`]: true,
      }
    }
  }

  async function scrollToTargetComment() {
    const hash = route.hash
    if (!hash?.startsWith('#comment-')) return

    expandReviewForHash(hash)
    await nextTick()

    requestAnimationFrame(() => {
      const target = document.querySelector(hash)
      if (!target) return
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      target.classList.add('review-item--highlight')
      window.setTimeout(() => target.classList.remove('review-item--highlight'), 2200)
    })
  }

  /** 【API】发表/更新短评 → POST /api/comments */
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

  /** 【API】删除短评 → DELETE /api/comments */
  async function deleteComment() {
    if (!requireLogin() || !myComment.value) return
    await commentApi.remove(movie.value.movie_id)
    commentText.value = ''
    ElMessage.success('评论已删除')
    await loadComments()
  }

  function goLogin() {
    router.push({ path: '/', query: { redirect: route.fullPath } })
  }

  function openDetailPage(url) {
    const target = url || detailInfoLinks.value[0]?.url || movie.value?.detail_url
    if (target) {
      window.open(target, '_blank', 'noopener,noreferrer')
    }
  }

  function openWatchPage(url) {
    const target = url || watchLinks.value?.primary_url
    if (target) {
      window.open(target, '_blank', 'noopener,noreferrer')
    }
  }

  /** 【API】观看链接 → GET /api/movies/:id/watch-links */
  async function loadWatchLinks() {
    const movieId = movie.value?.movie_id || route.params.id
    if (!movieId) return
    try {
      const { data } = await movieApi.watchLinks(movieId)
      watchLinks.value = data
    } catch {
      watchLinks.value = null
    }
  }

  /** 【API】正片 → GET /api/movies/:id/play */
  async function loadPlayback() {
    loadingPlayback.value = true
    moviePlaybackError.value = false
    startPlaybackSlowTimer(() => loadingPlayback.value)
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
      resetPlaybackFallback()
    }
  }

  /** 【API】预告 → GET /api/movies/:id/trailer */
  async function loadTrailer(refresh = false, { initLocal = false, strictCachedTypes = false } = {}) {
    const movieId = Number(movie.value?.movie_id || route.params.id)
    if (initLocal) await initLocalTrailerIds()
    if (!refresh) {
      const instant = applyLocalTrailerIfExists(movieId)
      if (instant) {
        trailer.value = instant
        return
      }
      const cached = getCachedTrailer(movieId)
      if (cached && (!strictCachedTypes || VALID_TRAILER_TYPES.has(cached.type))) {
        trailer.value = cached
        return
      }
    }
    loadingTrailer.value = true
    startTrailerSlowTimer(() => loadingTrailer.value)
    try {
      trailer.value = await prefetchTrailer(movieId, { refresh })
    } catch {
      trailer.value = { type: 'none', message: '预告加载失败' }
    } finally {
      loadingTrailer.value = false
      resetTrailerFallback()
    }
  }

  /** 【API】评分 → POST /api/ratings */
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

  /** 【API】收藏 → POST/DELETE /api/favorites */
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

  /** 【API】待看片单 → POST/DELETE /api/watchlist */
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

  /** 【API】片单 → POST/DELETE /api/lists */
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
  watch(() => route.hash, () => {
    scrollToTargetComment()
  })
  onMounted(load)

  return reactive({
    route,
    router,
    userStore,
    themeStore,
    movie,
    similar,
    pageLoading,
    myScore,
    savedScore,
    playback,
    trailer,
    loadingPlayback,
    loadingTrailer,
    showTrailerLoadFallback,
    showPlaybackLoadFallback,
    activeTab,
    summaryExpanded,
    userComments,
    commentText,
    commentScore,
    submittingComment,
    moviePlaybackError,
    watchLinks,
    displaySummary,
    moviePlaybackSource,
    hasLocalMovie,
    movieAutoplay,
    sourceLabel,
    trailerLabel,
    streamingLinks,
    hasDetailInfo,
    primaryDetailLabel,
    commentStarScore,
    starScore,
    myComment,
    heroFlowStyle,
    heroScrimStyle,
    creditRows,
    scrollToInfo,
    playTrailer,
    switchToMovieTab,
    onMoviePlaybackFailed,
    toggleSummaryExpand,
    isReviewCollapsible,
    measureReviewBody,
    isReviewExpanded,
    toggleReviewExpand,
    displayReviewText,
    reviewTranslationLabel,
    isReviewTranslationLoading,
    canTranslateReview,
    toggleReviewTranslation,
    submitComment,
    deleteComment,
    goLogin,
    openDetailPage,
    openWatchPage,
    loadPlayback,
    loadTrailer,
    submitRating,
    deleteRating,
    onStarChange,
    toggleFavorite,
    toggleWatchlist,
    toggleList,
  })
}
