<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { movieApi } from '../api'
import { applyLocalTrailerIfExists, tryLocalTrailerFallback } from '../utils/trailerCache'
import MediaPlayer from './MediaPlayer.vue'

const props = defineProps({
  movies: { type: Array, default: () => [] },
})

const emit = defineEmits(['change'])
const router = useRouter()

const index = ref(0)
const trailer = ref(null)
const loadingTrailer = ref(false)
const online = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)
const trailerPlaying = ref(false)
const posterShownAt = ref(0)
/** 与 YouTube iframe 确认延迟对齐，保证先看到封面再切视频 */
const POSTER_MIN_MS = 1000
let trailerLoadSeq = 0
let posterHoldTimer = null

const current = computed(() => props.movies[index.value] || null)
const poster = computed(() =>
  current.value ? current.value.poster_url || `/api/posters/${current.value.movie_id}` : '',
)

const genres = computed(() => {
  const raw = current.value?.genres || ''
  return raw.split('|').filter(Boolean).slice(0, 2).join(' · ')
})

function posterOf(movie) {
  return movie?.poster_url || `/api/posters/${movie?.movie_id}`
}

function stripTitle(title) {
  if (!title) return ''
  const short = title.split(/[\s|/]/)[0]
  return short.length > 10 ? `${short.slice(0, 10)}…` : short
}

function isPlayable(data) {
  return data && data.type !== 'none' && (data.embed_url || data.stream_url)
}

const canPlayTrailer = computed(() => isPlayable(trailer.value))

function isLocalTrailer(data) {
  return data?.type === 'mp4'
}

function isRemoteTrailer(data) {
  return ['youtube', 'bilibili'].includes(data?.type)
}

const shouldTryTrailer = computed(() => {
  if (!canPlayTrailer.value) return false
  if (isLocalTrailer(trailer.value)) return true
  return online.value && isRemoteTrailer(trailer.value)
})

const showVideo = computed(() => shouldTryTrailer.value && trailerPlaying.value)

const backdropUrl = computed(() => trailer.value?.backdrop_url || '')

const useSharpBackdrop = computed(() =>
  /image\.tmdb\.org\/t\/p\/w1280\//.test(backdropUrl.value),
)

function clearPosterHoldTimer() {
  if (posterHoldTimer) {
    clearTimeout(posterHoldTimer)
    posterHoldTimer = null
  }
}

function syncOnline() {
  online.value = navigator.onLine
  if (!online.value) {
    if (!isLocalTrailer(trailer.value)) {
      trailerPlaying.value = false
    }
    return
  }
  if (current.value && !trailer.value) {
    loadTrailer()
  }
}

watch(current, (movie) => {
  clearPosterHoldTimer()
  trailer.value = null
  trailerPlaying.value = false
  posterShownAt.value = Date.now()
  if (movie) {
    emit('change', movie)
    loadTrailer()
  }
}, { immediate: true })

onMounted(() => {
  window.addEventListener('online', syncOnline)
  window.addEventListener('offline', syncOnline)
})

onBeforeUnmount(() => {
  clearPosterHoldTimer()
  window.removeEventListener('online', syncOnline)
  window.removeEventListener('offline', syncOnline)
})

function openDetail() {
  if (current.value) {
    const mid = Number(current.value.movie_id)
    if (!mid || Number.isNaN(mid)) {
      console.warn('[HeroCarousel] 无效movie_id，取消跳转', current.value)
      return
    }
    router.push({ name: 'movie-detail', params: { id: mid } })
  }
}

async function loadTrailer() {
  if (!current.value) return
  const movieId = current.value.movie_id
  const seq = ++trailerLoadSeq
  loadingTrailer.value = true

  const instant = applyLocalTrailerIfExists(movieId)
  if (instant) {
    if (seq !== trailerLoadSeq) return
    trailer.value = instant
    loadingTrailer.value = false
    return
  }

  try {
    const { data } = await movieApi.trailer(movieId, { autoplay: 1, refresh: 1 })
    if (seq !== trailerLoadSeq) return
    trailer.value = data
  } catch {
    if (seq !== trailerLoadSeq) return
    const local = await tryLocalTrailerFallback(movieId)
    if (local) {
      trailer.value = local
      return
    }
    trailer.value = { type: 'none', message: '预告加载失败' }
  } finally {
    if (seq === trailerLoadSeq) {
      loadingTrailer.value = false
    }
  }
}

function onPlaybackConfirmed() {
  clearPosterHoldTimer()
  const elapsed = Date.now() - posterShownAt.value
  const wait = Math.max(0, POSTER_MIN_MS - elapsed)
  if (wait > 0) {
    posterHoldTimer = setTimeout(() => {
      posterHoldTimer = null
      trailerPlaying.value = true
    }, wait)
  } else {
    trailerPlaying.value = true
  }
}

function onPlaybackFailed() {
  trailerPlaying.value = false
}

function onHeroClick(event) {
  if (event.target.closest('.hero-arrow, .hero-strip, button, a')) return
  if (!showVideo.value) openDetail()
}

function prev() {
  if (!props.movies.length) return
  index.value = (index.value - 1 + props.movies.length) % props.movies.length
}

function next() {
  if (!props.movies.length) return
  index.value = (index.value + 1) % props.movies.length
}
</script>

<template>
  <section
    v-if="current"
    class="hero relative overflow-hidden"
    :class="{ 'hero--playing': showVideo }"
    @click="onHeroClick"
  >
    <div
      class="hero-backdrop"
      :class="{
        'hero-backdrop--video': showVideo,
        'hero-backdrop--poster': !useSharpBackdrop,
      }"
    >
      <img
        v-if="useSharpBackdrop"
        :key="`${current.movie_id}-wide`"
        :src="backdropUrl"
        class="hero-backdrop-img"
        alt=""
      />
      <div v-else :key="`${current.movie_id}-poster`" class="hero-poster-scene">
        <img
          :src="poster"
          class="hero-backdrop-img hero-backdrop-img--blur-fill"
          alt=""
        />
        <img
          :src="poster"
          class="hero-poster-feature"
          alt=""
        />
      </div>
      <div class="hero-backdrop-vignette" />
    </div>

    <div
      v-if="shouldTryTrailer"
      class="hero-video-wrap"
      :class="{ 'hero-video-wrap--active': showVideo }"
    >
      <MediaPlayer
        :source="trailer"
        autoplay
        muted
        loop
        cover
        hero-mode
        :play-check-ms="8000"
        :enable-fallback="false"
        @playback-confirmed="onPlaybackConfirmed"
        @playback-failed="onPlaybackFailed"
      />
    </div>

    <div class="pointer-events-none absolute inset-0 z-[2] hero-overlay-bottom" />
    <div class="pointer-events-none absolute inset-0 z-[2] hero-overlay-left" />

    <button class="hero-arrow left-4" aria-label="上一部" @click.stop="prev">‹</button>
    <button class="hero-arrow right-4" aria-label="下一部" @click.stop="next">›</button>

    <div class="hero-content">
      <h1 class="hero-title">{{ current.title }}</h1>
      <div class="hero-meta">
        <span class="hero-rating">{{ Number(current.rating).toFixed(1) }}</span>
        <span v-if="current.release_year">{{ current.release_year }}</span>
        <span v-if="genres">{{ genres }}</span>
      </div>
      <button class="hero-cta" @click.stop="openDetail">查看详情</button>
    </div>

    <div class="hero-strip">
      <button
        v-for="(m, i) in movies"
        :key="m.movie_id"
        class="hero-strip-item"
        :class="{ 'hero-strip-item--active': i === index }"
        @click.stop="index = i"
      >
        <div class="hero-strip-thumb">
          <img :src="posterOf(m)" :alt="m.title" loading="lazy" />
        </div>
        <span class="hero-strip-label">{{ stripTitle(m.title) }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.hero {
  height: min(78vh, 620px);
  min-height: 440px;
  background: #031d31;
  cursor: pointer;
}

.hero-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background: #031d31;
  transition: opacity 0.55s ease;
}

.hero-backdrop--video {
  opacity: 0;
  pointer-events: none;
}

.hero-backdrop-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
  transition: opacity 0.55s ease, filter 0.55s ease;
}

.hero-poster-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.hero-backdrop-img--blur-fill {
  inset: -22%;
  width: 144%;
  height: 144%;
  filter: blur(64px) saturate(1.25) brightness(0.42);
  transform: scale(1.12);
  object-fit: cover;
  object-position: center center;
}

.hero-poster-feature {
  position: absolute;
  top: 50%;
  right: max(5%, 8vw);
  z-index: 1;
  height: min(90%, 540px);
  width: auto;
  max-width: min(40vw, 360px);
  transform: translateY(calc(-50% - 1.25rem));
  object-fit: contain;
  border-radius: 0.45rem;
  box-shadow:
    0 24px 64px rgba(0, 0, 0, 0.55),
    0 8px 24px rgba(0, 0, 0, 0.35),
    0 0 0 1px rgba(255, 255, 255, 0.1);
  transition: opacity 0.55s ease, transform 0.55s ease;
}

.hero-backdrop--poster .hero-backdrop-vignette {
  background:
    linear-gradient(to top, rgba(3, 29, 49, 0.92) 0%, rgba(3, 29, 49, 0.35) 40%, rgba(3, 29, 49, 0.08) 100%),
    linear-gradient(to right, rgba(3, 29, 49, 0.72) 0%, rgba(3, 29, 49, 0.28) 38%, transparent 58%);
}

.hero-backdrop-vignette {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to top, rgba(3, 29, 49, 0.9) 0%, rgba(3, 29, 49, 0.28) 42%, rgba(3, 29, 49, 0.12) 100%),
    linear-gradient(to right, rgba(3, 29, 49, 0.55) 0%, transparent 42%);
}

.hero-video-wrap {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: transparent;
  opacity: 0;
  transition: opacity 0.55s ease;
  pointer-events: none;
}

.hero-video-wrap--active {
  opacity: 1;
}

.hero--playing .hero-overlay-bottom {
  background: linear-gradient(
    to top,
    rgba(3, 29, 49, 0.88) 0%,
    rgba(3, 29, 49, 0.28) 32%,
    transparent 62%
  );
}

.hero--playing .hero-overlay-left {
  background: linear-gradient(
    to right,
    rgba(3, 29, 49, 0.42) 0%,
    rgba(3, 29, 49, 0.12) 24%,
    transparent 40%
  );
}

.hero-overlay-bottom {
  background: linear-gradient(
    to top,
    rgba(3, 29, 49, 0.92) 0%,
    rgba(3, 29, 49, 0.45) 28%,
    transparent 58%
  );
}

.hero-overlay-left {
  background: linear-gradient(
    to right,
    rgba(3, 29, 49, 0.55) 0%,
    rgba(3, 29, 49, 0.2) 22%,
    transparent 42%
  );
}

.hero-content {
  position: absolute;
  z-index: 10;
  left: max(1.5rem, 4vw);
  bottom: 7.5rem;
  max-width: min(520px, 46vw);
  color: white;
  pointer-events: auto;
}

.hero-title {
  font-size: clamp(1.75rem, 3.6vw, 2.75rem);
  font-weight: 800;
  line-height: 1.15;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.55);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.88);
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.5);
}

.hero-rating {
  border-radius: 0.25rem;
  background: #01b4e4;
  padding: 0.1rem 0.45rem;
  font-weight: 700;
  color: #032541;
}

.hero-cta {
  margin-top: 1.1rem;
  border-radius: 0.35rem;
  background: #01b4e4;
  padding: 0.55rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 700;
  color: #032541;
  box-shadow: 0 6px 20px rgba(1, 180, 228, 0.35);
  transition: filter 0.2s, transform 0.2s;
  cursor: pointer;
}

.hero-cta:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.hero-strip {
  position: absolute;
  z-index: 15;
  left: max(1.5rem, 4vw);
  right: max(1.5rem, 4vw);
  bottom: 1rem;
  display: flex;
  gap: 0.65rem;
  overflow-x: auto;
  padding-bottom: 0.25rem;
  scrollbar-width: none;
  pointer-events: auto;
}

.hero-strip::-webkit-scrollbar {
  display: none;
}

.hero-strip-item {
  flex: 0 0 auto;
  width: 5.5rem;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  text-align: left;
  opacity: 0.72;
  transition: opacity 0.2s, transform 0.2s;
}

.hero-strip-item:hover {
  opacity: 0.92;
}

.hero-strip-item--active {
  opacity: 1;
  transform: translateY(-2px);
}

.hero-strip-thumb {
  overflow: hidden;
  border-radius: 0.35rem;
  border: 2px solid transparent;
  aspect-ratio: 16 / 10;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.hero-strip-item--active .hero-strip-thumb {
  border-color: #01b4e4;
  box-shadow: 0 0 0 1px rgba(1, 180, 228, 0.4);
}

.hero-strip-thumb img {
  display: block;
  height: 100%;
  width: 100%;
  object-fit: cover;
}

.hero-strip-label {
  display: block;
  margin-top: 0.35rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.85);
}

.hero-strip-item--active .hero-strip-label {
  color: #01b4e4;
  font-weight: 600;
}

.hero-arrow {
  position: absolute;
  top: 50%;
  z-index: 20;
  display: flex;
  height: 2.75rem;
  width: 2.75rem;
  transform: translateY(-50%);
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.35);
  font-size: 1.5rem;
  line-height: 1;
  color: white;
  backdrop-filter: blur(6px);
  opacity: 0;
  transition: opacity 0.25s, background 0.2s, transform 0.2s;
  cursor: pointer;
}

.hero:hover .hero-arrow {
  opacity: 1;
}

.hero-arrow:hover {
  background: rgba(1, 180, 228, 0.88);
  transform: translateY(-50%) scale(1.05);
}

@media (max-width: 640px) {
  .hero-content {
    bottom: 6.5rem;
    max-width: calc(100% - 2rem);
  }

  .hero-poster-feature {
    right: 1rem;
    height: min(72%, 400px);
    max-width: min(46vw, 200px);
    transform: translateY(calc(-50% - 0.75rem));
    opacity: 0.92;
  }

  .hero-strip-item {
    width: 4.5rem;
  }
}
</style>
