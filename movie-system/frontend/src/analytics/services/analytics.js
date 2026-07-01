/**
 * 数据分析模块 API 服务层
 * 
 * 【前后端调用链路】
 * ┌─────────────────────────────────────────────────────────────────────────────┐
 * │  前端 (Vue)                                                               │
 * │  AnalyticsView.vue → useAnalytics.js → analytics.js (本文件)               │
 * │                                      │                                     │
 * │                           ┌──────────▼──────────┐                          │
 * │                           │   HTTP GET /api/analytics/*   │                  │
 * │                           └──────────┬──────────┘                          │
 * └──────────────────────────────────────┼──────────────────────────────────────┘
 *                                      │ axios 请求
 * ┌──────────────────────────────────────▼──────────────────────────────────────┐
 * │  后端 (Flask)                                                             │
 * │  app.py 第688-813行 → analytics_service.py                                │
 * │  请求路径示例：GET /api/analytics/overview?genre=Action&year=2020           │
 * └─────────────────────────────────────────────────────────────────────────────┘
 * 
 * 【前后端对应关系表】
 * ┌─────────────────────┬──────────────────────────────────────────────────────┐
 * │ 前端方法 (analytics.js) │ 对应后端路由 (app.py)                              │
 * ├─────────────────────┼──────────────────────────────────────────────────────┤
 * │ getOverview()       │ @app.route("/api/analytics/overview") 第697行         │
 * │ getGenres()         │ @app.route("/api/analytics/genres") 第708行          │
 * │ getYears()          │ @app.route("/api/analytics/years") 第714行           │
 * │ getCountries()      │ @app.route("/api/analytics/countries") 第719行      │
 * │ getRatings()        │ @app.route("/api/analytics/ratings") 第725行         │
 * │ getLanguages()      │ @app.route("/api/analytics/languages") 第760行       │
 * │ getTop()            │ @app.route("/api/analytics/top") 第742行              │
 * │ getFeatured()       │ @app.route("/api/analytics/featured") 第748行        │
 * │ getMovies()         │ @app.route("/api/analytics/movies") 第754行          │
 * │ getDuration()       │ @app.route("/api/analytics/duration") 第766行        │
 * │ getDirectors()      │ @app.route("/api/analytics/directors") 第771行       │
 * │ getActors()         │ @app.route("/api/analytics/actors") 第736行         │
 * │ getReviews()        │ @app.route("/api/analytics/reviews") 第777行        │
 * │ getCountryGenre()   │ @app.route("/api/analytics/country-genre") 第782行   │
 * │ getRatingDuration() │ @app.route("/api/analytics/rating-duration") 第788行 │
 * │ getAwards()         │ @app.route("/api/analytics/awards") 第793行          │
 * │ getMonthly()        │ @app.route("/api/analytics/monthly") 第799行         │
 * │ getFilterOptions()  │ @app.route("/api/analytics/filter-options") 第689行   │
 * │ getWordcloud()      │ @app.route("/api/analytics/wordcloud") 第804行       │
 * └─────────────────────┴──────────────────────────────────────────────────────┘
 * 
 * 【使用示例】
 * // 前端调用
 * const data = await analyticsApi.getOverview({ genre: 'Action' })
 * // 实际发送请求: GET /api/analytics/overview?genre=Action
 * // 后端返回: { total_movies: 1234, total_users: 56, ... }
 */
import axios from 'axios'

const API_BASE = '/api/analytics'

/**
 * axios 实例配置
 * - baseURL: 固定为 /api/analytics，简化接口路径
 * - timeout: 30秒，数据分析接口可能涉及复杂查询，超时时间较长
 */
const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

/**
 * 数据分析 API 集合
 * 
 * 每个方法对应后端 analytics_service.py 中的一个函数，
 * 参数 filters 用于传递筛选条件（genre、year、country 等）。
 */
export const analyticsApi = {
  /**
   * 获取概览统计数据
   * @param {Object} filters - 筛选条件
   * @returns {Object} 包含电影总数、用户数、评分数等概览信息
   * 
   * 【前后端对应】 ← 前后端对照标记
   * 前端: analyticsApi.getOverview(filters)
   * 后端: GET /api/analytics/overview → app.py 第697行 → analytics_service.py overview_stats()
   */
  getOverview(filters = {}) {
    return api.get('/overview', { params: filters }).then(res => res.data)
  },

  /**
   * 获取电影类型分布
   * @param {number} limit - 返回数量限制，默认15
   * @param {Object} filters - 筛选条件
   * @returns {Array} 类型分布数组，每项包含 name 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getGenres(limit, filters)
   * 后端: GET /api/analytics/genres → app.py 第708行 → analytics_service.py genre_distribution()
   */
  getGenres(limit = 15, filters = {}) {
    return api.get('/genres', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取年度上映趋势
   * @param {Object} filters - 筛选条件
   * @returns {Array} 年度分布数组，每项包含 year 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getYears(filters)
   * 后端: GET /api/analytics/years → app.py 第714行 → analytics_service.py year_distribution()
   */
  getYears(filters = {}) {
    return api.get('/years', { params: filters }).then(res => res.data)
  },

  /**
   * 获取国家/地区分布
   * @param {number} limit - 返回数量限制，默认12
   * @param {Object} filters - 筛选条件
   * @returns {Array} 国家分布数组，每项包含 name 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getCountries(limit, filters)
   * 后端: GET /api/analytics/countries → app.py 第719行 → analytics_service.py country_distribution()
   */
  getCountries(limit = 12, filters = {}) {
    return api.get('/countries', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取评分区间分布
   * @param {Object} filters - 筛选条件
   * @returns {Array} 评分分布数组，每项包含 range 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getRatings(filters)
   * 后端: GET /api/analytics/ratings → app.py 第725行 → analytics_service.py rating_distribution()
   */
  getRatings(filters = {}) {
    return api.get('/ratings', { params: filters }).then(res => res.data)
  },

  /**
   * 获取语言分布
   * @param {number} limit - 返回数量限制，默认10
   * @param {Object} filters - 筛选条件
   * @returns {Array} 语言分布数组，每项包含 name 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getLanguages(limit, filters)
   * 后端: GET /api/analytics/languages → app.py 第760行 → analytics_service.py language_distribution()
   */
  getLanguages(limit = 10, filters = {}) {
    return api.get('/languages', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取高分电影榜单
   * @param {number} limit - 返回数量限制，默认10
   * @param {Object} filters - 筛选条件
   * @returns {Array} 电影列表，包含评分、评分人数等信息
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getTop(limit, filters)
   * 后端: GET /api/analytics/top → app.py 第742行 → analytics_service.py top_movies()
   */
  getTop(limit = 10, filters = {}) {
    return api.get('/top', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取精选电影列表
   * @param {number} limit - 返回数量限制，默认12
   * @param {Object} filters - 筛选条件
   * @returns {Array} 精选电影列表
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getFeatured(limit, filters)
   * 后端: GET /api/analytics/featured → app.py 第748行 → analytics_service.py featured_movies()
   */
  getFeatured(limit = 12, filters = {}) {
    return api.get('/featured', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取电影列表（用于导出）
   * @param {Object} filters - 筛选条件
   * @returns {Array} 电影列表，包含完整字段信息
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getMovies(filters)
   * 后端: GET /api/analytics/movies → app.py 第754行 → analytics_service.py get_all_movies()
   */
  getMovies(filters = {}) {
    return api.get('/movies', { params: filters }).then(res => res.data)
  },

  /**
   * 获取电影时长分布
   * @param {Object} filters - 筛选条件
   * @returns {Array} 时长分布数组，每项包含 range 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getDuration(filters)
   * 后端: GET /api/analytics/duration → app.py 第766行 → analytics_service.py duration_distribution()
   */
  getDuration(filters = {}) {
    return api.get('/duration', { params: filters }).then(res => res.data)
  },

  /**
   * 获取导演作品数量排行
   * @param {number} limit - 返回数量限制，默认10
   * @param {Object} filters - 筛选条件
   * @returns {Array} 导演排行数组，每项包含 name 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getDirectors(limit, filters)
   * 后端: GET /api/analytics/directors → app.py 第771行 → analytics_service.py director_distribution()
   */
  getDirectors(limit = 10, filters = {}) {
    return api.get('/directors', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取演员出演电影统计
   * @param {number} limit - 返回数量限制，默认10
   * @param {Object} filters - 筛选条件
   * @returns {Array} 演员统计数组，每项包含 name 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getActors(limit, filters)
   * 后端: GET /api/analytics/actors → app.py 第736行 → analytics_service.py actor_distribution()
   */
  getActors(limit = 10, filters = {}) {
    return api.get('/actors', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取评论数量分布
   * @param {Object} filters - 筛选条件
   * @returns {Array} 评论分布数组，每项包含 range 和 count
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getReviews(filters)
   * 后端: GET /api/analytics/reviews → app.py 第777行 → analytics_service.py review_count_distribution()
   */
  getReviews(filters = {}) {
    return api.get('/reviews', { params: filters }).then(res => res.data)
  },

  /**
   * 获取国家与类型关联数据
   * @param {number} limit - 返回数量限制，默认8
   * @param {Object} filters - 筛选条件
   * @returns {Array} 国家-类型关联数组
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getCountryGenre(limit, filters)
   * 后端: GET /api/analytics/country-genre → app.py 第782行 → analytics_service.py country_genre_correlation()
   */
  getCountryGenre(limit = 8, filters = {}) {
    return api.get('/country-genre', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取评分与时长相关性数据
   * @param {Object} filters - 筛选条件
   * @returns {Array} 散点图数据，每项包含 rating 和 duration
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getRatingDuration(filters)
   * 后端: GET /api/analytics/rating-duration → app.py 第788行 → analytics_service.py rating_duration_correlation()
   */
  getRatingDuration(filters = {}) {
    return api.get('/rating-duration', { params: filters }).then(res => res.data)
  },

  /**
   * 获取获奖情况分布
   * @param {number} limit - 返回数量限制，默认10
   * @param {Object} filters - 筛选条件
   * @returns {Array} 获奖分布数组
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getAwards(limit, filters)
   * 后端: GET /api/analytics/awards → app.py 第793行 → analytics_service.py award_distribution()
   */
  getAwards(limit = 10, filters = {}) {
    return api.get('/awards', { params: { limit, ...filters } }).then(res => res.data)
  },

  /**
   * 获取月度上映分布
   * @param {Object} filters - 筛选条件
   * @returns {Array} 月度分布数组
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getMonthly(filters)
   * 后端: GET /api/analytics/monthly → app.py 第799行 → analytics_service.py monthly_release_distribution()
   */
  getMonthly(filters = {}) {
    return api.get('/monthly', { params: filters }).then(res => res.data)
  },

  /**
   * 获取筛选选项（用于筛选器下拉框）
   * @param {Object} params - 参数（genre_limit, country_limit, year_from 等）
   * @returns {Object} 包含 genres, years, countries 三个数组
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getFilterOptions(params)
   * 后端: GET /api/analytics/filter-options → app.py 第689行 → analytics_service.py analytics_filter_options()
   */
  getFilterOptions(params = {}) {
    return api.get('/filter-options', { params }).then(res => res.data)
  },

  /**
   * 获取词云数据
   * @param {number} limit - 返回词数限制，默认60
   * @param {Object} filters - 筛选条件
   * @returns {Array} 词云数据数组，每项包含 text 和 weight
   * 
   * 【前后端对应】
   * 前端: analyticsApi.getWordcloud(limit, filters)
   * 后端: GET /api/analytics/wordcloud → app.py 第804行 → analytics_service.py wordcloud_data()
   */
  getWordcloud(limit = 60, filters = {}) {
    return api.get('/wordcloud', { params: { limit, ...filters } }).then(res => res.data)
  }
}

export default analyticsApi