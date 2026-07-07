/**
 * 【首页 H2 / 详情 D1e】预告片缓存与预加载
 * 首页 MovieCard 悬停、HeroCarousel、详情页共用
 * API：GET /api/movies/<id>/trailer、GET /api/trailers/<id>、GET /api/trailers/local-ids
 */
import { movieApi } from '../api'

// ─── 内存缓存与并发控制 ───────────────────────────────────────────────────────
const cache = new Map()           // movieId → trailer 对象
const pending = new Map()         // movieId → 进行中的 Promise（去重）
const localTrailerIds = new Set() // 后端已确认有本地 mp4 的 id
let localIdsReady = null

let activeCount = 0
const queue = []
const MAX_CONCURRENT = 4 // 同时最多 4 个 trailer 请求，避免首页卡片同时 hover 打爆后端

/** 判断 trailer 数据是否可播放（有 embed_url 或 stream_url） */
function isPlayable(data) {
  return data && data.type !== 'none' && (data.embed_url || data.stream_url)
}

/** 构造本地 mp4 预告源（走 /api/trailers/<id> 静态文件） */
function localTrailerSource(movieId) {
  const url = `/api/trailers/${movieId}`
  return {
    type: 'mp4',
    video_key: `local:${movieId}`,
    embed_url: url,
    stream_url: url,
    watch_url: url,
    message: 'TMDB 官方预告',
  }
}

function hasLocalTrailer(movieId) {
  return localTrailerIds.has(Number(movieId))
}

/** 启动时拉取本地预告 id 列表，命中则直接写入 cache */
export async function initLocalTrailerIds() {
  if (localIdsReady) return localIdsReady
  localIdsReady = (async () => {
    try {
      const { data } = await movieApi.trailerLocalIds()
      localTrailerIds.clear()
      for (const id of data.ids || []) {
        localTrailerIds.add(Number(id))
        cache.set(Number(id), localTrailerSource(Number(id)))
      }
    } catch {
      localTrailerIds.clear()
    }
  })()
  return localIdsReady
}

/** 离线或 API 失败时，HEAD 探测本地文件是否存在 */
export async function tryLocalTrailerFallback(movieId) {
  const numericId = Number(movieId)
  if (hasLocalTrailer(numericId)) {
    const data = localTrailerSource(numericId)
    cache.set(numericId, data)
    return data
  }
  const url = `/api/trailers/${numericId}`
  try {
    const res = await fetch(url, { method: 'HEAD' })
    if (res.ok) {
      localTrailerIds.add(numericId)
      const data = localTrailerSource(numericId)
      cache.set(numericId, data)
      return data
    }
  } catch {
    // offline or backend unavailable
  }
  return null
}

/** 队列调度：限制并发数 */
function runNext() {
  if (activeCount >= MAX_CONCURRENT || !queue.length) return
  const job = queue.shift()
  activeCount += 1
  job().finally(() => {
    activeCount -= 1
    runNext()
  })
}

function enqueue(task) {
  return new Promise((resolve, reject) => {
    queue.push(() => task().then(resolve, reject))
    runNext()
  })
}

export function getCachedTrailer(movieId) {
  return cache.get(Number(movieId)) ?? null
}

/** 若已知有本地预告，同步返回（悬停时零延迟） */
export function applyLocalTrailerIfExists(movieId) {
  const numericId = Number(movieId)
  if (!hasLocalTrailer(numericId)) return null
  const data = localTrailerSource(numericId)
  cache.set(numericId, data)
  return data
}

/**
 * 【核心】预加载预告：先查 cache → 排队请求 API → 失败则本地回退
 * @param {number} movieId
 * @param {{ refresh?: boolean, autoplay?: boolean }} options
 */
export function prefetchTrailer(movieId, options = {}) {
  const numericId = Number(movieId)
  const { refresh = false } = options

  if (!refresh) {
    const instant = applyLocalTrailerIfExists(numericId)
    if (instant) return Promise.resolve(instant)
  }

  const cached = cache.get(numericId)
  if (!refresh && cached) {
    if (cached.type === 'mp4' || cached.type === 'youtube' || cached.type === 'bilibili') {
      return Promise.resolve(cached)
    }
  }
  if (!refresh && pending.has(numericId)) return pending.get(numericId)

  const promise = enqueue(async () => {
    try {
      const params = {}
      if (options.autoplay) params.autoplay = 1
      if (refresh || (cached && cached.type !== 'mp4' && cached.type !== 'none')) {
        params.refresh = 1
      }
      const { data } = await movieApi.trailer(numericId, params)
      if (data?.type && data.type !== 'none') {
        cache.set(numericId, data)
      } else {
        cache.delete(numericId)
      }
      return data
    } catch {
      const local = await tryLocalTrailerFallback(numericId)
      if (local) return local
      cache.delete(numericId)
      return { type: 'none', message: '预告加载失败' }
    } finally {
      pending.delete(numericId)
    }
  })

  pending.set(numericId, promise)
  return promise
}

export function isTrailerPlayable(data) {
  return isPlayable(data)
}

export function isLocalTrailer(data) {
  return data?.type === 'mp4'
}

export function isRemoteTrailer(data) {
  return ['youtube', 'bilibili'].includes(data?.type)
}
