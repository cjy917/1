/**
 * 【详情页 D3】短评区格式化工具
 * 用于 03-DetailReviewsSection：评分显示、星级换算、时间格式
 */

/** 10 分制 → 显示 "8/10" 或 "8.5/10" */
export function formatReviewRating(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return ''
  return Number.isInteger(n) ? `${n}/10` : `${n.toFixed(1)}/10`
}

/** 10 分制 → el-rate 5 星制（除以 2） */
export function reviewStarScore(value) {
  const n = Number(value)
  if (Number.isNaN(n) || n <= 0) return 0
  return n / 2
}

/** ISO 时间 → "YYYY-MM-DD HH:mm" */
export function formatCommentTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
