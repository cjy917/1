import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 30000,
})

export default api

export const authApi = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

export const movieApi = {
  list: (params) => api.get('/movies', { params }),
  home: () => api.get('/movies/home'),
  filters: () => api.get('/movies/filters'),
  detail: (id) => api.get(`/movies/${id}`),
  similar: (id) => api.get(`/movies/${id}/similar`),
  trailer: (id, params) => api.get(`/movies/${id}/trailer`, { params }),
  trailerLocalIds: () => api.get('/trailers/local-ids'),
  play: (id, params) => api.get(`/movies/${id}/play`, { params }),
  search: (q) => api.get('/movies/search', { params: { q } }),
}

export const ratingApi = {
  rate: (data) => api.post('/ratings', data),
  remove: (movie_id) => api.delete('/ratings', { params: { movie_id } }),
  mine: () => api.get('/user/ratings'),
}

export const favoriteApi = {
  list: () => api.get('/favorites'),
  add: (movie_id) => api.post('/favorites', { movie_id }),
  remove: (movie_id) => api.delete('/favorites', { params: { movie_id } }),
}

export const watchlistApi = {
  list: () => api.get('/watchlist'),
  add: (movie_id) => api.post('/watchlist', { movie_id }),
  remove: (movie_id) => api.delete('/watchlist', { params: { movie_id } }),
}

export const listApi = {
  list: () => api.get('/lists'),
  add: (movie_id) => api.post('/lists', { movie_id }),
  remove: (movie_id) => api.delete('/lists', { params: { movie_id } }),
}

export const analyticsApi = {
  overview: () => api.get('/analytics/overview'),
  genres: () => api.get('/analytics/genres'),
  years: () => api.get('/analytics/years'),
  countries: () => api.get('/analytics/countries'),
  ratings: () => api.get('/analytics/ratings'),
  actors: () => api.get('/analytics/actors'),
  top: () => api.get('/analytics/top'),
  sources: () => api.get('/analytics/sources'),
  ratingLeaderboard: (limit = 10) => api.get('/analytics/rating-leaderboard', { params: { limit } }),
}

export const recommendApi = {
  personal: () => api.get('/recommend/personal'),
  refresh: () => api.post('/recommend/refresh'),
  similar: (id) => api.get(`/recommend/similar/${id}`),
  guest: () => api.get('/recommend/guest'),
}

export const commentApi = {
  list: (movie_id) => api.get(`/movies/${movie_id}/comments`),
  submit: (data) => api.post('/comments', data),
  remove: (movie_id) => api.delete('/comments', { params: { movie_id } }),
}

export const adminApi = {
  preview: () => api.get('/admin/data-preview'),
}
