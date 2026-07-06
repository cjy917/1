<script setup>
// 导入Vue核心函数和工具
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { movieApi } from '../api'
import MovieCard from '../components/MovieCard.vue'

// 初始化路由实例
const route = useRoute()
const router = useRouter()

// 响应式数据定义
const filters = ref({ years: [], genres: [], languages: [] })  // 筛选选项列表（年份、类型、语言）
const movies = ref([])                                         // 电影列表数据
const total = ref(0)                                           // 电影总数
const page = ref(1)                                            // 当前页码
const pages = ref(1)                                           // 总页数
let syncingRoute = false                                       // 路由同步标志，防止循环触发

/**
 * 默认查询参数初始化函数
 * 返回一个包含所有筛选条件的默认对象
 */
const defaultQuery = () => ({
  q: '',                    // 搜索关键词
  selectedGenres: [],       // 选中的类型列表
  selectedLanguages: [],    // 选中的语言列表
  year_from: '',            // 年份范围起始
  year_to: '',              // 年份范围结束
  sort: 'rating_desc',      // 排序方式（默认评分降序）
  min_rating: '',           // 最低评分
  max_rating: '',           // 最高评分
  min_votes: 0,             // 最少投票人数
})

// 当前查询状态（响应式），用于同步路由参数
const query = reactive(defaultQuery())

// 筛选面板展开/收起状态
const sortOpen = ref(false)    // 排序面板是否展开
const filtersOpen = ref(true)  // 筛选面板是否展开

// 草稿状态，用于用户在筛选面板中操作但未提交的临时数据
const draft = reactive({
  q: '',
  selectedGenres: [],
  selectedLanguages: [],
  year_from: '',
  year_to: '',
  sort: 'rating_desc',
  min_rating: '',
  max_rating: '',
  min_votes: 0,
})

// 排序选项配置
const sortOptions = [
  { value: 'popular', label: '热门降序' },
  { value: 'popular_asc', label: '热门升序' },
  { value: 'rating_desc', label: '评分降序' },
  { value: 'rating_asc', label: '评分升序' },
  { value: 'year_desc', label: '发行日期降序' },
  { value: 'year_asc', label: '发行日期升序' },
]

/**
 * 同步草稿状态从当前查询状态
 * 当query发生变化时，将其值同步到draft，保持筛选面板显示与当前查询一致
 */
function syncDraftFromQuery() {
  draft.q = query.q || ''
  draft.selectedGenres = [...(query.selectedGenres || [])]
  draft.selectedLanguages = [...(query.selectedLanguages || [])]
  draft.year_from = query.year_from || ''
  draft.year_to = query.year_to || ''
  draft.sort = query.sort || 'rating_desc'
  draft.min_rating = query.min_rating ?? ''
  draft.max_rating = query.max_rating ?? ''
  draft.min_votes = Number(query.min_votes || 0)
}

/**
 * 评分范围计算属性（双向绑定）
 * 将draft中的min_rating和max_rating转换为滑块需要的数组格式
 * 空值时使用默认值0-10，超出范围时清空
 */
const ratingRange = computed({
  get() {
    const min = draft.min_rating === '' ? 0 : Number(draft.min_rating)
    const max = draft.max_rating === '' ? 10 : Number(draft.max_rating)
    return [Number.isNaN(min) ? 0 : min, Number.isNaN(max) ? 10 : max]
  },
  set([min, max]) {
    draft.min_rating = min <= 0 ? '' : String(min)
    draft.max_rating = max >= 10 ? '' : String(max)
  },
})

/**
 * 最少投票人数计算属性（双向绑定）
 * 将draft中的min_votes转换为数字格式
 */
const minVotes = computed({
  get: () => Number(draft.min_votes || 0),
  set: (value) => {
    draft.min_votes = value
  },
})

/**
 * 排序方式变更处理
 * 更新draft中的排序方式
 */
function onSortChange(event) {
  draft.sort = event.target.value
}

/**
 * 年份范围变更处理
 * 更新draft中的年份范围，并进行校验：起始年份不能大于结束年份
 */
function onYearChange(field, event) {
  const value = event.target.value
  draft[field] = value
  const from = field === 'year_from' ? value : draft.year_from
  const to = field === 'year_to' ? value : draft.year_to
  // 校验：如果起始年份大于结束年份，自动调整结束年份等于起始年份
  if (from && to && Number(from) > Number(to)) {
    if (field === 'year_from') draft.year_to = value
    else draft.year_from = value
  }
}

/**
 * 类型切换处理（多选）
 * 如果类型已选中则取消选中，否则添加选中
 */
function toggleGenre(genre) {
  const index = draft.selectedGenres.indexOf(genre)
  if (index >= 0) draft.selectedGenres.splice(index, 1)
  else draft.selectedGenres.push(genre)
}

/**
 * 语言切换处理（多选）
 * 如果语言已选中则取消选中，否则添加选中
 */
function toggleLanguage(language) {
  const index = draft.selectedLanguages.indexOf(language)
  if (index >= 0) draft.selectedLanguages.splice(index, 1)
  else draft.selectedLanguages.push(language)
}

/**
 * 判断类型是否处于选中状态
 */
function isGenreActive(genre) {
  return draft.selectedGenres.includes(genre)
}

/**
 * 判断语言是否处于选中状态
 */
function isLanguageActive(language) {
  return draft.selectedLanguages.includes(language)
}

/**
 * 提交搜索
 * 将draft中的筛选条件应用到query，并触发数据重新加载
 */
function submitSearch() {
  onApply({
    q: draft.q.trim(),
    selectedGenres: [...draft.selectedGenres],
    selectedLanguages: [...draft.selectedLanguages],
    year_from: draft.year_from,
    year_to: draft.year_to,
    sort: draft.sort,
    min_rating: draft.min_rating,
    max_rating: draft.max_rating,
    min_votes: draft.min_votes,
  }, true)  // reload=true 表示需要重新加载数据
}

/**
 * 重置筛选条件
 * 将draft重置为默认值，并触发onReset重新加载数据
 */
function resetFilters() {
  Object.assign(draft, {
    q: '',
    selectedGenres: [],
    selectedLanguages: [],
    year_from: '',
    year_to: '',
    sort: 'rating_desc',
    min_rating: '',
    max_rating: '',
    min_votes: 0,
  })
  onReset()
}

/**
 * 监听query变化，同步到draft
 * 深度监听，立即执行
 */
watch(
  () => query,
  () => syncDraftFromQuery(),
  { deep: true, immediate: true },
)

/**
 * 逗号分隔字符串解析函数
 * 将逗号分隔的字符串转换为数组，过滤空值并去除首尾空格
 */
function splitCsv(value) {
  if (!value) return []
  return String(value).split(',').map((item) => item.trim()).filter(Boolean)
}

/**
 * 解析路由查询参数
 * 将URL中的查询参数转换为内部使用的查询对象格式
 */
function parseRouteQuery(routeQuery = {}) {
  return {
    q: routeQuery.q || '',
    selectedGenres: splitCsv(routeQuery.genres),      // 将逗号分隔的类型字符串转为数组
    selectedLanguages: splitCsv(routeQuery.languages), // 将逗号分隔的语言字符串转为数组
    year_from: routeQuery.year_from || '',
    year_to: routeQuery.year_to || '',
    sort: routeQuery.sort || 'rating_desc',
    min_rating: routeQuery.min_rating || '',
    max_rating: routeQuery.max_rating || '',
    min_votes: routeQuery.min_votes ? Number(routeQuery.min_votes) : 0,
  }
}

/**
 * 构建路由查询参数
 * 将内部查询对象转换为URL查询参数格式，只保留非默认值
 */
function buildRouteQuery() {
  const nextQuery = {}
  if (query.q) nextQuery.q = query.q
  if (query.selectedGenres.length) nextQuery.genres = query.selectedGenres.join(',')
  if (query.selectedLanguages.length) nextQuery.languages = query.selectedLanguages.join(',')
  if (query.year_from) nextQuery.year_from = query.year_from
  if (query.year_to) nextQuery.year_to = query.year_to
  if (query.sort && query.sort !== defaultQuery().sort) nextQuery.sort = query.sort
  if (query.min_rating) nextQuery.min_rating = String(query.min_rating)
  if (query.max_rating) nextQuery.max_rating = String(query.max_rating)
  if (query.min_votes > 0) nextQuery.min_votes = String(query.min_votes)
  if (page.value > 1) nextQuery.page = String(page.value)
  return nextQuery
}

/**
 * 生成路由查询参数签名
 * 将路由查询参数序列化为字符串，用于比较是否发生变化
 */
function routeQuerySignature(routeQuery = {}) {
  return JSON.stringify({
    ...parseRouteQuery(routeQuery),
    page: routeQuery.page ? Math.max(1, Number(routeQuery.page) || 1) : 1,
  })
}

/**
 * 生成当前状态查询参数签名
 * 将内部查询状态序列化为字符串，用于与路由参数比较
 */
function stateQuerySignature() {
  return JSON.stringify({
    q: query.q || '',
    selectedGenres: [...query.selectedGenres],
    selectedLanguages: [...query.selectedLanguages],
    year_from: query.year_from || '',
    year_to: query.year_to || '',
    sort: query.sort || defaultQuery().sort,
    min_rating: query.min_rating || '',
    max_rating: query.max_rating || '',
    min_votes: Number(query.min_votes || 0),
    page: page.value,
  })
}

/**
 * 加载筛选选项
 * 从API获取可用的年份、类型、语言选项列表
 */
async function loadFilters() {
  const { data } = await movieApi.filters()
  filters.value = data
}

/**
 * 加载电影列表
 * 根据当前查询条件从API获取电影数据，包含分页信息
 */
async function loadMovies() {
  const params = {
    page: page.value,
    page_size: 24,
    keyword: query.q || undefined,
    genres: query.selectedGenres.length ? query.selectedGenres.join(',') : undefined,
    languages: query.selectedLanguages.length ? query.selectedLanguages.join(',') : undefined,
    year_from: query.year_from || undefined,
    year_to: query.year_to || undefined,
    sort: query.sort,
    min_rating: query.min_rating || undefined,
    max_rating: query.max_rating || undefined,
    min_votes: query.min_votes > 0 ? query.min_votes : undefined,
  }
  const { data } = await movieApi.list(params)
  movies.value = data.items
  total.value = data.total
  pages.value = data.pages
}

/**
 * 应用查询参数补丁
 * 将补丁对象中的值更新到query，处理数组类型字段的特殊情况
 */
function applyQueryPatch(patch = {}) {
  // 处理类型数组（特殊处理：先清空再重新赋值，保持响应式）
  if (Array.isArray(patch.selectedGenres)) {
    query.selectedGenres.splice(0, query.selectedGenres.length, ...patch.selectedGenres)
  }
  // 处理语言数组（同上）
  if (Array.isArray(patch.selectedLanguages)) {
    query.selectedLanguages.splice(0, query.selectedLanguages.length, ...patch.selectedLanguages)
  }
  // 处理其他字段
  const { selectedGenres, selectedLanguages, ...rest } = patch
  if (Object.keys(rest).length) {
    Object.assign(query, rest)
  }
}

/**
 * 同步路由查询参数
 * 将当前查询状态同步到URL，设置syncingRoute标志防止循环触发
 */
async function syncRouteQuery() {
  syncingRoute = true
  await router.replace({ name: 'movies', query: buildRouteQuery() })
  await nextTick()
  syncingRoute = false
}

/**
 * 应用查询变更
 * 更新query状态，可选重新加载数据并同步路由
 */
async function onApply(patch = {}, reload = true) {
  applyQueryPatch(patch)
  if (reload) {
    page.value = 1           // 重置页码为1
    await syncRouteQuery()   // 同步路由参数
    loadMovies()             // 重新加载电影数据
  }
}

/**
 * 重置查询条件
 * 将query重置为默认值，重新加载数据并同步路由
 */
async function onReset() {
  applyQueryPatch(defaultQuery())
  page.value = 1
  await syncRouteQuery()
  loadMovies()
}

/**
 * 分页跳转
 * 更新页码，同步路由参数并重新加载数据
 */
async function goPage(nextPage) {
  page.value = nextPage
  await syncRouteQuery()
  loadMovies()
}

/**
 * 从路由恢复查询状态
 * 根据URL中的查询参数恢复内部查询状态和页码
 */
function restoreFromRoute(routeQuery = route.query) {
  applyQueryPatch(parseRouteQuery(routeQuery))
  page.value = routeQuery.page ? Math.max(1, Number(routeQuery.page) || 1) : 1
}

/**
 * 监听路由查询参数变化
 * 当路由参数发生变化时，恢复查询状态并重新加载数据
 * 通过syncingRoute标志和签名比较防止循环触发
 */
watch(
  () => route.query,
  (routeQuery) => {
    // 如果不是电影页面或正在同步路由，忽略
    if (route.name !== 'movies' || syncingRoute) return
    // 如果路由参数与当前状态相同，忽略
    if (routeQuerySignature(routeQuery) === stateQuerySignature()) return
    // 恢复查询状态并重新加载数据
    restoreFromRoute(routeQuery)
    loadMovies()
  },
  { deep: true },
)

/**
 * 页面挂载时初始化
 * 从路由恢复查询状态，加载筛选选项，加载电影数据
 */
onMounted(async () => {
  restoreFromRoute(route.query)
  await loadFilters()
  loadMovies()
})
</script>

<template>
  <!-- 电影列表页面根容器，限定最大宽度、左右留白、上下内边距 -->
  <div class="movies-page mx-auto max-w-7xl px-4 py-8">
    <!-- 页面头部：标题 + 筛选结果统计 -->
    <div class="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold">电影库</h1>
        <!-- 有搜索关键词时展示检索条数 -->
        <p v-if="query.q" class="mt-1 text-sm text-muted">搜索「{{ query.q }}」，共 {{ total }} 部结果</p>
        <!-- 无关键词展示全部电影总数 -->
        <p v-else class="mt-1 text-sm text-muted">共 {{ total }} 部电影</p>
      </div>
    </div>
    <!-- 左右布局：侧边筛选栏 + 电影卡片列表，大屏侧边固定280px -->
    <div class="grid gap-6 lg:grid-cols-[280px_1fr]">
      <!-- 左侧筛选侧边栏 -->
      <aside class="movie-filter-sidebar">
        <!-- 排序折叠面板 -->
        <div class="filter-card">
          <!-- 折叠面板头部，点击展开/收起排序下拉 -->
          <button type="button" class="filter-card__header" @click="sortOpen = !sortOpen">
            <span>排序</span>
            <!-- 下拉箭头，open状态旋转180度 -->
            <svg
              class="filter-card__chevron"
              :class="{ 'filter-card__chevron--open': sortOpen }"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fill-rule="evenodd"
                d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
          <!-- 排序面板内容，控制显隐 -->
          <div v-show="sortOpen" class="filter-card__body">
            <label class="filter-label">结果排序</label>
            <!-- 排序下拉选择框，切换触发排序更新 -->
            <select :value="draft.sort" class="filter-input filter-input--select" @change="onSortChange">
              <option v-for="item in sortOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
        </div>

        <!-- 综合筛选折叠面板 -->
        <div class="filter-card">
          <!-- 筛选面板头部，控制展开收起 -->
          <button type="button" class="filter-card__header" @click="filtersOpen = !filtersOpen">
            <span>筛选</span>
            <svg
              class="filter-card__chevron"
              :class="{ 'filter-card__chevron--open': filtersOpen }"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fill-rule="evenodd"
                d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
                clip-rule="evenodd"
              />
            </svg>
          </button>

          <!-- 筛选面板主体，堆叠式筛选区块 -->
          <div v-show="filtersOpen" class="filter-card__body filter-card__body--stacked">
            <!-- 年份筛选区块 -->
            <section class="filter-block">
              <h4 class="filter-block__title">发行日期</h4>
              <p class="filter-block__hint">按上映年份筛选</p>
              <div class="filter-year-row">
                <!-- 起始年份下拉 -->
                <label class="filter-year-field">
                  <span>从</span>
                  <select
                    :value="draft.year_from"
                    class="filter-input"
                    @change="onYearChange('year_from', $event)"
                  >
                    <option value="">不限</option>
                    <option v-for="y in filters.years" :key="`from-${y}`" :value="String(y)">{{ y }}</option>
                  </select>
                </label>
                <!-- 结束年份下拉 -->
                <label class="filter-year-field">
                  <span>到</span>
                  <select
                    :value="draft.year_to"
                    class="filter-input"
                    @change="onYearChange('year_to', $event)"
                  >
                    <option value="">不限</option>
                    <option v-for="y in filters.years" :key="`to-${y}`" :value="String(y)">{{ y }}</option>
                  </select>
                </label>
              </div>
            </section>

            <!-- 电影类型多选标签 -->
            <section class="filter-block">
              <h4 class="filter-block__title">类型</h4>
              <p class="filter-block__hint">可多选，匹配任一类型即可</p>
              <div class="genre-chips">
                <button
                  v-for="genre in filters.genres"
                  :key="genre"
                  type="button"
                  class="genre-chip"
                  :class="{ 'genre-chip--active': isGenreActive(genre) }"
                  @click="toggleGenre(genre)"
                >
                  {{ genre }}
                </button>
              </div>
            </section>

            <!-- 影片语言多选标签 -->
            <section class="filter-block">
              <h4 class="filter-block__title">语言</h4>
              <p class="filter-block__hint">可多选，匹配任一语言即可</p>
              <div class="genre-chips">
                <button
                  v-for="language in filters.languages"
                  :key="language"
                  type="button"
                  class="genre-chip"
                  :class="{ 'genre-chip--active': isLanguageActive(language) }"
                  @click="toggleLanguage(language)"
                >
                  {{ language }}
                </button>
              </div>
            </section>

            <!-- 评分区间滑块筛选 -->
            <section class="filter-block">
              <h4 class="filter-block__title">用户评分</h4>
              <el-slider
                v-model="ratingRange"
                class="filter-slider"
                range
                :min="0"
                :max="10"
                :step="0.5"
                :show-tooltip="false"
              />
              <!-- 滑块刻度文字 -->
              <div class="filter-slider-scale">
                <span>0</span>
                <span>5</span>
                <span>10</span>
              </div>
            </section>

            <!-- 最少投票人数滑块筛选 -->
            <section class="filter-block">
              <h4 class="filter-block__title">最少人数投票</h4>
              <el-slider
                v-model="minVotes"
                class="filter-slider"
                :min="0"
                :max="500"
                :step="50"
                :show-tooltip="false"
              />
              <div class="filter-slider-scale filter-slider-scale--wide">
                <span>0</span>
                <span>100</span>
                <span>200</span>
                <span>300</span>
                <span>400</span>
                <span>500</span>
              </div>
            </section>

            <!-- 关键词输入框 -->
            <section class="filter-block filter-block--last">
              <h4 class="filter-block__title">关键词</h4>
              <input
                v-model="draft.q"
                class="filter-input filter-input--keyword"
                placeholder="按关键词筛选…"
                @keyup.enter="submitSearch"
              />
            </section>

            <!-- 筛选操作按钮：搜索、重置 -->
            <div class="filter-actions">
              <button type="button" class="filter-actions__search" @click="submitSearch">
                搜索
              </button>
              <button type="button" class="filter-actions__reset" @click="resetFilters">
                重置
              </button>
            </div>
          </div>
        </div>
      </aside>
      <!-- 右侧电影卡片列表 + 分页区域 -->
      <section>
        <!-- 响应式网格：移动端2列、平板3列、大屏4列电影卡片 -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
          <MovieCard v-for="movie in movies" :key="movie.movie_id" :movie="movie" />
        </div>
        <!-- 分页控件：上一页、页码、下一页 -->
        <div class="mt-8 flex items-center justify-center gap-3">
          <button
            class="movies-page__pager rounded-full px-4 py-2 text-sm disabled:opacity-40"
            :disabled="page <= 1"
            @click="goPage(page - 1)"
          >
            上一页
          </button>
          <span class="text-sm text-muted">{{ page }} / {{ pages }}</span>
          <button
            class="movies-page__pager rounded-full px-4 py-2 text-sm disabled:opacity-40"
            :disabled="page >= pages"
            @click="goPage(page + 1)"
          >
            下一页
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* 分页按钮基础样式 */
.movies-page__pager {
  border: 1px solid var(--fywz-border);
  background: var(--fywz-surface-2);
  color: var(--fywz-text);
}
/* 分页按钮hover激活色 */
.movies-page__pager:hover:not(:disabled) {
  border-color: #01b4e4;
  color: #01b4e4;
}
/* 侧边筛选栏弹性布局，卡片间距 */
.movie-filter-sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
/* 筛选卡片容器样式：边框、圆角、阴影 */
.filter-card {
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  border-radius: 8px;
  background: var(--fywz-filter-bg, #fff);
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.05);
}
/* 折叠面板头部按钮 */
.filter-card__header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  border: none;
  background: transparent;
  padding: 0.85rem 1rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--fywz-text);
  cursor: pointer;
}
/* 折叠箭头基础样式，旋转过渡动画 */
.filter-card__chevron {
  width: 1.1rem;
  height: 1.1rem;
  color: var(--fywz-muted);
  transition: transform 0.2s;
}
/* 展开状态箭头翻转180度 */
.filter-card__chevron--open {
  transform: rotate(180deg);
}
/* 筛选卡片内容内边距 */
.filter-card__body {
  padding: 0 1rem 1rem;
}
.filter-card__body--stacked {
  padding-top: 0;
}
/* 筛选标签文字说明 */
.filter-label {
  display: block;
  margin-bottom: 0.45rem;
  font-size: 0.85rem;
  color: var(--fywz-muted);
}
/* 单个筛选区块，底部分隔线 */
.filter-block {
  padding: 0.95rem 0;
  border-bottom: 1px solid var(--fywz-filter-border, #e3e3e3);
}
/* 最后一个区块去除下边框 */
.filter-block--last {
  border-bottom: none;
  padding-bottom: 0.25rem;
}
/* 筛选区块标题 */
.filter-block__title {
  margin: 0 0 0.65rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--fywz-text);
}
/* 筛选提示小字 */
.filter-block__hint {
  margin: -0.35rem 0 0.55rem;
  font-size: 0.75rem;
  color: var(--fywz-muted);
}
/* 年份起止选择行布局 */
.filter-year-row {
  display: grid;
  gap: 0.65rem;
}
.filter-year-field {
  display: grid;
  grid-template-columns: 1.5rem 1fr;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: var(--fywz-muted);
}
/* 通用输入框样式 */
.filter-input {
  width: 100%;
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  border-radius: 8px;
  background: var(--fywz-filter-bg, #fff);
  padding: 0.45rem 0.65rem;
  font-size: 0.875rem;
  color: var(--fywz-text);
  outline: none;
}
/* 输入框聚焦高亮边框 */
.filter-input:focus {
  border-color: #01b4e4;
}
/* 关键词输入框加高内边距 */
.filter-input--keyword {
  padding: 0.55rem 0.75rem;
}
/* 下拉选择框自定义下拉箭头 */
.filter-input--select {
  min-height: 38px;
  cursor: pointer;
  padding-right: 2rem;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%2352606d'%3E%3Cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z' clip-rule='evenodd'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.55rem center;
  background-size: 1rem;
  appearance: none;
}
/* 类型/语言标签自动换行布局 */
.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
/* 筛选标签默认样式 */
.genre-chip {
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  border-radius: 999px;
  background: var(--fywz-filter-bg, #fff);
  padding: 0.28rem 0.72rem;
  font-size: 0.82rem;
  line-height: 1.35;
  color: var(--fywz-text);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.genre-chip:hover {
  border-color: #01b4e4;
}
/* 选中标签高亮底色文字 */
.genre-chip--active {
  border-color: #01b4e4;
  background: #01b4e4;
  color: #042541;
  font-weight: 600;
}
/* 滑块外层边距 */
.filter-slider {
  margin: 0 0.35rem;
}
/* 深度修改ElementPlus滑块轨道 */
.filter-slider :deep(.el-slider__runway) {
  height: 4px;
  background: #d5dbe3;
}
/* 滑块选中区间蓝色 */
.filter-slider :deep(.el-slider__bar) {
  background: #01b4e4;
}
/* 滑块圆点样式 */
.filter-slider :deep(.el-slider__button) {
  width: 16px;
  height: 16px;
  border: none;
  background: #01b4e4;
}
/* 滑块刻度文字两端对齐 */
.filter-slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.35rem;
  font-size: 0.75rem;
  color: var(--fywz-muted);
}
.filter-slider-scale--wide {
  font-size: 0.7rem;
}
/* 筛选操作按钮双栏网格 */
.filter-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  padding-top: 0.85rem;
}
/* 搜索、重置按钮通用基础 */
.filter-actions__search,
.filter-actions__reset {
  border-radius: 999px;
  padding: 0.62rem 0.85rem;
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
  transition: filter 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
/* 搜索主按钮蓝色底色 */
.filter-actions__search {
  border: none;
  background: #01b4e4;
  color: #032541;
}
.filter-actions__search:hover {
  filter: brightness(1.05);
}
/* 重置按钮描边样式 */
.filter-actions__reset {
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  background: var(--fywz-filter-bg, #fff);
  color: var(--fywz-text);
}
.filter-actions__reset:hover {
  border-color: #01b4e4;
  color: #01b4e4;
}
</style>