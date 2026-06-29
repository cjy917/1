/** 大文件正片直连后端，避免 Vite 开发代理缓冲导致无法播放 */
export function resolveMediaUrl(url) {
  if (!url) return ''
  if (url.startsWith('/api/') && import.meta.env.DEV) {
    return `http://127.0.0.1:5000${url}`
  }
  return url
}
