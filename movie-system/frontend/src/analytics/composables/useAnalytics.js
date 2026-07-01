/**
 * 数据分析模块组合式函数（Composable）
 * 
 * 【调用链路】
 * AnalyticsView.vue ←→ useAnalytics.js (组合式函数层) ←→ analytics.js (API层)
 * 
 * 负责管理数据分析页面的所有状态和数据获取逻辑：
 * 1. 模块级缓存：离开页面再回来不重复加载全部数据
 * 2. 统一的数据获取方法：批量并行请求所有分析数据
 * 3. 加载状态管理：loading, refreshing, error, hasLoaded
 * 4. 筛选功能支持：loadFilteredData, loadFilterOptions
 */
import { ref } from 'vue'
import { analyticsApi } from '../services/analytics'

// 模块级缓存版本号：修改此值可强制刷新所有缓存
const ANALYTICS_CACHE_VERSION = 7

/**
 * 加载状态
 * - loading: 首次加载中（显示全屏加载动画）
 * - refreshing: 刷新中（显示刷新提示）
 * - error: 加载错误信息
 * - hasLoaded: 是否已完成首次加载
 */
const loading = ref(false)
const refreshing = ref(false)
const error = ref(null)
const hasLoaded = ref(false)

/**
 * 数据状态（响应式）
 * 每项对应一个后端接口返回的数据
 */
const overview = ref(null)           // 概览统计
const genres = ref([])               // 类型分布
const years = ref([])                // 年度趋势
const countries = ref([])            // 国家分布
const ratings = ref([])              // 评分分布
const languages = ref([])            // 语言分布
const topMovies = ref([])            // 高分电影榜单
const featuredMovies = ref([])       // 精选电影列表
const exportMovies = ref([])         // 导出用电影列表
const duration = ref([])             // 时长分布
const directors = ref([])            // 导演排行
const actors = ref([])               // 演员统计
const reviews = ref([])              // 评论分布
const countryGenre = ref([])         // 国家-类型关联
const ratingDuration = ref([])       // 评分-时长相关性
const awards = ref([])               // 获奖分布
const monthly = ref([])              // 月度分布
const wordcloud = ref([])            // 词云数据
const filterOptions = ref({ genres: [], years: [], countries: [] }) // 筛选选项

let cacheVersion = 0

/**
 * 核心方法：批量获取仪表盘数据
 * 
 * 并行请求16个数据分析接口，一次性加载所有图表所需数据。
 * 
 * @param {Object} filters - 筛选条件（genre, year, country）
 * @param {Object} options - 选项配置
 * @param {boolean} options.includeFeatured - 是否包含精选电影（首次加载需要）
 * @param {boolean} options.silent - 是否静默加载（筛选后刷新时为true）
 */
async function fetchDashboard(filters = {}, { includeFeatured = true, silent = false } = {}) {
  // 根据加载模式设置状态
  if (silent && hasLoaded.value) {
    refreshing.value = true
  } else if (!hasLoaded.value) {
    loading.value = true
  } else {
    refreshing.value = true
  }
  error.value = null

  try {
    // 构建并行请求数组
    const requests = [
      analyticsApi.getOverview(filters),           // 0: 概览
      analyticsApi.getGenres(15, filters),         // 1: 类型分布
      analyticsApi.getYears(filters),              // 2: 年度趋势
      analyticsApi.getCountries(12, filters),      // 3: 国家分布
      analyticsApi.getRatings(filters),            // 4: 评分分布
      analyticsApi.getLanguages(10, filters),      // 5: 语言分布
      analyticsApi.getTop(10, filters),            // 6: 高分电影
      analyticsApi.getDuration(filters),           // 7: 时长分布（若包含featured则索引+1）
      analyticsApi.getDirectors(10, filters),      // 8: 导演排行
      analyticsApi.getActors(10, filters),         // 9: 演员统计
      analyticsApi.getReviews(filters),            // 10: 评论分布
      analyticsApi.getCountryGenre(8, filters),    // 11: 国家-类型关联
      analyticsApi.getRatingDuration(filters),     // 12: 评分-时长相关性
      analyticsApi.getAwards(10, filters),         // 13: 获奖分布
      analyticsApi.getMonthly(filters),            // 14: 月度分布
      analyticsApi.getWordcloud(60, filters),      // 15: 词云数据
    ]

    // 如果需要精选电影，插入到第7位（高分电影之后，时长分布之前）
    if (includeFeatured) {
      requests.splice(7, 0, analyticsApi.getFeatured(12, filters))
    }

    // 并行执行所有请求
    const results = await Promise.all(requests)

    // 按顺序赋值给响应式状态
    let i = 0
    overview.value = results[i++]
    genres.value = results[i++]
    years.value = results[i++]
    countries.value = results[i++]
    ratings.value = results[i++]
    languages.value = results[i++]
    topMovies.value = results[i++]
    if (includeFeatured) {
      featuredMovies.value = results[i++]
    }
    duration.value = results[i++]
    directors.value = results[i++]
    actors.value = results[i++]
    reviews.value = results[i++]
    countryGenre.value = results[i++]
    ratingDuration.value = results[i++]
    awards.value = results[i++]
    monthly.value = results[i++]
    wordcloud.value = results[i++]

    hasLoaded.value = true
    cacheVersion = ANALYTICS_CACHE_VERSION
  } catch (err) {
    error.value = err.message || '加载数据失败'
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

/**
 * 加载筛选器选项（类型、年份、国家下拉框数据）
 */
async function loadFilterOptions() {
  try {
    filterOptions.value = await analyticsApi.getFilterOptions({
      genre_limit: 25,
      country_limit: 20,
      year_from: 2010,
    })
  } catch (err) {
    console.error('加载筛选项失败:', err)
  }
}

/**
 * 组合式函数主入口
 * 
 * 对外暴露所有状态和方法，供组件使用。
 */
export function useAnalytics() {
  /**
   * 单独加载精选电影（用于首页等非完整分析页面）
   */
  async function loadFeaturedMovies() {
    try {
      featuredMovies.value = await analyticsApi.getFeatured(12, {})
    } catch (err) {
      console.error('加载精选电影失败:', err)
    }
  }

  /**
   * 加载导出用电影列表
   * @param {Object} filters - 筛选条件
   */
  async function loadExportMovies(filters = {}) {
    try {
      exportMovies.value = await analyticsApi.getMovies(filters)
    } catch (err) {
      console.error('加载导出电影失败:', err)
    }
  }

  /**
   * 单独加载高分电影榜单
   * @param {Object} filters - 筛选条件
   */
  async function loadTopMoviesOnly(filters = {}) {
    try {
      topMovies.value = await analyticsApi.getTop(10, filters)
    } catch (err) {
      console.error('加载热门电影失败:', err)
    }
  }

  /**
   * 加载筛选后的数据（静默模式，不显示全屏加载）
   * @param {Object} filters - 筛选条件
   */
  async function loadFilteredData(filters = {}) {
    await fetchDashboard(filters, { includeFeatured: false, silent: true })
  }

  /**
   * 加载所有数据（首次进入页面调用）
   * 带有缓存机制，避免重复加载
   * @param {Object} filters - 筛选条件
   */
  async function loadAllData(filters = {}) {
    if (hasLoaded.value && cacheVersion === ANALYTICS_CACHE_VERSION) return
    await Promise.all([loadFilterOptions(), fetchDashboard(filters, { includeFeatured: true, silent: false })])
  }

  /**
   * 强制刷新所有数据（清除缓存）
   * @param {Object} filters - 筛选条件
   */
  async function refreshAllData(filters = {}) {
    hasLoaded.value = false
    cacheVersion = 0
    await Promise.all([loadFilterOptions(), fetchDashboard(filters, { includeFeatured: true, silent: true })])
  }

  return {
    // 状态
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
    topMovies,
    featuredMovies,
    exportMovies,
    duration,
    directors,
    actors,
    reviews,
    countryGenre,
    ratingDuration,
    awards,
    monthly,
    wordcloud,
    filterOptions,
    // 方法
    loadAllData,
    loadFilteredData,
    refreshAllData,
    loadFeaturedMovies,
    loadExportMovies,
    loadTopMoviesOnly,
  }
}