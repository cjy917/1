<!--
  【首页 H3】单张电影卡片
  功能：点击进详情、悬停播预告、底部快捷评分
  依赖：trailerCache.js、MediaPlayer.vue、ratingsStore
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { useRatingsStore } from '../stores/ratings'
import {
  applyLocalTrailerIfExists,
  getCachedTrailer,
  isLocalTrailer,
  isRemoteTrailer,
  isTrailerPlayable,
  prefetchTrailer,
  tryLocalTrailerFallback,
} from '../utils/trailerCache'
import MediaPlayer from './MediaPlayer.vue'

const props = defineProps({
  movie: { type: Object, required: true },
  recommendMode: { type: Boolean, default: false }, // 推荐页：显示算法标签、reason
})

// ─── 推荐算法标签（Spark ALS/GraphX/Content 等） ─────────────────────────────
const ALGO_TAG_META = {
  als: { label: 'ALS', className: 'algo-tag--als' },
  graphx: { label: 'GraphX', className: 'algo-tag--graphx' },
  content: { label: 'Content', className: 'algo-tag--content' },
  cold_start: { label: '热门', className: 'algo-tag--popular' },
  popular: { label: '热门', className: 'algo-tag--popular' },
}

const algoTags = computed(() => {
  const raw = props.movie.algorithm
  if (!raw) return []
  const keys =
    raw === 'cold_start' || raw === 'popular'
      ? ['popular']
      : String(raw).split('+').filter(Boolean)
  return keys
    .map((key) => ALGO_TAG_META[key])
    .filter(Boolean)
})

// ─── 展示用计算属性 ─────────────────────────────────────────────────────────
const displayScore = computed(() => {
  const rating = props.movie.rating
  if (rating != null && rating !== '' && !Number.isNaN(Number(rating))) {
    return Number(rating).toFixed(1)
  }
  const score = props.movie.score
  if (score != null && score !== '' && !Number.isNaN(Number(score))) {
    const num = Number(score)
    return num <= 1 ? (num * 10).toFixed(1) : num.toFixed(1)
  }
  return null
})

const router = useRouter()
const userStore = useUserStore()
const ratingsStore = useRatingsStore()
const saving = ref(false)

// ─── 悬停预告播放状态 ───────────────────────────────────────────────────────
const cardRef = ref(null)
const hovering = ref(false)
const trailer = ref(null)
const trailerPlaying = ref(false)
const online = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)

let loadSeq = 0       // 防止快速移入移出时旧请求覆盖新状态
let observer = null   // 进入视口预加载预告

const poster = computed(() => props.movie.poster_url || `/api/posters/${props.movie.movie_id}`)

const displayDate = computed(() => {
  const raw = props.movie.release_date || ''
  const match = raw.match(/(\d{4})-(\d{2})-(\d{2})/)
  if (match) return `${match[1]}年 ${match[2]}月 ${match[3]}日`
  if (props.movie.release_year) return `${props.movie.release_year}年`
  return ''
})

const savedScore = computed(() => {
  const fromStore = ratingsStore.byMovieId[props.movie.movie_id]
  if (fromStore != null) return fromStore
  return props.movie.my_rating || 0
})

const starScore = computed(() => savedScore.value / 2)

const canPlayTrailer = computed(() => isTrailerPlayable(trailer.value))

const shouldTryTrailer = computed(() => {
  if (!hovering.value || !canPlayTrailer.value) return false
  if (isLocalTrailer(trailer.value)) return true
  return online.value && isRemoteTrailer(trailer.value)
})

const showVideo = computed(() => shouldTryTrailer.value && trailerPlaying.value)

/** 写入 trailer 数据；本地 mp4 可立即播放 */
function applyTrailer(data) {
  trailer.value = data
  if (!hovering.value || !isTrailerPlayable(data)) return
  if (isLocalTrailer(data)) {
    trailerPlaying.value = true
  }
}

/** 【H3】悬停时加载预告：cache → prefetchTrailer → 本地 HEAD 回退 */
async function ensureTrailer() {
  const movieId = props.movie.movie_id
  const instant = applyLocalTrailerIfExists(movieId)
  if (instant) {
    applyTrailer(instant)
    return
  }

  const cached = getCachedTrailer(movieId)
  if (cached) {
    if (cached.type === 'mp4' || cached.type === 'none') {
      applyTrailer(cached)
      return
    }
    if (!online.value) {
      const local = await tryLocalTrailerFallback(movieId)
      if (local) {
        applyTrailer(local)
        return
      }
    }
  }
  const seq = ++loadSeq
  try {
    const data = await prefetchTrailer(movieId)
    if (seq !== loadSeq || !hovering.value) return
    applyTrailer(data)
  } catch {
    if (seq !== loadSeq) return
    const local = await tryLocalTrailerFallback(movieId)
    if (local) {
      applyTrailer(local)
      return
    }
    trailer.value = { type: 'none' }
  }
}

function onMouseEnter() {
  hovering.value = true
  ensureTrailer()
}

function onMouseLeave() {
  hovering.value = false
  trailerPlaying.value = false
  loadSeq += 1
}

function onPlaybackConfirmed() {
  if (hovering.value) trailerPlaying.value = true
}

function onPlaybackFailed() {
  trailerPlaying.value = false
}

/** 点击卡片 → 电影详情页 */
function openDetail() {
  router.push({ name: 'movie-detail', params: { id: props.movie.movie_id } })
}

/** 底部 el-rate：10 分制存后端，界面 5 星（×2） */
async function onStarChange(value) {
  if (saving.value) return
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录后再评分')
    return
  }
  saving.value = true
  try {
    if (value === 0) {
      if (savedScore.value > 0) {
        await ratingsStore.remove(props.movie.movie_id)
        ElMessage.success('评分已删除')
      }
      return
    }
    const score = value * 2
    await ratingsStore.save(props.movie.movie_id, score)
    ElMessage.success('评分成功')
  } catch {
    ElMessage.error('操作失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

/** 卡片进入视口前 160px 即预取预告，减少悬停等待 */
onMounted(() => {
  const el = cardRef.value
  if (!el || typeof IntersectionObserver === 'undefined') return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        prefetchTrailer(props.movie.movie_id)
      }
    },
    { rootMargin: '160px' },
  )
  observer.observe(el)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  loadSeq += 1
})
</script>

<template>
  <!-- 整张卡片可点击；评分条 @click.stop 阻止冒泡 -->
  <article class="group w-[140px] shrink-0 cursor-pointer sm:w-[150px]" @click="openDetail">
    <div
      ref="cardRef"
      class="relative overflow-hidden rounded-[10px] shadow-sm transition group-hover:shadow-lg"
      style="box-shadow: 0 2px 8px var(--fywz-card-shadow); ring: 1px solid var(--fywz-border)"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <!-- 海报：有视频时透明隐藏 -->
      <img
        :src="poster"
        :alt="movie.title"
        class="aspect-[2/3] w-full object-cover transition duration-300 group-hover:scale-[1.03]"
        :class="{ 'opacity-0': showVideo }"
        loading="lazy"
      />

      <!-- 悬停预告层：card-mode 静音循环 -->
      <div
        v-if="shouldTryTrailer"
        class="card-video-wrap"
        :class="{ 'card-video-wrap--active': showVideo }"
      >
        <MediaPlayer
          :source="trailer"
          autoplay
          muted
          loop
          cover
          card-mode
          :enable-fallback="false"
          :play-check-ms="1800"
          @playback-confirmed="onPlaybackConfirmed"
          @playback-failed="onPlaybackFailed"
        />
      </div>

      <!-- 推荐模式左上角：综合分 -->
      <span
        v-if="recommendMode && displayScore"
        class="absolute left-1.5 top-1.5 z-20 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-bold text-[#f5c518]"
      >
        {{ displayScore }}
      </span>
      <!-- 已评分右上角：我的分数 -->
      <span
        v-if="savedScore > 0"
        class="absolute right-1.5 top-1.5 z-20 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-bold text-[#01B4E4]"
      >
        {{ savedScore.toFixed(1) }}
      </span>
      <!-- 悬停上滑：快捷评分 -->
      <div
        class="absolute inset-x-0 bottom-0 z-20 flex translate-y-full flex-col items-center bg-gradient-to-t from-black/95 via-black/70 to-transparent px-1 pb-2 pt-7 transition-transform duration-200 group-hover:translate-y-0"
        @click.stop
      >
        <span class="mb-1.5 text-xs font-medium text-white/90 sm:text-sm">我的评分</span>
        <el-rate
          :model-value="starScore"
          allow-half
          clearable
          :max="5"
          :disabled="saving"
          :colors="['#01B4E4', '#01B4E4', '#01B4E4']"
          void-color="#6b7280"
          disabled-void-color="#4b5563"
          class="card-star-rate"
          @change="onStarChange"
        />
      </div>
    </div>
    <!-- 标题 / 算法标签 / 上映日期 -->
    <div class="mt-2 px-0.5">
      <h3 class="line-clamp-2 text-[15px] font-bold leading-5">{{ movie.title }}</h3>
      <div v-if="recommendMode && algoTags.length" class="algo-tags mt-1.5 flex flex-wrap gap-1">
        <span
          v-for="tag in algoTags"
          :key="tag.label"
          class="algo-tag"
          :class="tag.className"
        >
          {{ tag.label }}
        </span>
      </div>
      <p v-if="movie.reason" class="reason-text mt-1.5">{{ movie.reason }}</p>
      <p class="mt-1 text-sm text-muted">
        <template v-if="recommendMode && displayScore">{{ displayScore }} 分</template>
        <template v-if="recommendMode && displayScore && displayDate"> · </template>
        {{ displayDate }}
      </p>
    </div>
  </article>
</template>

<style scoped>
/* 标题两行截断 */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-video-wrap {
  position: absolute;
  inset: 0;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.25s ease;
  pointer-events: none;
}

.card-video-wrap--active {
  opacity: 1;
}

.card-star-rate {
  height: auto;
}

.card-star-rate :deep(.el-rate__icon) {
  font-size: 1.35rem;
  margin-right: 0.05rem;
}

.card-star-rate :deep(.el-rate__decimal) {
  font-size: 1.35rem;
}

.reason-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 11px;
  line-height: 1.35;
  color: var(--fywz-muted, #9aa7c0);
}

.algo-tag {
  display: inline-block;
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.4;
}

.algo-tag--als {
  background: rgba(37, 99, 235, 0.15);
  color: #2563eb;
}

.algo-tag--graphx {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.algo-tag--content {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.algo-tag--popular {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}
</style>
