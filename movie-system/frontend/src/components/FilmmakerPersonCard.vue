<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { posterThumbSrc } from '../utils/mediaUrl'

const props = defineProps({
  person: { type: Object, required: true },
  role: { type: String, required: true },
  rank: { type: Number, default: 0 },
  relation: { type: Boolean, default: false },
  subjectName: { type: String, default: '' },
})

const mosaicRef = ref(null)
const mosaicVisible = ref(false)
let mosaicObserver = null

const detailRoute = computed(() => ({
  name: 'chart-filmmaker-detail',
  params: { role: props.role, name: props.person.name },
  // 相关影人卡片：进入详情后滚到作品列表
  hash: props.relation ? '#filmmaker-works' : undefined,
}))

const posterTiles = computed(() =>
  (props.person.sample_movies || [])
    .filter((movie) => movie.movie_id)
    .slice(0, 4)
    .map((movie) => ({
      key: movie.movie_id,
      src: posterThumbSrc(movie.movie_id, 220),
      alt: movie.title || props.person.name,
    })),
)

const displayLinks = computed(() => (props.person.links || []).slice(0, 3))

function linkLabel(link) {
  if (link.type === 'co_direct') {
    return `两人共同执导《${link.movie_title}》`
  }
  if (link.type === 'co_star') {
    return `两人共同出演《${link.movie_title}》`
  }
  if (link.type === 'shared_actor') {
    const currentName = props.subjectName || '本页影人'
    return `因演员 ${link.via_actor}：${currentName}《${link.subject_movie_title}》/ ${props.person.name}《${link.peer_movie_title}》`
  }
  return link.movie_title || ''
}

const worksText = computed(() => {
  const titles = (props.person.sample_movies || []).map((movie) => movie.title).filter(Boolean)
  if (titles.length) return titles.join(' · ')
  return '暂无代表作品'
})

const rankClass = computed(() => {
  if (props.rank === 1) return 'person-card--rank-1'
  if (props.rank === 2) return 'person-card--rank-2'
  if (props.rank === 3) return 'person-card--rank-3'
  return ''
})

const countLabel = computed(() => {
  if (props.relation && props.person.collaboration_count) {
    return `关联 ${props.person.collaboration_count}`
  }
  return `${props.person.movie_count} 部`
})

const posterFetchPriority = computed(() => (props.rank > 0 && props.rank <= 6 ? 'high' : 'low'))

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') {
    mosaicVisible.value = true
    return
  }
  mosaicObserver = new IntersectionObserver(
    ([entry]) => {
      if (entry?.isIntersecting) {
        mosaicVisible.value = true
        mosaicObserver?.disconnect()
        mosaicObserver = null
      }
    },
    { rootMargin: '120px 0px', threshold: 0.01 },
  )
  if (mosaicRef.value) {
    mosaicObserver.observe(mosaicRef.value)
  }
})

onBeforeUnmount(() => {
  mosaicObserver?.disconnect()
  mosaicObserver = null
})

function onPosterLoad(event) {
  event.target.classList.add('person-card__poster--loaded')
}
</script>

<template>
  <router-link :to="detailRoute" class="person-card" :class="rankClass">
    <div ref="mosaicRef" class="person-card__visual">
      <div
        v-if="posterTiles.length && mosaicVisible"
        class="person-card__mosaic"
        :class="`person-card__mosaic--${Math.min(posterTiles.length, 4)}`"
      >
        <img
          v-for="tile in posterTiles"
          :key="tile.key"
          :src="tile.src"
          :alt="tile.alt"
          class="person-card__poster"
          loading="lazy"
          decoding="async"
          :fetchpriority="posterFetchPriority"
          @load="onPosterLoad"
        />
      </div>
      <div v-else-if="!posterTiles.length" class="person-card__fallback" />
      <div v-else class="person-card__mosaic person-card__mosaic--placeholder" />

      <div class="person-card__shade" />

      <span v-if="rank > 0 && rank <= 3" class="person-card__badge">{{ rank }}</span>
      <span class="person-card__count">{{ countLabel }}</span>
    </div>

    <div class="person-card__body">
      <h3 class="person-card__name">{{ person.name }}</h3>
      <template v-if="relation && person.relation_summary">
        <p class="person-card__relation-summary">{{ person.relation_summary }}</p>
        <ul class="person-card__links">
          <li v-for="(link, index) in displayLinks" :key="`${link.type}-${index}`">
            <p class="person-card__link-text">{{ linkLabel(link) }}</p>
          </li>
        </ul>
      </template>
      <p v-else class="person-card__works">{{ worksText }}</p>
      <p v-if="relation" class="person-card__action">点击查看全部作品 →</p>
    </div>
  </router-link>
</template>

<style scoped>
.person-card {
  display: block;
  overflow: hidden;
  border-radius: 1rem;
  background: var(--fywz-surface);
  border: 1px solid var(--fywz-border);
  text-decoration: none;
  color: inherit;
  box-shadow: 0 8px 24px var(--fywz-card-shadow);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.person-card:hover {
  transform: translateY(-6px);
  border-color: rgba(1, 180, 228, 0.55);
  box-shadow: 0 18px 40px rgba(1, 180, 228, 0.16);
}

.person-card--rank-1 {
  border-color: rgba(255, 196, 77, 0.55);
}

.person-card--rank-2 {
  border-color: rgba(192, 200, 212, 0.65);
}

.person-card--rank-3 {
  border-color: rgba(205, 127, 80, 0.55);
}

.person-card__visual {
  position: relative;
  aspect-ratio: 4 / 5;
  overflow: hidden;
  background: linear-gradient(145deg, #0d253f 0%, #1a4a6e 100%);
}

.person-card__mosaic {
  position: absolute;
  inset: 0;
  display: grid;
  gap: 2px;
}

.person-card__mosaic--placeholder {
  background:
    linear-gradient(110deg, rgba(255, 255, 255, 0.04) 25%, rgba(255, 255, 255, 0.1) 37%, rgba(255, 255, 255, 0.04) 63%);
  background-size: 200% 100%;
  animation: person-card-shimmer 1.2s ease-in-out infinite;
}

.person-card__mosaic--1 {
  grid-template-columns: 1fr;
}

.person-card__mosaic--2 {
  grid-template-columns: repeat(2, 1fr);
}

.person-card__mosaic--3,
.person-card__mosaic--4 {
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
}

.person-card__poster {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(1.05);
  opacity: 0;
  transition: opacity 0.35s ease, transform 0.35s ease;
}

.person-card__poster--loaded {
  opacity: 1;
}

.person-card:hover .person-card__poster {
  transform: scale(1.06);
}

.person-card__fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 20%, rgba(1, 180, 228, 0.35), transparent 45%),
    linear-gradient(160deg, #0d253f 0%, #132f4c 55%, #01b4e4 160%);
}

.person-card__shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(3, 37, 65, 0.08) 55%,
    rgba(3, 37, 65, 0.45) 100%
  );
}

.person-card__badge {
  position: absolute;
  top: 0.65rem;
  left: 0.65rem;
  z-index: 3;
  min-width: 1.65rem;
  height: 1.65rem;
  padding: 0 0.4rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #ffc44d, #ff9f1a);
  color: #032541;
  font-size: 0.75rem;
  font-weight: 800;
  line-height: 1.65rem;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.person-card--rank-2 .person-card__badge {
  background: linear-gradient(135deg, #e8edf3, #b8c4d4);
}

.person-card--rank-3 .person-card__badge {
  background: linear-gradient(135deg, #e8a87c, #cd7f50);
}

.person-card__count {
  position: absolute;
  top: 0.65rem;
  right: 0.65rem;
  z-index: 3;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  background: rgba(3, 37, 65, 0.72);
  backdrop-filter: blur(6px);
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.6875rem;
  font-weight: 600;
}

.person-card__body {
  padding: 0.85rem 0.95rem 1rem;
}

.person-card__name {
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.35;
  color: var(--fywz-text);
}

.person-card__relation-summary {
  margin-top: 0.4rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: #01b4e4;
}

.person-card__links {
  margin: 0.45rem 0 0;
  padding: 0;
  list-style: none;
}

.person-card__links li {
  margin-top: 0.45rem;
}

.person-card__link-text {
  font-size: 0.6875rem;
  line-height: 1.55;
  color: var(--fywz-text-muted);
}

.person-card__works {
  margin-top: 0.4rem;
  font-size: 0.75rem;
  line-height: 1.55;
  color: var(--fywz-text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.person-card__action {
  margin-top: 0.55rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #01b4e4;
}

@keyframes person-card-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
