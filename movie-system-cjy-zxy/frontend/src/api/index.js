/**
 * =============================================================================
 * 前后端 API 连接层
 * 用法：先在本文件搜接口名 → 再到 backend/app.py 搜路由 → services/*.py 搜业务
 * 速查索引：src/code-map.js
 * =============================================================================
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 30000,
})

export const authApi = {
  /** 【A1】登录 → POST /api/auth/login */
  login: (data) => api.post('/auth/login', data),
  /** 【A1】注册 → POST /api/auth/register */
  register: (data) => api.post('/auth/register', data),
  /** 退出 → POST /api/auth/logout */
  logout: () => api.post('/auth/logout'),
  /** 【A3】当前用户 → GET /api/auth/me */
  me: () => api.get('/auth/me'),
}

// ─── 首页 + 详情页 · 电影 ───────────────────────────────────────────────────
export const movieApi = {
  list: (params) => api.get('/movies', { params }),
  /** 【首页-H1】首页分区数据 → GET /api/movies/home */
  home: () => api.get('/movies/home'),
  /** 【首页-H4】首页短评 → GET /api/movies/home/comments */
  homeComments: (limit = 30) => api.get('/movies/home/comments', { params: { limit } }),
  filters: () => api.get('/movies/filters'),
  /** 【详情-D0】电影详情 → GET /api/movies/:id */
  detail: (id) => api.get(`/movies/${id}`),
  /** 【首页-H2 / 详情-D1e】预告片 → GET /api/movies/:id/trailer */
  trailer: (id, params) => api.get(`/movies/${id}/trailer`, { params }),
  /** 【首页+详情】本地预告 ID 列表 → GET /api/trailers/local-ids */
  trailerLocalIds: () => api.get('/trailers/local-ids'),
  /** 【详情-D1d / D2】正片播放 → GET /api/movies/:id/play */
  play: (id, params) => api.get(`/movies/${id}/play`, { params }),
  /** 【详情-D2a】观看平台链接 → GET /api/movies/:id/watch-links */
  watchLinks: (id) => api.get(`/movies/${id}/watch-links`),
  search: (q) => api.get('/movies/search', { params: { q } }),
}

// ─── 详情页 · 评分 / 收藏 / 片单 ────────────────────────────────────────────
export const ratingApi = {
  /** 【详情-D1f】提交评分 → POST /api/ratings */
  rate: (data) => api.post('/ratings', data),
  remove: (movie_id) => api.delete('/ratings', { params: { movie_id } }),
  mine: () => api.get('/user/ratings'),
}

export const favoriteApi = {
  list: () => api.get('/favorites'),
  /** 【详情-D1b】收藏 → POST /api/favorites */
  add: (movie_id) => api.post('/favorites', { movie_id }),
  remove: (movie_id) => api.delete('/favorites', { params: { movie_id } }),
}

export const watchlistApi = {
  list: () => api.get('/watchlist'),
  /** 【详情-D1c】待看片单 → POST /api/watchlist */
  add: (movie_id) => api.post('/watchlist', { movie_id }),
  remove: (movie_id) => api.delete('/watchlist', { params: { movie_id } }),
}

export const listApi = {
  list: () => api.get('/lists'),
  /** 【详情-D1a】片单 → POST /api/lists */
  add: (movie_id) => api.post('/lists', { movie_id }),
  remove: (movie_id) => api.delete('/lists', { params: { movie_id } }),
}

// ─── 详情页 · 推荐 / 短评 / 翻译 ────────────────────────────────────────────
export const recommendApi = {
  personal: () => api.get('/recommend/personal'),
  refresh: () => api.post('/recommend/refresh', {}, { timeout: 600000 }),
  /** 【详情-D4】相似推荐 → GET /api/recommend/similar/:id */
  similar: (id) => api.get(`/recommend/similar/${id}`),
  guest: () => api.get('/recommend/guest'),
  /** 【首页·偏好推荐】问卷偏好 → POST /api/recommend/preference */
  byPreference: (prefs) =>
    api.post('/recommend/preference', {
      likeGenres: prefs.likeGenres || [],
      likeDirectors: prefs.likeDirectors || [],
      likeActors: prefs.likeActors || [],
    }),
}

export const commentApi = {
  /** 【详情-D3】短评列表 → GET /api/movies/:id/comments */
  list: (movie_id) => api.get(`/movies/${movie_id}/comments`),
  submit: (data) => api.post('/comments', data),
  remove: (movie_id) => api.delete('/comments', { params: { movie_id } }),
}

export const translateApi = {
  /** 【详情-D3b】评论翻译 → POST /api/translate */
  translate: (data) => api.post('/translate', data, { timeout: 60000 }),
}

// ─── 登录注册 · 偏好问卷 ────────────────────────────────────────────────────
export const preferenceApi = {
  /** 【A2】问卷导演列表 → GET /api/preferences/directors */
  directors: () => api.get('/preferences/directors'),
  /** 【A2】问卷演员列表 → GET /api/preferences/actors */
  actors: () => api.get('/preferences/actors'),
}
