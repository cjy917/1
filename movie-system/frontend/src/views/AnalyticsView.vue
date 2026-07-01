<template>
  <!--
    数据分析页面主视图组件
    【调用链路】
    AnalyticsView.vue ←→ useAnalytics.js (数据管理) ←→ analytics.js (API调用)
    ←→ backend/app.py (路由) ←→ analytics_service.py (业务逻辑)

    页面结构：
    1. 页头（标题、刷新提示）
    2. 精选电影展示（Apple风格卡片）
    3. 加载/错误状态
    4. 概览统计（StatsOverview）
    5. 筛选栏（FilterBar）
    6. 高分电影展示（MovieShowcase）
    7. 内容深度分析（词云、导演排行、类型分布、获奖分布、演员统计）
    8. 地域文化分析（国家分布、语言分布、年度趋势、国家-类型关联）
    9. 社交热度分析（评分分布、时长分布、评分-时长相关性、评论分布）
    10. 详情弹窗（DrilldownModal）
  -->
  <div class="analytics-view">
    <main class="main-content">
      <!-- 页头区域 -->
      <header class="page-header">
        <p class="eyebrow">FYWZ movies · 数据洞察</p>
        <h1 class="display-2">电影数据分析</h1>
        <p v-if="refreshing" class="refresh-hint">正在更新数据…</p>
      </header>

      <!-- 精选电影展示（Apple风格） -->
      <AppleMovieShowcase v-if="hasLoaded" :movies="featuredMovies" @movie-click="handleMovieClick" />

      <!-- 加载状态 -->
      <div v-if="loading && !hasLoaded" class="loading-state">
        <div class="spinner"></div>
        <p class="copy-sm">加载数据中...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error && !hasLoaded" class="error-state">
        <p class="copy">⚠️ {{ error }}</p>
        <button @click="handleRetry" class="btn btn-primary">重试</button>
      </div>

      <!-- 主内容区（数据加载成功后显示） -->
      <template v-else-if="hasLoaded">
        <!-- 概览统计卡片 -->
        <StatsOverview :overview="overview" />

        <!-- 筛选栏 -->
        <FilterBar
          :genres="filterOptions.genres"
          :years="filterOptions.years"
          :countries="filterOptions.countries"
          :filters="filters"
          :export-data="exportData"
          @update:filters="handleFiltersDraft"
          @search="handleSearch"
        />

        <!-- 高分电影榜单 -->
        <MovieShowcase :movies="topMovies" @movie-click="handleMovieClick" />

        <!-- 内容深度分析模块 -->
        <section class="section">
          <div class="section-header">
            <h2 class="headline">🎬 内容深度分析</h2>
            <p class="copy-sm">探索电影内容的核心维度</p>
          </div>
          <!-- 词云大图（占据整行） -->
          <div class="bento-card wordcloud-hero">
            <div class="card-header">
              <h3 class="headline">电影类型词云</h3>
              <p class="caption">移动鼠标与词云互动 · 词频越高字体越大</p>
            </div>
            <TagCloudSphere :data="wordcloud" />
          </div>
          <!-- 四宫格图表 -->
          <div class="bento-grid">
            <!-- 导演作品数量排行 -->
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
            <!-- 电影类型分布 -->
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">电影类型分布</h3>
              </div>
              <PieChart :data="genres.slice(0, 10)" :height="chartHeight" />
            </div>
            <!-- 获奖情况分布 -->
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">获奖情况分布</h3>
              </div>
              <PieChart :data="awards" :height="chartHeight" />
            </div>
            <!-- 演员出演电影统计 -->
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

        <!-- 地域文化分析模块（带背景色） -->
        <section class="section section-accent">
          <div class="section-header">
            <h2 class="headline">🌍 地域文化分析</h2>
            <p class="copy-sm">探索电影的地域分布特征</p>
          </div>
          <div class="bento-grid">
            <!-- 国家/地区分布 -->
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">国家/地区分布</h3>
              </div>
              <PieChart :data="countries" :height="chartHeight" />
            </div>
            <!-- 语言分布 -->
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">语言分布</h3>
              </div>
              <PieChart :data="languages" :height="chartHeight" />
            </div>
            <!-- 年度上映趋势 -->
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
            <!-- 国家与类型关联 -->
            <div class="bento-card">
              <div class="card-header">
                <h3 class="headline">国家与类型关联</h3>
              </div>
              <PieChart :data="countryGenre" :height="chartHeight" />
            </div>
          </div>
        </section>

        <!-- 社交热度分析模块 -->
        <section class="section">
          <div class="section-header">
            <h2 class="headline">💬 社交热度分析</h2>
            <p class="copy-sm">分析电影的社交互动数据</p>
          </div>
          <div class="bento-grid">
            <!-- 评分区间分布 -->
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
            <!-- 电影时长分布 -->
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
            <!-- 评分与时长相关性（散点图） -->
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
            <!-- 评论数量分布 -->
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

      <!-- 详情弹窗（点击导演/演员时弹出） -->
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
/**
 * 数据分析页面脚本
 * 
 * 数据流向：
 * 1. onMounted → loadAllData() → useAnalytics.fetchDashboard()
 * 2. fetchDashboard() 并行请求16个后端接口
 * 3. 数据返回后更新响应式状态
 * 4. 组件自动渲染对应图表
 * 
 * 筛选流程：
 * 1. FilterBar 更新 filters → handleFiltersDraft()
 * 2. 用户点击搜索 → handleSearch() → loadFilteredData() + loadExportMovies()
 * 3. loadFilteredData() 重新请求后端接口（带筛选条件）
 * 4. 图表数据更新，页面重新渲染
 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalytics } from '../analytics/composables/useAnalytics'
import { useChartLinkage } from '../analytics/composables/useChartLinkage'

// 导入组件
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
import '../analytics/assets/styles/variables.css'

// 路由实例
const router = useRouter()

/**
 * 从 useAnalytics 组合式函数获取状态和方法
 * 
 * 状态：
 * - loading/refreshing/error/hasLoaded: 加载状态
 * - overview/genres/years/countries/ratings/languages: 各类统计数据
 * - directors/actors/reviews/duration/awards/monthly/wordcloud: 图表数据
 * - topMovies/featuredMovies/exportMovies: 电影列表数据
 * - filterOptions: 筛选器选项
 * 
 * 方法：
 * - loadAllData(): 加载所有数据（首次进入）
 * - loadFilteredData(): 加载筛选后的数据
 * - refreshAllData(): 强制刷新所有数据
 * - loadExportMovies(): 加载导出用电影列表
 */
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

/**
 * 从 useChartLinkage 获取筛选和弹窗状态
 * - filters: 当前筛选条件（genre, year, country）
 * - drilldown: 详情弹窗状态（visible, type, data）
 * - openDrilldown: 打开详情弹窗的方法
 */
const { filters, drilldown, openDrilldown } = useChartLinkage()

// 图表统一高度
const chartHeight = '300px'

/**
 * 导出数据（计算属性）
 * 收集需要导出的所有数据，传递给 FilterBar 组件用于导出功能
 */
const exportData = computed(() => ({
  overview: overview.value,
  genres: genres.value,
  countries: countries.value,
  ratings: ratings.value,
  directors: directors.value,
  actors: actors.value,
  movies: exportMovies.value,
}))

/**
 * 构建有效筛选条件
 * 过滤掉空值，只保留有值的筛选条件
 * @param {Object} source - 原始筛选条件
 * @returns {Object} 有效筛选条件
 */
function effectiveFilters(source = filters.value) {
  const result = {}
  if (source.genre) result.genre = source.genre
  if (source.year) result.year = source.year
  if (source.country) result.country = source.country
  return result
}

/**
 * 处理筛选条件变更（草稿模式）
 * 用户在筛选栏中选择选项时，先更新本地状态，不立即请求数据
 * @param {Object} newFilters - 新的筛选条件
 */
function handleFiltersDraft(newFilters) {
  Object.assign(filters.value, newFilters)
}

/**
 * 处理搜索（应用筛选条件）
 * 用户点击搜索按钮时，应用筛选条件并重新加载数据
 */
function handleSearch() {
  const active = effectiveFilters()
  loadFilteredData(active)
  loadExportMovies(active)
}

/**
 * 处理弹窗关闭
 * @param {boolean} visible - 弹窗可见性
 */
function handleModalClose(visible) {
  drilldown.value.visible = visible
}

/**
 * 处理图表点击事件
 * 当用户点击导演或演员图表时，打开详情弹窗
 * @param {string} chartType - 图表类型（directors/actors）
 * @param {Object} params - 点击参数（包含 name）
 */
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

/**
 * 处理重试（加载失败时）
 * 清除缓存并重新加载所有数据
 */
function handleRetry() {
  refreshAllData()
}

/**
 * 处理电影点击
 * 跳转到电影详情页
 * @param {Object} movie - 电影对象（包含 movie_id）
 */
function handleMovieClick(movie) {
  if (movie?.movie_id) {
    router.push({ name: 'movie-detail', params: { id: movie.movie_id } })
  }
}

/**
 * 页面挂载时初始化
 * 1. 加载所有数据分析数据
 * 2. 如果导出电影列表为空，加载导出数据
 */
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