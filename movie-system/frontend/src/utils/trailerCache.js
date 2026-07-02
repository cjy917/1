import { movieApi } from '../api'

const cache = new Map()
const pending = new Map()
const localTrailerIds = new Set()
let localIdsReady = null

let activeCount = 0
const queue = []
const MAX_CONCURRENT = 4

function isPlayable(data) {
  return data && data.type !== 'none' && (data.embed_url || data.stream_url)
}

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

export function hasLocalTrailer(movieId) {
  return localTrailerIds.has(Number(movieId))
}

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

export function applyLocalTrailerIfExists(movieId) {
  const numericId = Number(movieId)
  if (!hasLocalTrailer(numericId)) return null
  const data = localTrailerSource(numericId)
  cache.set(numericId, data)
  return data
}

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

export { localTrailerSource }
