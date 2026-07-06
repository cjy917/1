import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 60000,
})

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const code = error?.code
    const message = error?.message || ''
    const status = error?.response?.status

    if (code === 'ECONNABORTED' || /timeout/i.test(message) || error?.isAxiosError && !error.response) {
      if (code === 'ECONNABORTED' || /timeout/i.test(message)) {
        error.fywzCategory = 'frontend_timeout'
        error.fywzHint =
          '前端请求超时（60秒）：大概率是 Shadowrocket 代理访问 AI 服务慢，或后端 Flask 正在等待上游响应。' +
          '建议：1) 查看后端日志，确认 SiliconFlow 请求是否仍在进行；2) 切换 Shadowrocket 到更快的节点后重试；' +
          '3) 如需更长等待可在 api/index.js 把全局 timeout 再调高（如 120000）。'
      } else if (!error.response) {
        error.fywzCategory = 'frontend_network'
        error.fywzHint =
          '浏览器无法连接到后端：请检查 Flask 后端是否在 127.0.0.1:5000 端口正常运行，' +
          'Vite proxy (/api → http://127.0.0.1:5000) 是否生效，或代理软件是否把 localhost 也错误走了代理' +
          '（在 NO_PROXY 增加 127.0.0.1,localhost 可解决）。'
      }
    } else if (status === 401) {
      error.fywzCategory = 'auth_401'
      error.fywzHint = '未登录或登录态已过期，请重新登录。'
    } else if (status === 403) {
      error.fywzCategory = 'auth_403'
      error.fywzHint = '权限不足。'
    } else if (status === 404) {
      error.fywzCategory = 'not_found'
      error.fywzHint = '请求的 API 路由不存在，请检查后端 app.py 是否已注册该路由。'
    } else if (status === 502) {
      error.fywzCategory = 'upstream_502'
      error.fywzHint = '上游 AI 服务响应异常（502 Bad Gateway）。通常是模型名错误、API Key 无效、或代理连接被中断。'
    } else if (status === 503) {
      error.fywzCategory = 'backend_503'
      error.fywzHint = '后端服务未就绪（503）：可能是 AI 功能开关未启用或 API Key 未配置。'
    } else if (status === 504) {
      error.fywzCategory = 'backend_504'
      error.fywzHint = '后端访问 AI 服务超时（504 Gateway Timeout）。大概率是代理问题：请检查 HTTP_PROXY/HTTPS_PROXY 是否配置正确，代理客户端是否运行中。'
    } else {
      error.fywzCategory = `http_${status || 'unknown'}`
      error.fywzHint = `后端返回 HTTP ${status}，请查看后端日志。`
    }
    return Promise.reject(error)
  },
)

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
  refresh: () => api.post('/recommend/refresh', {}, { timeout: 600000 }),
  similar: (id) => api.get(`/recommend/similar/${id}`),
  guest: () => api.get('/recommend/guest'),
}

export const commentApi = {
  list: (movie_id) => api.get(`/movies/${movie_id}/comments`),
  submit: (data) => api.post('/comments', data),
  remove: (movie_id) => api.delete('/comments', { params: { movie_id } }),
}

export const aiAssistantApi = {
  config: () => api.get('/ai-assistant/config'),
  chat: (message, history = [], user_id = null) => {
    const payload = { message, history }
    if (user_id != null) payload.user_id = user_id
    return api.post('/ai-assistant/chat', payload, { timeout: 90000 })
  },
}
