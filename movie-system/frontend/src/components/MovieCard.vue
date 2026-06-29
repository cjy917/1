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
})

const router = useRouter()
const userStore = useUserStore()
const ratingsStore = useRatingsStore()
const saving = ref(false)

const cardRef = ref(null)
const hovering = ref(false)
const trailer = ref(null)
const trailerPlaying = ref(false)
const online = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)

let loadSeq = 0
let observer = null

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

const starScore = computed(() => savedScore.value)

const canPlayTrailer = computed(() => isTrailerPlayable(trailer.value))

const shouldTryTrailer = computed(() => {
  if (!hovering.value || !canPlayTrailer.value) return false
  if (isLocalTrailer(trailer.value)) return true
  return online.value && isRemoteTrailer(trailer.value)
})

const showVideo = computed(() => shouldTryTrailer.value && trailerPlaying.value)

function applyTrailer(data) {
  trailer.value = data
  if (!hovering.value || !isTrailerPlayable(data)) return
  if (isLocalTrailer(data)) {
    trailerPlaying.value = true
  }
}

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

function openDetail() {
  router.push({ name: 'movie-detail', params: { id: props.movie.movie_id } })
}

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
    const score = value
    await ratingsStore.save(props.movie.movie_id, score)
    ElMessage.success('评分成功')
  } catch {
    ElMessage.error('操作失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

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
  <article class="group w-[140px] shrink-0 cursor-pointer sm:w-[150px]" @click="openDetail">
    <div
      ref="cardRef"
      class="relative overflow-hidden rounded-[10px] shadow-sm transition group-hover:shadow-lg"
      style="box-shadow: 0 2px 8px var(--fywz-card-shadow); ring: 1px solid var(--fywz-border)"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <img
        :src="poster"
        :alt="movie.title"
        class="aspect-[2/3] w-full object-cover transition duration-300 group-hover:scale-[1.03]"
        :class="{ 'opacity-0': showVideo }"
        loading="lazy"
      />

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

      <span
        v-if="savedScore > 0"
        class="absolute right-1.5 top-1.5 z-20 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-bold text-[#01B4E4]"
      >
        {{ savedScore.toFixed(1) }}
      </span>
      <div
        class="absolute inset-x-0 bottom-0 z-20 flex translate-y-full flex-col items-center bg-gradient-to-t from-black/95 via-black/70 to-transparent px-1 pb-2 pt-7 transition-transform duration-200 group-hover:translate-y-0"
        @click.stop
      >
        <span class="mb-1.5 text-xs font-medium text-white/90 sm:text-sm">我的评分</span>
        <el-rate
          :model-value="starScore"
          allow-half
          clearable
          :max="10"
          :disabled="saving"
          :colors="['#01B4E4', '#01B4E4', '#01B4E4']"
          void-color="#6b7280"
          disabled-void-color="#4b5563"
          class="card-star-rate"
          @change="onStarChange"
        />
      </div>
    </div>
    <div class="mt-2 px-0.5">
      <h3 class="line-clamp-2 text-[15px] font-bold leading-5">{{ movie.title }}</h3>
      <p class="mt-1 text-sm text-muted">{{ displayDate }}</p>
    </div>
  </article>
</template>

<style scoped>
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
  font-size: 0.95rem;
  margin-right: 0;
}

.card-star-rate :deep(.el-rate__decimal) {
  font-size: 0.95rem;
}
</style>
