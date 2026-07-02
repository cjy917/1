import axios from 'axios'

const API_BASE = '/api/analytics'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

export const analyticsApi = {
  getOverview(filters = {}) {
    return api.get('/overview', { params: filters }).then(res => res.data)
  },

  getGenres(limit = 15, filters = {}) {
    return api.get('/genres', { params: { limit, ...filters } }).then(res => res.data)
  },

  getYears(filters = {}) {
    return api.get('/years', { params: filters }).then(res => res.data)
  },

  getCountries(limit = 12, filters = {}) {
    return api.get('/countries', { params: { limit, ...filters } }).then(res => res.data)
  },

  getRatings(filters = {}) {
    return api.get('/ratings', { params: filters }).then(res => res.data)
  },

  getLanguages(limit = 10, filters = {}) {
    return api.get('/languages', { params: { limit, ...filters } }).then(res => res.data)
  },

  getTop(limit = 10, filters = {}) {
    return api.get('/top', { params: { limit, ...filters } }).then(res => res.data)
  },

  getFeatured(limit = 12, filters = {}) {
    return api.get('/featured', { params: { limit, ...filters } }).then(res => res.data)
  },

  getMovies(filters = {}) {
    return api.get('/movies', { params: filters }).then(res => res.data)
  },

  getDuration(filters = {}) {
    return api.get('/duration', { params: filters }).then(res => res.data)
  },

  getDirectors(limit = 10, filters = {}) {
    return api.get('/directors', { params: { limit, ...filters } }).then(res => res.data)
  },

  getActors(limit = 10, filters = {}) {
    return api.get('/actors', { params: { limit, ...filters } }).then(res => res.data)
  },

  getReviews(filters = {}) {
    return api.get('/reviews', { params: filters }).then(res => res.data)
  },

  getCountryGenre(limit = 8, filters = {}) {
    return api.get('/country-genre', { params: { limit, ...filters } }).then(res => res.data)
  },

  getRatingDuration(filters = {}) {
    return api.get('/rating-duration', { params: filters }).then(res => res.data)
  },

  getAwards(limit = 10, filters = {}) {
    return api.get('/awards', { params: { limit, ...filters } }).then(res => res.data)
  },

  getMonthly(filters = {}) {
    return api.get('/monthly', { params: filters }).then(res => res.data)
  },

  getFilterOptions(params = {}) {
    return api.get('/filter-options', { params }).then(res => res.data)
  },

  getWordcloud(limit = 60, filters = {}) {
    return api.get('/wordcloud', { params: { limit, ...filters } }).then(res => res.data)
  }
}

export default analyticsApi
