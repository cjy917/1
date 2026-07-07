/**
 * 【首页 H2b / 详情 D2】媒体 URL 解析
 * 开发模式下 /api/ 大文件（正片 mp4）直连 Flask:5000，避免 Vite 代理缓冲导致无法播放
 * 使用者：MediaPlayer.vue、HeroCarousel.vue
 */
export function resolveMediaUrl(url) {
  if (!url) return ''
  if (url.startsWith('/api/') && import.meta.env.DEV) {
    return `http://127.0.0.1:5000${url}`
  }
  return url
}
