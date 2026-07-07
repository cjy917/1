/**
 * 【详情页 D1】Hero 背景渐变色
 * 颜色来自 GET /api/movies/<id>/hero-theme（poster_theme_service 从海报采样）
 * 用于 01-DetailHeroSection 的 flow 动画层 + 左侧 scrim 遮罩
 */

/** 多色流动渐变背景（CSS backgroundImage + backgroundSize 动画） */
export function buildHeroFlowStyle(theme) {
  const r = theme?.r ?? 13
  const g = theme?.g ?? 37
  const b = theme?.b ?? 63
  const shade = (factor) =>
    `${Math.min(255, Math.round(r * factor))}, ${Math.min(255, Math.round(g * factor))}, ${Math.min(255, Math.round(b * factor))}`
  const glow = `${Math.min(255, r + 68)}, ${Math.min(255, g + 32)}, ${Math.min(255, b + 38)}`
  const hot = `${Math.min(255, r + 95)}, ${Math.min(255, g + 52)}, ${Math.min(255, b + 18)}`
  return {
    backgroundImage: `linear-gradient(125deg, rgb(${shade(0.28)}) 0%, rgb(${r}, ${g}, ${b}) 16%, rgb(${hot}) 34%, rgb(${glow}) 50%, rgb(${shade(0.52)}) 68%, rgb(${hot}) 84%, rgb(${shade(0.3)}) 100%)`,
    backgroundSize: '500% 500%',
  }
}

/** 左侧深色 scrim，保证标题文字可读 */
export function buildHeroScrimStyle(theme) {
  const r = theme?.r ?? 13
  const g = theme?.g ?? 37
  const b = theme?.b ?? 63
  const left = `${Math.max(0, r - 8)}, ${Math.max(0, g - 8)}, ${Math.max(0, b - 8)}`
  const mid = `${Math.round(r * 0.55)}, ${Math.round(g * 0.55)}, ${Math.round(b * 0.55)}`
  return {
    background: `linear-gradient(to right, rgba(${left}, 0.62) 0%, rgba(${mid}, 0.24) 36%, rgba(${mid}, 0.06) 58%, transparent 100%)`,
  }
}
