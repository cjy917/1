/**
 * 【详情页 D1】剧情简介展示辅助
 * 用于 01-DetailHeroSection：判断简介是否被截断、是否需要「展开」
 */

/** 超过此字数默认折叠显示 */
export const SUMMARY_COLLAPSE_CHARS = 280

/** 以句号/问号等结尾视为完整句子，不显示「被截断」提示 */
const SUMMARY_COMPLETE_ENDING = /[。！？…!?.\u2026]$/

/** 简介末尾无标点且较长 → 可能是爬虫截断，显示省略号 */
export function isSummaryIncomplete(content) {
  const summary = (content || '').trim()
  if (!summary) return false
  if (SUMMARY_COMPLETE_ENDING.test(summary)) return false
  return summary.length >= 60
}

/** 格式化展示文本：不完整时在末尾补 … */
export function formatSummaryDisplay(content) {
  const summary = (content || '').trim()
  if (!summary) return ''
  if (!isSummaryIncomplete(summary)) return summary
  if (summary.endsWith('…') || summary.endsWith('...')) return summary
  return `${summary}…`
}

/** 是否超过折叠阈值，控制「展开/收起」按钮 */
export function isSummaryLong(content, limit = SUMMARY_COLLAPSE_CHARS) {
  return (content || '').length > limit
}
