/**
 * 【详情页 D1】演职员/类型/年份/语言 → 路由
 * 用于 01-DetailHeroSection + DetailCreditRow
 */

/** 解析后端 pipe/逗号分隔的姓名字符串 → 数组 */
export function parseCreditNames(value) {
  if (!value) return []
  if (Array.isArray(value)) {
    return value.map((part) => String(part).trim()).filter(Boolean)
  }
  return String(value)
    .split(/[|,，、/]/)
    .map((part) => part.trim())
    .filter(Boolean)
}

/** 点击导演/演员 → PersonView，可选 role 查询参数 */
export function buildPersonRoute(name, role) {
  return {
    name: 'person-detail',
    params: { name },
    query: role ? { role } : undefined,
  }
}

/** 点击上映年份 → MoviesView 按年筛选 */
export function buildMoviesYearRoute(year) {
  const value = String(year || '').trim()
  if (!value) return { name: 'movies' }
  return {
    name: 'movies',
    query: { year_from: value, year_to: value },
  }
}

/** 点击类型标签 → MoviesView 按 genre 筛选 */
export function buildMoviesGenreRoute(genre) {
  const value = String(genre || '').trim()
  if (!value) return { name: 'movies' }
  return {
    name: 'movies',
    query: { genres: value },
  }
}

/** 点击语言 → MoviesView 按 language 筛选 */
export function buildMoviesLanguageRoute(language) {
  const value = String(language || '').trim()
  if (!value) return { name: 'movies' }
  return {
    name: 'movies',
    query: { languages: value },
  }
}
