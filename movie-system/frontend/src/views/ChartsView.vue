<script setup>
/**
 * 影人列表页（/charts）
 * - 进入时请求一次 GET /api/charts/filmmakers，同时拿到导演榜 + 演员榜
 * - 顶部「导演」「演员」按钮只做页面内滚动，不会重新请求后端
 */
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { chartsApi } from '../api'
import FilmmakerPersonCard from '../components/FilmmakerPersonCard.vue'

const route = useRoute()
const directors = ref([])
const actors = ref([])
const directorTotal = ref(0)
const actorTotal = ref(0)
const loading = ref(true)
const loadError = ref('')
const activeAnchor = ref('chart-filmmakers-directors')

/** 数字千分位，用于「库内共 5,340 位」 */
function formatTotal(value) {
  return Number(value || 0).toLocaleString()
}

/** 点击导演/演员 Tab：高亮按钮 + 平滑滚到对应区块 */
function scrollToSection(anchor) {
  activeAnchor.value = anchor
  const el = document.getElementById(anchor)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function applyRouteHash() {
  const hash = route.hash?.replace('#', '')
  if (!hash || loading.value) return
  if (hash === 'chart-filmmakers-directors' || hash === 'chart-filmmakers-actors') {
    setTimeout(() => scrollToSection(hash), 100)
  }
}

onMounted(async () => {
  loadError.value = ''
  try {
    // 影人板块唯一的数据请求：导演 directors + 演员 actors 一次返回
    const { data } = await chartsApi.filmmakers()
    if (!data?.directors && typeof data === 'string') {
      throw new Error('后端返回异常，请重启 Flask 服务')
    }
    directors.value = data.directors || []
    actors.value = data.actors || []
    directorTotal.value = Number(data.director_total) || 0
    actorTotal.value = Number(data.actor_total) || 0
  } catch (err) {
    loadError.value = err?.response?.data?.error || err?.message || '加载榜单失败，请确认后端已启动'
    directors.value = []
    actors.value = []
  } finally {
    loading.value = false
    applyRouteHash()
  }
})
</script>

<template>
  <div class="charts-page">
    <section class="charts-nav sticky top-[72px] z-30">
      <div class="mx-auto max-w-[1400px] px-4 py-5 lg:px-8">
        <div class="charts-tabs">
          <button
            type="button"
            class="charts-tab"
            :class="{ 'charts-tab--active': activeAnchor === 'chart-filmmakers-directors' }"
            @click="scrollToSection('chart-filmmakers-directors')"
          >
            导演
          </button>
          <button
            type="button"
            class="charts-tab"
            :class="{ 'charts-tab--active': activeAnchor === 'chart-filmmakers-actors' }"
            @click="scrollToSection('chart-filmmakers-actors')"
          >
            演员
          </button>
        </div>
      </div>
    </section>

    <div v-if="loading" class="charts-loading">
      <div class="charts-loading__grid">
        <div v-for="n in 10" :key="n" class="charts-skeleton" />
      </div>
    </div>

    <div v-else-if="loadError" class="mx-auto max-w-[1400px] px-4 py-16 text-center lg:px-8">
      <p class="text-muted">{{ loadError }}</p>
      <p class="mt-2 text-sm text-muted">
        请在 backend 目录执行 <span class="charts-hint-code">python app.py</span> 重启后端
      </p>
    </div>

    <template v-else>
      <section id="chart-filmmakers-directors" class="people-section scroll-mt-28">
        <div class="mx-auto max-w-[1400px] px-4 lg:px-8">
          <div class="people-section__head">
            <h2 class="people-section__title">导演</h2>
            <span class="people-section__meta">库内共 {{ formatTotal(directorTotal) }} 位 · 本页 Top {{ directors.length }}</span>
          </div>
          <div v-if="directors.length" class="people-grid">
            <FilmmakerPersonCard
              v-for="(person, index) in directors"
              :key="person.name"
              :person="person"
              role="director"
              :rank="index + 1"
            />
          </div>
          <p v-else class="py-12 text-center text-sm text-muted">暂无导演数据</p>
        </div>
      </section>

      <section id="chart-filmmakers-actors" class="people-section people-section--alt scroll-mt-28">
        <div class="mx-auto max-w-[1400px] px-4 lg:px-8">
          <div class="people-section__head">
            <h2 class="people-section__title">演员</h2>
            <span class="people-section__meta">库内共 {{ formatTotal(actorTotal) }} 位 · 本页 Top {{ actors.length }}</span>
          </div>
          <div v-if="actors.length" class="people-grid">
            <FilmmakerPersonCard
              v-for="(person, index) in actors"
              :key="person.name"
              :person="person"
              role="actor"
              :rank="index + 1"
            />
          </div>
          <p v-else class="py-12 text-center text-sm text-muted">暂无演员数据</p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.charts-page {
  padding-bottom: 3rem;
}

.charts-nav {
  border-bottom: 1px solid var(--fywz-border);
  background: color-mix(in srgb, var(--fywz-bg) 92%, transparent);
  backdrop-filter: blur(12px);
}

.charts-tabs {
  display: inline-flex;
  gap: 0.35rem;
  padding: 0.35rem;
  border-radius: 999px;
  border: 1px solid var(--fywz-border);
  background: var(--fywz-surface-2);
}

.charts-tab {
  min-width: 5.5rem;
  border: none;
  border-radius: 999px;
  padding: 0.5rem 1.25rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--fywz-text-muted);
  background: transparent;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.charts-tab--active {
  color: var(--fywz-accent-text);
  background: linear-gradient(135deg, #01b4e4, #0096c7);
  box-shadow: 0 6px 18px rgba(1, 180, 228, 0.35);
}

.charts-tab:not(.charts-tab--active):hover {
  color: var(--fywz-text);
  background: var(--fywz-tab-hover);
}

.charts-hint-code {
  border-radius: 0.25rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 0.125rem 0.375rem;
  font-family: ui-monospace, monospace;
  font-size: 0.875em;
}

.charts-loading {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem 1rem 0;
}

.charts-loading__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.charts-skeleton {
  aspect-ratio: 4 / 5.8;
  border-radius: 1rem;
  background: linear-gradient(
    110deg,
    var(--fywz-surface-2) 8%,
    color-mix(in srgb, var(--fywz-border) 60%, transparent) 18%,
    var(--fywz-surface-2) 33%
  );
  background-size: 200% 100%;
  animation: charts-shimmer 1.4s ease infinite;
}

@keyframes charts-shimmer {
  to {
    background-position-x: -200%;
  }
}

.people-section {
  padding: 2rem 0 2.5rem;
}

.people-section--alt {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--fywz-surface-2) 65%, transparent) 0%,
    transparent 100%
  );
}

.people-section__head {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 1.35rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--fywz-border);
  position: relative;
}

.people-section__head::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 3.5rem;
  height: 2px;
  border-radius: 999px;
  background: #01b4e4;
}

.people-section__title {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: var(--fywz-text);
}

.people-section__meta {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--fywz-text-muted);
}

.people-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

@media (min-width: 640px) {
  .charts-loading__grid,
  .people-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.15rem;
  }
}

@media (min-width: 1024px) {
  .charts-loading__grid,
  .people-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1.25rem;
  }
}

@media (min-width: 1280px) {
  .charts-loading__grid,
  .people-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}
</style>
