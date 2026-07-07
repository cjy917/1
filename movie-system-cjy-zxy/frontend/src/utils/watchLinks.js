/**
 * 【详情页 D2a】在线观看 / 详情外链
 * API 优先：GET /api/movies/<id>/watch-links
 * 无 API 结果时用片名+年份拼各平台搜索链接
 */

// ─── 各流媒体平台搜索 URL 模板 ───────────────────────────────────────────────
const PLATFORM_META = [
  ['tencent', '腾讯视频', (q) => `https://v.qq.com/x/search/?q=${encodeURIComponent(q)}`],
  ['iqiyi', '爱奇艺', (q) => `https://so.iqiyi.com/so/q_${encodeURIComponent(q)}`],
  ['youku', '优酷', (q) => `https://www.youku.com/ku/websearch?keyword=${encodeURIComponent(q)}`],
  ['bilibili', '哔哩哔哩', (q) => `https://search.bilibili.com/all?keyword=${encodeURIComponent(q)}`],
  ['mgtv', '芒果TV', (q) => `https://so.mgtv.com/so?k=${encodeURIComponent(q)}`],
]

/** 从双语标题中提取中文片名，用于搜索关键词 */
function extractChineseTitle(title) {
  const parts = (title || '').match(/[\u4e00-\u9fff]+/g)
  if (parts?.length) return parts.join('')
  return (title || '').replace(/\s+[A-Za-z][A-Za-z0-9\s':\-,\.!&]*$/, '').trim()
}

/** 片名 + 年份 → 搜索词 */
function buildSearchQuery(movie) {
  const title = (movie?.title || '').trim()
  const year = movie?.release_year || 0
  const primary = extractChineseTitle(title) || title
  return year ? `${primary} ${year}`.trim() : primary
}

/** 前端兜底：API 无链接时生成各平台搜索页 */
export function buildInstantStreamingLinks(movie) {
  if (!movie?.title) return []
  const query = buildSearchQuery(movie)
  return PLATFORM_META.map(([platform, label, buildUrl]) => ({
    platform,
    label,
    url: buildUrl(query),
    direct: false,
  }))
}

const INFO_PLATFORMS = new Set(['douban', 'tmdb_detail', 'tmdb_watch'])

/** 从电影 detail_url 推断豆瓣/TMDB 详情页 */
export function inferDetailLinkFromMovie(movieData) {
  if (!movieData?.detail_url) return null
  const url = movieData.detail_url
  const source = movieData.source || ''
  if (url.includes('themoviedb.org') || source === 'tmdb') {
    return { platform: 'tmdb_detail', label: 'TMDB', url, direct: false }
  }
  if (url.includes('douban.com') || source === 'douban') {
    return { platform: 'douban', label: '豆瓣', url, direct: false }
  }
  return null
}

export function watchLinkLabel(link) {
  return link?.label || '在线观看'
}

export function detailLinkLabel(link) {
  if (!link) return '了解详情'
  if (link.platform === 'douban') return '了解详情 · 豆瓣'
  if (link.platform === 'tmdb_detail' || link.platform === 'tmdb_watch') return '了解详情 · TMDB'
  return '了解详情'
}

/** 播放区平台按钮：API 直链优先，否则 instant 搜索链接 */
export function resolveStreamingLinks(watchLinks, movie) {
  const apiLinks = (watchLinks?.links || [])
    .filter((item) => !INFO_PLATFORMS.has(item.platform))
    .sort((a, b) => Number(Boolean(b.direct)) - Number(Boolean(a.direct)))
  if (apiLinks.length) return apiLinks
  return buildInstantStreamingLinks(movie)
}

/** Hero 区「了解详情」：豆瓣/TMDB 信息页 */
export function resolveDetailInfoLinks(watchLinks, movie) {
  const links = watchLinks?.links || []
  const infoLinks = links.filter((item) => ['douban', 'tmdb_detail'].includes(item.platform))
  if (infoLinks.length) return infoLinks
  const inferred = inferDetailLinkFromMovie(movie)
  return inferred ? [inferred] : []
}
