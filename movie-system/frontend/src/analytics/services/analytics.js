import axios from 'axios'

/**
 * 数据分析模块 API 服务
 * 
 * 提供与后端 /api/analytics 前缀下所有接口的交互方法
 * 支持多维度筛选（类型、年份、国家）和数据分页/限制
 */

const API_BASE = '/api/analytics'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

export const analyticsApi = {
  /** 获取数据概览统计（电影总数、平均评分、总评分人数、总影评数） */
  getOverview(filters = {}) {
    return api.get('/overview', { params: filters }).then(res => res.data)
  },

  /** 获取类型分布统计 */
  getGenres(limit = 15, filters = {}) {
    return api.get('/genres', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取年份分布统计 */
  getYears(filters = {}) {
    return api.get('/years', { params: filters }).then(res => res.data)
  },

  /** 获取国家分布统计 */
  getCountries(limit = 12, filters = {}) {
    return api.get('/countries', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取评分区间分布统计 */
  getRatings(filters = {}) {
    return api.get('/ratings', { params: filters }).then(res => res.data)
  },

  /** 获取语言分布统计 */
  getLanguages(limit = 10, filters = {}) {
    return api.get('/languages', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取评分最高的电影列表 */
  getTop(limit = 10, filters = {}) {
    return api.get('/top', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取精选电影列表（随机选择高评分电影） */
  getFeatured(limit = 12, filters = {}) {
    return api.get('/featured', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取电影列表（用于数据导出） */
  getMovies(filters = {}) {
    return api.get('/movies', { params: filters }).then(res => res.data)
  },

  /** 获取时长分布统计 */
  getDuration(filters = {}) {
    return api.get('/duration', { params: filters }).then(res => res.data)
  },

  /** 获取导演分布统计 */
  getDirectors(limit = 10, filters = {}) {
    return api.get('/directors', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取演员分布统计 */
  getActors(limit = 10, filters = {}) {
    return api.get('/actors', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取影评数量分布统计 */
  getReviews(filters = {}) {
    return api.get('/reviews', { params: filters }).then(res => res.data)
  },

  /** 获取国家-类型关联统计 */
  getCountryGenre(limit = 8, filters = {}) {
    return api.get('/country-genre', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取评分-时长相关性数据（散点图） */
  getRatingDuration(filters = {}) {
    return api.get('/rating-duration', { params: filters }).then(res => res.data)
  },

  /** 获取获奖情况分布统计 */
  getAwards(limit = 10, filters = {}) {
    return api.get('/awards', { params: { limit, ...filters } }).then(res => res.data)
  },

  /** 获取月度上映分布统计 */
  getMonthly(filters = {}) {
    return api.get('/monthly', { params: filters }).then(res => res.data)
  },

  /** 获取筛选选项数据（用于前端筛选器） */
  getFilterOptions(params = {}) {
    return api.get('/filter-options', { params }).then(res => res.data)
  },

  /** 获取类型词云数据 */
  getWordcloud(limit = 60, filters = {}) {
    return api.get('/wordcloud', { params: { limit, ...filters } }).then(res => res.data)
  }
}

export default analyticsApi
