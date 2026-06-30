import { ref } from 'vue'
import { analyticsApi } from '../services/analytics'

// 模块级缓存：离开页面再回来不重复全屏加载
const ANALYTICS_CACHE_VERSION = 7
const loading = ref(false)
const refreshing = ref(false)
const error = ref(null)
const hasLoaded = ref(false)

const overview = ref(null)
const genres = ref([])
const years = ref([])
const countries = ref([])
const ratings = ref([])
const languages = ref([])
const topMovies = ref([])
const featuredMovies = ref([])
const exportMovies = ref([])
const duration = ref([])
const directors = ref([])
const actors = ref([])
const reviews = ref([])
const countryGenre = ref([])
const ratingDuration = ref([])
const awards = ref([])
const monthly = ref([])
const wordcloud = ref([])
const filterOptions = ref({ genres: [], years: [], countries: [] })
let cacheVersion = 0

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

    if (includeFeatured) {
      requests.splice(7, 0, analyticsApi.getFeatured(12, filters))
    }

    const results = await Promise.all(requests)

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
  async function loadFeaturedMovies() {
    try {
      featuredMovies.value = await analyticsApi.getFeatured(12, {})
    } catch (err) {
      console.error('加载精选电影失败:', err)
    }
  }

  async function loadExportMovies(filters = {}) {
    try {
      exportMovies.value = await analyticsApi.getMovies(filters)
    } catch (err) {
      console.error('加载导出电影失败:', err)
    }
  }

  async function loadTopMoviesOnly(filters = {}) {
    try {
      topMovies.value = await analyticsApi.getTop(10, filters)
    } catch (err) {
      console.error('加载热门电影失败:', err)
    }
  }

  async function loadFilteredData(filters = {}) {
    await fetchDashboard(filters, { includeFeatured: false, silent: true })
  }

  async function loadAllData(filters = {}) {
    if (hasLoaded.value && cacheVersion === ANALYTICS_CACHE_VERSION) return
    await Promise.all([loadFilterOptions(), fetchDashboard(filters, { includeFeatured: true, silent: false })])
  }

  async function refreshAllData(filters = {}) {
    hasLoaded.value = false
    cacheVersion = 0
    await Promise.all([loadFilterOptions(), fetchDashboard(filters, { includeFeatured: true, silent: true })])
  }

  return {
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
    loadAllData,
    loadFilteredData,
    refreshAllData,
    loadFeaturedMovies,
    loadExportMovies,
    loadTopMoviesOnly,
  }
}
