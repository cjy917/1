<template>
  <div class="analytics-view">
    <main class="main-content">
      <header class="page-header">
        <p class="eyebrow">FYWZ movies · 数据洞察</p>
        <h1 class="display-2">电影数据分析</h1>
        <p v-if="refreshing" class="refresh-hint">正在更新数据…</p>
      </header>

      <AppleMovieShowcase v-if="hasLoaded" :movies="featuredMovies" @movie-click="handleMovieClick" />

      <div v-if="loading && !hasLoaded" class="loading-state">
        <div class="spinner"></div>
        <p class="copy-sm">加载数据中...</p>
      </div>

      <div v-else-if="error && !hasLoaded" class="error-state">
        <p class="copy">⚠️ {{ error }}</p>
        <button @click="handleRetry" class="btn btn-primary">重试</button>
      </div>

      <template v-else-if="hasLoaded">
        <StatsOverview :overview="overview" />

        <FilterBar
          :genres="filterOptions.genres"
          :years="filterOptions.years"
          :countries="filterOptions.countries"
          :filters="filters"
          :export-data="exportData"
          @update:filters="handleFiltersDraft"
          @search="handleSearch"
        />

        <MovieShowcase :movies="topMovies" @movie-click="handleMovieClick" />

        <section class="section">
          <div class="section-header">
            <h2 class="headline">🎬 内容深度分析</h2>
            <p class="copy-sm">探索电影内容的核心维度</p>
          </div>
          <div class="bento-card wordcloud-hero">
            <div class="card-header">
              <h3 class="headline">电影类型词云</h3>
              <p class="caption">移动鼠标与词云互动 · 词频越高字体越大</p>
            </div>
            <TagCloudSphere :data="wordcloud" />
          </div>
          <div class="bento-grid">
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">导演作品数量排行</h3>
              </div>
              <BarChart
                :labels="directors.map(d => d.name)"
                :values="directors.map(d => d.count)"
                :rotate="true"
                :height="chartHeight"
                @click="(params) => handleChartClick('directors', params)"
              />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">电影类型分布</h3>
              </div>
              <PieChart :data="genres.slice(0, 10)" :height="chartHeight" />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">获奖情况分布</h3>
              </div>
              <PieChart :data="awards" :height="chartHeight" />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">演员出演电影统计</h3>
              </div>
              <BarChart
                :labels="actors.map(a => a.name)"
                :values="actors.map(a => a.count)"
                :rotate="true"
                :height="chartHeight"
                @click="(params) => handleChartClick('actors', params)"
              />
            </div>
          </div>
        </section>

        <section class="section section-accent">
          <div class="section-header">
            <h2 class="headline">🌍 地域文化分析</h2>
            <p class="copy-sm">探索电影的地域分布特征</p>
          </div>
          <div class="bento-grid">
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">国家/地区分布</h3>
              </div>
              <PieChart :data="countries" :height="chartHeight" />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">语言分布</h3>
              </div>
              <PieChart :data="languages" :height="chartHeight" />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">年度上映趋势</h3>
              </div>
              <LineChart
                :labels="years.map(y => y.year.toString())"
                :values="years.map(y => y.count)"
                :height="chartHeight"
              />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">国家与类型关联</h3>
              </div>
              <PieChart :data="countryGenre" :height="chartHeight" />
            </div>
          </div>
        </section>

        <section class="section section-leaderboard">
          <div class="section-header">
            <h2 class="headline">🏆 评分排行榜</h2>
            <p class="copy-sm">综合评分与评分人数的热门电影排名</p>
          </div>
          <div class="bento-card leaderboard-card">
            <RatingLeaderboard />
          </div>
        </section>

        <section class="section">
          <div class="section-header">
            <h2 class="headline">💬 社交热度分析</h2>
            <p class="copy-sm">分析电影的社交互动数据</p>
          </div>
          <div class="bento-grid">
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">评分区间分布</h3>
              </div>
              <BarChart
                :labels="ratings.map(r => r.range)"
                :values="ratings.map(r => r.count)"
                :height="chartHeight"
              />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">电影时长分布</h3>
              </div>
              <BarChart
                :labels="duration.map(d => d.range)"
                :values="duration.map(d => d.count)"
                :height="chartHeight"
              />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">评分与时长相关性</h3>
              </div>
              <ScatterChart
                :data="ratingDuration"
                x-name="评分"
                y-name="时长(分钟)"
                :height="chartHeight"
              />
            </div>
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">评论数量分布</h3>
              </div>
              <BarChart
                :labels="reviews.map(r => r.range)"
                :values="reviews.map(r => r.count)"
                :height="chartHeight"
              />
            </div>
          </div>
        </section>
      </template>

      <DrilldownModal
        :visible="drilldown.visible"
        :type="drilldown.type"
        :data="drilldown.data"
        @update:visible="handleModalClose"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalytics } from '../analytics/composables/useAnalytics'
import { useChartLinkage } from '../analytics/composables/useChartLinkage'
import StatsOverview from '../analytics/components/Dashboard/StatsOverview.vue'
import FilterBar from '../analytics/components/Common/FilterBar.vue'
import DrilldownModal from '../analytics/components/Common/DrilldownModal.vue'
import PieChart from '../analytics/components/charts/PieChart.vue'
import BarChart from '../analytics/components/charts/BarChart.vue'
import LineChart from '../analytics/components/charts/LineChart.vue'
import ScatterChart from '../analytics/components/charts/ScatterChart.vue'
import TagCloudSphere from '../analytics/components/charts/TagCloudSphere.vue'
import MovieShowcase from '../analytics/components/Dashboard/MovieShowcase.vue'
import AppleMovieShowcase from '../analytics/components/Dashboard/AppleMovieShowcase.vue'
import RatingLeaderboard from '../components/RatingLeaderboard.vue'
import '../analytics/assets/styles/variables.css'

const router = useRouter()

const {
  loading,
  refreshing,
  error,
  hasLoaded,
  overview,
  genres,
  years,
  countries,
  ratings,
  languages,
  directors,
  actors,
  reviews,
  countryGenre,
  ratingDuration,
  duration,
  awards,
  wordcloud,
  topMovies,
  featuredMovies,
  exportMovies,
  filterOptions,
  loadAllData,
  loadFilteredData,
  refreshAllData,
  loadExportMovies,
} = useAnalytics()

const { filters, drilldown, openDrilldown } = useChartLinkage()

const chartHeight = '300px'

const exportData = computed(() => ({
  overview: overview.value,
  genres: genres.value,
  countries: countries.value,
  ratings: ratings.value,
  directors: directors.value,
  actors: actors.value,
  movies: exportMovies.value,
}))

function effectiveFilters(source = filters.value) {
  const result = {}
  if (source.genre) result.genre = source.genre
  if (source.year) result.year = source.year
  if (source.country) result.country = source.country
  return result
}

function handleFiltersDraft(newFilters) {
  Object.assign(filters.value, newFilters)
}

function handleSearch() {
  const active = effectiveFilters()
  loadFilteredData(active)
  loadExportMovies(active)
}

function handleModalClose(visible) {
  drilldown.value.visible = visible
}

function handleChartClick(chartType, params) {
  const { name } = params
  if (chartType === 'directors') {
    openDrilldown('director', {
      name,
      count: directors.value.find(d => d.name === name)?.count,
    })
  } else if (chartType === 'actors') {
    openDrilldown('actor', {
      name,
      count: actors.value.find(a => a.name === name)?.count,
    })
  }
}

function handleRetry() {
  refreshAllData()
}

function handleMovieClick(movie) {
  if (movie?.movie_id) {
    const mid = Number(movie.movie_id)
    if (!mid || Number.isNaN(mid)) {
      console.warn('[AnalyticsView] 无效movie_id，取消跳转', movie)
      return
    }
    router.push({ name: 'movie-detail', params: { id: mid } })
  }
}

onMounted(() => {
  loadAllData()
  if (!exportMovies.value.length) {
    loadExportMovies({})
  }
})
</script>

<style scoped>
.analytics-view {
  min-height: 100vh;
  background: var(--background);
  overflow-x: hidden;
}

.main-content {
  max-width: 1440px;
  margin: 0 auto;
  padding: calc(var(--spacing) * 6) calc(var(--spacing) * 4) calc(var(--spacing) * 13);
  min-width: 0;
}

.page-header {
  text-align: center;
  margin-bottom: calc(var(--spacing) * 10);
}

.page-header .eyebrow {
  margin-bottom: calc(var(--spacing) * 2);
  color: var(--muted-foreground);
  font-size: 14px;
}

.page-header h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  color: var(--foreground);
}

.refresh-hint {
  margin: calc(var(--spacing) * 3) 0 0;
  font-size: 13px;
  color: var(--muted-foreground);
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: calc(var(--spacing) * 24) calc(var(--spacing) * 4);
}

.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: calc(var(--spacing) * 4);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state .btn {
  margin-top: calc(var(--spacing) * 4);
  padding: 10px 20px;
  background: var(--primary);
  color: var(--primary-foreground);
  border: none;
  border-radius: 10px;
  cursor: pointer;
}

.section {
  margin-bottom: calc(var(--spacing) * 13);
}

.section-accent {
  background: var(--secondary);
  border-radius: var(--radius);
  padding: calc(var(--spacing) * 10);
}

.section-header {
  margin-bottom: calc(var(--spacing) * 6);
}

.section-header h2 {
  margin: 0 0 calc(var(--spacing) * 2);
  font-size: 1.5rem;
}

.section-header p {
  margin: 0;
  color: var(--muted-foreground);
}

.wordcloud-hero {
  margin-bottom: calc(var(--spacing) * 3);
  padding: calc(var(--spacing) * 6);
  min-height: 420px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.wordcloud-hero :deep(.tag-cloud-wordcloud) {
  margin-top: calc(var(--spacing) * 2);
  min-height: 380px;
  height: 380px;
}

.wordcloud-hero .card-header {
  display: flex;
  align-items: baseline;
  gap: calc(var(--spacing) * 4);
  margin-bottom: calc(var(--spacing) * 4);
}

.wordcloud-hero .card-header h3 {
  margin: 0;
}

.wordcloud-hero .card-header p {
  margin: 0;
  color: var(--muted-foreground);
  font-size: 13px;
}

.bento-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: calc(var(--spacing) * 3);
  min-width: 0;
}

.bento-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: calc(var(--spacing) * 5);
  box-shadow: var(--shadow-md);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  min-width: 0;
  overflow: hidden;
}

.bento-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.card-header {
  margin-bottom: calc(var(--spacing) * 3);
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.section-leaderboard {
  margin-bottom: calc(var(--spacing) * 13);
}

.leaderboard-card {
  padding: calc(var(--spacing) * 6) calc(var(--spacing) * 7);
}

.leaderboard-card :deep(.rating-leaderboard .mb-4) {
  margin-bottom: calc(var(--spacing) * 4);
}

.leaderboard-card :deep(.rating-leaderboard .text-muted) {
  color: var(--muted-foreground);
}

@media (max-width: 832px) {
  .leaderboard-card {
    padding: calc(var(--spacing) * 5);
  }
}

@media (max-width: 1024px) {
  .bento-grid {
    grid-template-columns: 1fr;
  }

  .section-accent {
    padding: calc(var(--spacing) * 7) calc(var(--spacing) * 5);
  }
}

@media (max-width: 832px) {
  .main-content {
    padding: calc(var(--spacing) * 4) calc(var(--spacing) * 3) calc(var(--spacing) * 10);
  }

  .page-header {
    margin-bottom: calc(var(--spacing) * 8);
  }

  .section {
    margin-bottom: calc(var(--spacing) * 10);
  }

  .bento-card {
    padding: calc(var(--spacing) * 6);
  }
}
</style>
