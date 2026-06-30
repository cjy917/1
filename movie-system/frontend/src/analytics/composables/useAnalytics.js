import { ref } from 'vue'
import { analyticsApi } from '../services/analytics'

/**
 * 数据分析模块状态管理 Composable
 * 
 * 提供数据分析页面的全局数据状态、加载状态和数据获取方法
 * 使用模块级缓存，离开页面再回来不会重复加载数据
 */

// 模块级缓存版本号，用于判断是否需要重新加载数据
const ANALYTICS_CACHE_VERSION = 7
const loading = ref(false)           // 首次加载状态
const refreshing = ref(false)        // 刷新状态
const error = ref(null)              // 错误信息
const hasLoaded = ref(false)         // 是否已完成首次加载

// 数据状态
const overview = ref(null)           // 概览统计
const genres = ref([])               // 类型分布
const years = ref([])                // 年份分布
const countries = ref([])            // 国家分布
const ratings = ref([])              // 评分分布
const languages = ref([])            // 语言分布
const topMovies = ref([])            // 热门电影
const featuredMovies = ref([])       // 精选电影
const exportMovies = ref([])         // 导出用电影列表
const duration = ref([])             // 时长分布
const directors = ref([])            // 导演分布
const actors = ref([])               // 演员分布
const reviews = ref([])              // 影评分布
const countryGenre = ref([])         // 国家-类型关联
const ratingDuration = ref([])       // 评分-时长相关性
const awards = ref([])               // 获奖分布
const monthly = ref([])              // 月度上映分布
const wordcloud = ref([])            // 词云数据
const filterOptions = ref({ genres: [], years: [], countries: [] })  // 筛选选项
let cacheVersion = 0

/**
 * 获取仪表盘所有数据
 * 
 * @param {Object} filters - 筛选条件
 * @param {Object} options - 选项
 * @param {boolean} options.includeFeatured - 是否包含精选电影
 * @param {boolean} options.silent - 是否静默加载（不显示 loading 状态）
 */
async function fetchDashboard(filters = {}, { includeFeatured = true, silent = false } = {}) {
  if (silent && hasLoaded.value) {
    refreshing.value = true
  } else if (!hasLoaded.value) {
    loading.value = true
  } else {
    refreshing.value = true
  }
  error.value = null

  try {
    // 并行请求所有数据源
    const requests = [
      analyticsApi.getOverview(filters),
      analyticsApi.getGenres(15, filters),
      analyticsApi.getYears(filters),
      analyticsApi.getCountries(12, filters),
      analyticsApi.getRatings(filters),
      analyticsApi.getLanguages(10, filters),
      analyticsApi.getTop(10, filters),
      analyticsApi.getDuration(filters),
      analyticsApi.getDirectors(10, filters),
      analyticsApi.getActors(10, filters),
      analyticsApi.getReviews(filters),
      analyticsApi.getCountryGenre(8, filters),
      analyticsApi.getRatingDuration(filters),
      analyticsApi.getAwards(10, filters),
      analyticsApi.getMonthly(filters),
      analyticsApi.getWordcloud(60, filters),
    ]

    // 插入精选电影请求（在第8个位置）
    if (includeFeatured) {
      requests.splice(7, 0, analyticsApi.getFeatured(12, filters))
    }

    const results = await Promise.all(requests)

    // 按顺序赋值结果
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
 * 加载筛选选项（类型、年份、国家列表）
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

export function useAnalytics() {
  /** 仅加载精选电影 */
  async function loadFeaturedMovies() {
    try {
      featuredMovies.value = await analyticsApi.getFeatured(12, {})
    } catch (err) {
      console.error('加载精选电影失败:', err)
    }
  }

  /** 加载导出用电影列表 */
  async function loadExportMovies(filters = {}) {
    try {
      exportMovies.value = await analyticsApi.getMovies(filters)
    } catch (err) {
      console.error('加载导出电影失败:', err)
    }
  }

  /** 仅加载热门电影 */
  async function loadTopMoviesOnly(filters = {}) {
    try {
      topMovies.value = await analyticsApi.getTop(10, filters)
    } catch (err) {
      console.error('加载热门电影失败:', err)
    }
  }

  /** 加载筛选后的数据（不包含精选电影，静默加载） */
  async function loadFilteredData(filters = {}) {
    await fetchDashboard(filters, { includeFeatured: false, silent: true })
  }

  /** 加载所有数据（含筛选选项），带缓存检查 */
  async function loadAllData(filters = {}) {
    if (hasLoaded.value && cacheVersion === ANALYTICS_CACHE_VERSION) return
    await Promise.all([loadFilterOptions(), fetchDashboard(filters, { includeFeatured: true, silent: false })])
  }

  /** 强制刷新所有数据（清除缓存） */
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
