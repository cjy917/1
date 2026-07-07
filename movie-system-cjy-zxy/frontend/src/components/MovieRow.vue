<!--
  【首页 H3】电影横滑/网格行
  用途：HomeView 各区块（热门/高分/新上映/偏好推荐）复用
  子组件：MovieCard.vue
-->
<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MovieCard from './MovieCard.vue'

// ─── Props ───────────────────────────────────────────────────────────────────
// layout=scroll：横向滚动条；layout=grid：响应式网格
// gridRows>0 时网格只显示固定行数，超出部分在 viewport 内纵向滚动
const props = defineProps({
  title: { type: String, required: true },
  movies: { type: Array, default: () => [] },
  layout: {
    type: String,
    default: 'scroll',
    validator: (value) => ['scroll', 'grid'].includes(value),
  },
  gridRows: { type: Number, default: 0 },
})

const track = ref(null)        // scroll 模式：横向滚动容器
const gridViewport = ref(null) // grid 模式：限制可见行数的外层
const gridRef = ref(null)      // grid 模式：CSS Grid 容器
let gridResizeObserver = null

/** 读取 computed grid-template-columns 得到列数 */
function getGridColumnCount(grid) {
  const template = getComputedStyle(grid).gridTemplateColumns
  if (!template || template === 'none') return 1
  return template.split(' ').filter(Boolean).length
}

/** 根据可见行数计算 viewport 最大高度，避免网格无限拉长 */
function updateGridViewportHeight() {
  const viewport = gridViewport.value
  const grid = gridRef.value
  if (!viewport || !grid) return

  const items = grid.children
  if (!items.length) {
    viewport.style.maxHeight = ''
    return
  }

  const cols = getGridColumnCount(grid)
  const visibleRows = props.gridRows > 0 ? props.gridRows : Math.ceil(items.length / cols)
  const lastIndex = Math.min(cols * visibleRows, items.length) - 1
  const firstRect = items[0].getBoundingClientRect()
  const lastRect = items[lastIndex].getBoundingClientRect()
  viewport.style.maxHeight = `${Math.ceil(lastRect.bottom - firstRect.top)}px`
}

/** grid 模式：监听尺寸变化，窗口缩放时重算高度 */
function setupGridViewport() {
  gridResizeObserver?.disconnect()
  gridResizeObserver = null

  if (props.layout !== 'grid' || props.gridRows <= 0) return

  updateGridViewportHeight()

  if (typeof ResizeObserver === 'undefined') return
  gridResizeObserver = new ResizeObserver(() => updateGridViewportHeight())
  if (gridRef.value) gridResizeObserver.observe(gridRef.value)
  if (gridViewport.value) gridResizeObserver.observe(gridViewport.value)
}

watch(
  () => [props.movies, props.layout, props.gridRows],
  async () => {
    if (props.layout !== 'grid' || props.gridRows <= 0) return
    await nextTick()
    updateGridViewportHeight()
  },
  { deep: true },
)

onMounted(() => {
  setupGridViewport()

  // ─── scroll 模式：鼠标拖拽横向滚动（替代仅滚轮） ─────────────────────────
  if (props.layout !== 'scroll') return

  let isDown = false
  let startX = 0
  let scrollLeft = 0
  const el = track.value
  if (!el) return

  el.addEventListener('mousedown', (e) => {
    isDown = true
    startX = e.pageX - el.offsetLeft
    scrollLeft = el.scrollLeft
  })
  el.addEventListener('mouseleave', () => { isDown = false })
  el.addEventListener('mouseup', () => { isDown = false })
  el.addEventListener('mousemove', (e) => {
    if (!isDown) return
    e.preventDefault()
    el.scrollLeft = scrollLeft - (e.pageX - el.offsetLeft - startX)
  })
})

onBeforeUnmount(() => {
  gridResizeObserver?.disconnect()
})
</script>

<template>
  <!-- 区块标题 + 电影列表 -->
  <section class="section-surface py-8">
    <div class="mx-auto max-w-[1400px] px-4 lg:px-8">
      <h2 v-if="title" class="mb-5 text-2xl font-bold">{{ title }}</h2>
      <!-- grid 布局（详情页相似推荐等） -->
      <div
        v-if="layout === 'grid'"
        ref="gridViewport"
        class="movie-grid-viewport"
        :class="{ 'movie-grid-viewport--scroll': gridRows > 0 }"
      >
        <div
          ref="gridRef"
          class="movie-grid grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
          <MovieCard v-for="movie in movies" :key="movie.movie_id" :movie="movie" />
        </div>
      </div>
      <!-- scroll 布局（首页各横滑栏） -->
      <div v-else ref="track" class="movie-row-scroll flex gap-4 overflow-x-auto pb-3 scroll-smooth">
        <MovieCard v-for="movie in movies" :key="movie.movie_id" :movie="movie" class="movie-row-scroll__card" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.movie-grid :deep(article) {
  width: 100%;
}

.movie-grid-viewport--scroll {
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  padding-right: 0.25rem;
}

.movie-row-scroll__card {
  flex: 0 0 auto;
  width: 9.5rem;
}

@media (min-width: 640px) {
  .movie-row-scroll__card {
    width: 10.5rem;
  }
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-thumb {
  background: var(--fywz-accent);
  opacity: 0.5;
  border-radius: 999px;
}
</style>
