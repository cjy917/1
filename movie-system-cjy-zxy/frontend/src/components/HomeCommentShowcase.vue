<!--
  【首页·区块3】底部短评气泡展示
  代码搜索: homeComments / COLUMNS
  API: movieApi.homeComments → GET /api/movies/home/comments
  速查索引: src/code-map.js (H4)
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { movieApi } from '../api'

const router = useRouter()

const COLUMNS = [
  { key: 'popular', title: '热门' },
  { key: 'top_rated', title: '高分' },
  { key: 'latest', title: '新上映' },
]

const commentPools = ref({
  popular: [],
  top_rated: [],
  latest: [],
})

const activeBubbles = ref({
  popular: [],
  top_rated: [],
  latest: [],
})

const loading = ref(true)
let bubbleSeq = 0
const timers = []

const SPAWN_INTERVAL_MIN = 850
const SPAWN_INTERVAL_MAX = 1250
const INITIAL_BURST = 3
const BUBBLE_HEIGHT = 21
const BUBBLE_GAP = 5

// ─── 气泡碰撞检测与位置计算 ─────────────────────────────────────────────────
function rectsOverlap(a, b) {
  return !(
    a.left + a.width + BUBBLE_GAP <= b.left
    || b.left + b.width + BUBBLE_GAP <= a.left
    || a.top + a.height + BUBBLE_GAP <= b.top
    || b.top + b.height + BUBBLE_GAP <= a.top
  )
}

function pickDispersedPosition(columnKey, width) {
  const existing = activeBubbles.value[columnKey]
  const height = BUBBLE_HEIGHT
  const maxLeft = Math.max(2, 94 - width)
  const maxTop = Math.max(2, 96 - height)

  let best = null
  let bestDistance = -1

  for (let attempt = 0; attempt < 28; attempt += 1) {
    const left = 2 + Math.random() * maxLeft
    const top = 2 + Math.random() * maxTop
    const candidate = { left, top, width, height }

    const overlapped = existing.some((item) => rectsOverlap(candidate, {
      left: item.left,
      top: item.top,
      width: item.width,
      height: item.height ?? BUBBLE_HEIGHT,
    }))

    if (!overlapped) {
      return { left, top }
    }

    const centerX = left + width / 2
    const centerY = top + height / 2
    let nearest = Infinity
    existing.forEach((item) => {
      const itemHeight = item.height ?? BUBBLE_HEIGHT
      const dx = centerX - (item.left + item.width / 2)
      const dy = centerY - (item.top + itemHeight / 2)
      nearest = Math.min(nearest, Math.hypot(dx, dy))
    })

    if (nearest > bestDistance) {
      bestDistance = nearest
      best = { left, top }
    }
  }

  if (best) return best
  return {
    left: 2 + Math.random() * maxLeft,
    top: 2 + Math.random() * maxTop,
  }
}

function truncate(text, max = 18) {
  const value = String(text || '')
  return value.length > max ? `${value.slice(0, max)}…` : value
}

function truncateContent(text, max = 72) {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  return value.length > max ? `${value.slice(0, max)}…` : value
}

function formatScore(score) {
  if (score == null || score === '') return null
  const num = Number(score)
  if (Number.isNaN(num)) return null
  return num.toFixed(1)
}

function posterUrl(bubble) {
  return bubble.poster_url || `/api/posters/${bubble.movie_id}`
}

function uniquePosters(pool, limit = 12) {
  const seen = new Set()
  const items = []
  for (const comment of pool) {
    const movieId = comment.movie_id
    if (!movieId || seen.has(movieId)) continue
    seen.add(movieId)
    items.push({
      movie_id: movieId,
      title: comment.movie_title,
      poster_url: posterUrl(comment),
    })
    if (items.length >= limit) break
  }
  return items
}

const sharedPosters = computed(() => {
  const merged = [
    ...uniquePosters(commentPools.value.popular, 6),
    ...uniquePosters(commentPools.value.top_rated, 6),
    ...uniquePosters(commentPools.value.latest, 6),
  ]
  const seen = new Set()
  return merged.filter((item) => {
    if (seen.has(item.movie_id)) return false
    seen.add(item.movie_id)
    return true
  }).slice(0, 12)
})

const filmstripPosters = computed(() => {
  const base = sharedPosters.value
  if (!base.length) return []
  return [...base, ...base, ...base]
})

function openComment(bubble) {
  if (!bubble?.movie_id || !bubble?.id) return
  router.push({
    name: 'movie-detail',
    params: { id: bubble.movie_id },
    hash: `#comment-${bubble.id}`,
  })
}

function spawnBubble(columnKey) {
  const pool = commentPools.value[columnKey]
  if (!pool?.length) return

  const comment = pool[Math.floor(Math.random() * pool.length)]
  const width = 58 + Math.random() * 22
  const { left, top } = pickDispersedPosition(columnKey, width)
  const duration = 3600 + Math.floor(Math.random() * 1200)

  const bubble = {
    id: ++bubbleSeq,
    ...comment,
    left,
    top,
    width,
    height: BUBBLE_HEIGHT,
    zIndex: bubbleSeq,
    duration,
  }

  activeBubbles.value[columnKey] = [...activeBubbles.value[columnKey], bubble]

  const timer = setTimeout(() => {
    activeBubbles.value[columnKey] = activeBubbles.value[columnKey].filter(
      (item) => item.id !== bubble.id,
    )
  }, duration)
  timers.push(timer)
}

function nextSpawnDelay() {
  return SPAWN_INTERVAL_MIN + Math.random() * (SPAWN_INTERVAL_MAX - SPAWN_INTERVAL_MIN)
}

function startColumnLoop(columnKey, initialDelay = 0) {
  const tick = (delay) => {
    const timer = setTimeout(() => {
      spawnBubble(columnKey)
      tick(nextSpawnDelay())
    }, delay)
    timers.push(timer)
  }
  tick(initialDelay)
}

function burstColumn(columnKey, count, startDelay = 0) {
  for (let i = 0; i < count; i += 1) {
    const timer = setTimeout(() => spawnBubble(columnKey), startDelay + i * 420)
    timers.push(timer)
  }
}

onMounted(async () => {
  try {
    const { data } = await movieApi.homeComments()
    commentPools.value = {
      popular: data.popular || [],
      top_rated: data.top_rated || [],
      latest: data.latest || [],
    }
  } finally {
    loading.value = false
  }

  COLUMNS.forEach((column, index) => {
    burstColumn(column.key, INITIAL_BURST, 200 + index * 350)
    startColumnLoop(column.key, 900 + index * 400)
  })
})

onBeforeUnmount(() => {
  timers.forEach((timer) => clearTimeout(timer))
})
</script>

<template>
  <section class="comment-showcase py-10">
    <div class="comment-showcase__content mx-auto max-w-[1400px] px-4 lg:px-8">
      <div class="comment-showcase__body">
        <div class="comment-showcase__filmstrip" aria-hidden="true">
          <div class="comment-showcase__filmstrip-track">
            <img
              v-for="(poster, index) in filmstripPosters"
              :key="`film-${poster.movie_id}-${index}`"
              :src="poster.poster_url"
              :alt="poster.title"
              class="comment-showcase__filmstrip-poster"
              loading="lazy"
            />
          </div>
          <div class="comment-showcase__filmstrip-fade" />
        </div>

        <div class="comment-showcase__body-content">
          <div class="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 class="text-2xl font-bold">影迷热议</h2>
              <p class="mt-1 text-sm text-muted">热门、高分、新上映影片的实时短评</p>
            </div>
          </div>

          <div class="comment-showcase__panel">
            <div class="comment-showcase__grid grid grid-cols-1 gap-5 md:grid-cols-3">
          <div
            v-for="column in COLUMNS"
            :key="column.key"
            class="comment-column"
          >
            <div class="comment-column__header">
              <span class="comment-column__dot" />
              {{ column.title }}
            </div>

            <div class="comment-column__stage">
              <div
                v-for="bubble in activeBubbles[column.key]"
                :key="bubble.id"
                class="comment-bubble-wrap"
                role="button"
                tabindex="0"
                :style="{
                  left: `${bubble.left}%`,
                  top: `${bubble.top}%`,
                  width: `${bubble.width}%`,
                  zIndex: bubble.zIndex,
                  animationDuration: `${bubble.duration}ms`,
                }"
                @click="openComment(bubble)"
                @keydown.enter="openComment(bubble)"
              >
                <div class="comment-bubble-meta">
                  <img
                    :src="posterUrl(bubble)"
                    :alt="bubble.movie_title"
                    class="comment-bubble-poster"
                    loading="lazy"
                  />
                  <span class="comment-bubble-movie">《{{ truncate(bubble.movie_title) }}》</span>
                  <span class="comment-bubble-user">{{ bubble.username }}</span>
                  <span v-if="formatScore(bubble.score)" class="comment-bubble-score">
                    {{ formatScore(bubble.score) }} 分
                  </span>
                </div>
                <div class="comment-bubble">
                  <p>{{ truncateContent(bubble.content) }}</p>
                </div>
              </div>

              <p v-if="loading" class="comment-column__placeholder">评论加载中…</p>
              <p
                v-else-if="!commentPools[column.key]?.length"
                class="comment-column__placeholder"
              >
                暂无评论
              </p>
            </div>
          </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.comment-showcase {
  position: relative;
}

.comment-showcase__content {
  position: relative;
}

.comment-showcase__body {
  position: relative;
}

.comment-showcase__body-content {
  position: relative;
  z-index: 1;
}

.comment-showcase__panel {
  position: relative;
}

.comment-showcase__filmstrip {
  position: absolute;
  inset: 0 0 auto;
  z-index: 0;
  height: 7.5rem;
  overflow: hidden;
  pointer-events: none;
}

.comment-showcase__filmstrip-track {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  width: max-content;
  min-height: 100%;
  padding: 0.35rem 0;
  animation: filmstrip-scroll 42s linear infinite;
}

.comment-showcase__filmstrip-poster {
  width: 3rem;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  object-fit: cover;
  border-radius: 0.4rem;
  opacity: 0.26;
  filter: saturate(0.8) brightness(1.1);
}

.comment-showcase__filmstrip-fade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, var(--fywz-bg) 0%, transparent 8%, transparent 92%, var(--fywz-bg) 100%),
    linear-gradient(180deg, transparent 55%, var(--fywz-bg) 100%);
}

.comment-showcase__grid {
  position: relative;
}

.comment-column {
  min-width: 0;
}

@media (min-width: 768px) {
  .comment-column + .comment-column {
    border-left: 1px solid color-mix(in srgb, var(--fywz-border) 65%, transparent);
    padding-left: 1.25rem;
  }
}

.comment-column__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.comment-column__dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  background: var(--fywz-accent);
  box-shadow: 0 0 10px rgba(1, 180, 228, 0.45);
}

.comment-column__stage {
  position: relative;
  height: 32rem;
  overflow: hidden;
}

.comment-column__placeholder {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  font-size: 0.9rem;
  color: var(--fywz-muted);
}

.comment-bubble-wrap {
  position: absolute;
  z-index: 2;
  cursor: pointer;
  animation-name: bubble-life;
  animation-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
  animation-fill-mode: forwards;
}

.comment-bubble-wrap:focus-visible {
  outline: 2px solid var(--fywz-accent);
  outline-offset: 2px;
  border-radius: 0.75rem;
}

.comment-bubble-wrap:hover .comment-bubble {
  border-color: rgba(1, 180, 228, 0.55);
  box-shadow: 0 12px 32px var(--fywz-card-shadow);
}

.comment-bubble-meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.35rem;
  font-size: 0.68rem;
  line-height: 1.2;
  color: var(--fywz-muted);
  min-width: 0;
}

.comment-bubble-poster {
  width: 1.35rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 0.25rem;
  object-fit: cover;
  border: 1px solid var(--fywz-border);
  box-shadow: 0 2px 6px var(--fywz-card-shadow);
}

.comment-bubble-movie {
  color: var(--fywz-text);
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.comment-bubble-user {
  opacity: 0.92;
  flex-shrink: 0;
}

.comment-bubble-score {
  color: #01b4e4;
  font-weight: 700;
  flex-shrink: 0;
}

.comment-bubble {
  position: relative;
  padding: 0.65rem 0.85rem;
  border-radius: 1rem 1rem 1rem 0.35rem;
  border: 1px solid var(--fywz-border);
  background: var(--fywz-surface);
  box-shadow: 0 10px 28px var(--fywz-card-shadow);
}

.comment-bubble::after {
  content: '';
  position: absolute;
  left: 0.85rem;
  bottom: -0.45rem;
  width: 0.75rem;
  height: 0.75rem;
  background: var(--fywz-surface);
  border-right: 1px solid var(--fywz-border);
  border-bottom: 1px solid var(--fywz-border);
  transform: rotate(45deg);
}

.comment-bubble p {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--fywz-text);
  word-break: break-word;
}

@keyframes filmstrip-scroll {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(-33.333%);
  }
}

@keyframes bubble-life {
  0% {
    opacity: 0;
    transform: scale(0.3) translateY(16px);
  }

  12% {
    opacity: 1;
    transform: scale(1.06) translateY(0);
  }

  20% {
    transform: scale(1) translateY(0);
  }

  62% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }

  100% {
    opacity: 0;
    transform: scale(0.96) translateY(0);
  }
}

@media (max-width: 767px) {
  .comment-column__stage {
    height: 26rem;
  }

  .comment-column + .comment-column {
    margin-top: 0.5rem;
    padding-top: 1rem;
    border-top: 1px solid color-mix(in srgb, var(--fywz-border) 65%, transparent);
  }
}
</style>
