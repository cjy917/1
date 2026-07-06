<script setup>
// 导入Vue核心函数和工具
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { movieApi } from '../api'

// 定义组件属性：控制搜索框的显示/隐藏
const props = defineProps({
  open: { type: Boolean, default: false },
})

// 定义组件事件：关闭搜索框
const emit = defineEmits(['close'])

// 初始化路由实例
const router = useRouter()

// 响应式数据定义
const keyword = ref('')                    // 当前输入的搜索关键词
const suggestions = ref([])                // 搜索建议列表
const popularMovies = ref([])              // 当前展示的热门电影列表
const inputRef = ref(null)                 // 搜索输入框DOM引用
const measureRef = ref(null)               // 测量输入文本宽度的隐藏元素引用
const completionRef = ref(null)            // 搜索补全文本元素引用
let timer = null                           // 防抖定时器

/**
 * 搜索补全后缀计算属性
 * 根据当前输入的关键词，从搜索建议中筛选以该关键词开头的电影，
 * 按评分降序排序，取评分最高的电影的后缀部分作为补全提示
 */
const completionSuffix = computed(() => {
  if (!keyword.value.trim()) return ''
  const q = keyword.value.trim()
  // 筛选以当前关键词开头且长度大于关键词的电影
  const candidates = suggestions.value.filter(item => 
    item.title && item.title.startsWith(q) && item.title.length > q.length
  )
  if (!candidates.length) return ''
  // 按评分降序排序
  const sorted = [...candidates].sort((a, b) => (b.rating || 0) - (a.rating || 0))
  // 返回评分最高电影的后缀部分
  return sorted[0].title.slice(q.length)
})

/**
 * 监听关键词和补全后缀变化，动态调整补全文本的位置
 * 通过measureRef测量输入文本宽度，将补全文本定位在输入文本后面
 */
watch([keyword, completionSuffix], () => {
  nextTick(() => {
    if (measureRef.value && completionRef.value) {
      completionRef.value.style.left = measureRef.value.offsetWidth + 'px'
    }
  })
})

// 缓存所有热门电影数据，避免重复请求
const allPopularMovies = ref([])

/**
 * 加载热门电影数据
 * 首次加载时从API获取数据并缓存，后续直接从缓存中随机打乱取前8条
 */
async function loadPopular() {
  // 首次加载时从API获取数据
  if (!allPopularMovies.value.length) {
    try {
      const { data } = await movieApi.home()
      allPopularMovies.value = data.popular || []
    } catch {
      allPopularMovies.value = []
    }
  }
  // 随机打乱顺序，取前8条展示
  const shuffled = [...allPopularMovies.value].sort(() => Math.random() - 0.5)
  popularMovies.value = shuffled.slice(0, 8)
}

/**
 * 监听搜索框打开/关闭状态
 * 打开时加载热门电影并自动聚焦输入框，关闭时清空关键词和搜索建议
 */
watch(
  () => props.open,
  async (visible) => {
    if (!visible) {
      keyword.value = ''
      suggestions.value = []
      return
    }
    await loadPopular()
    await nextTick()
    inputRef.value?.focus()
  },
)

/**
 * 监听关键词变化，防抖触发搜索
 * 清空关键词时清空搜索建议，输入关键词后250ms防抖触发API搜索
 */
watch(keyword, (val) => {
  clearTimeout(timer)
  const q = val.trim()
  if (!q) {
    suggestions.value = []
    return
  }
  // 250ms防抖，避免频繁请求
  timer = setTimeout(async () => {
    try {
      const { data } = await movieApi.search(q)
      suggestions.value = data.items || []
    } catch {
      suggestions.value = []
    }
  }, 250)
})

/**
 * 关闭搜索框
 * 触发close事件通知父组件
 */
function close() {
  emit('close')
}

/**
 * 提交搜索
 * 如果传入了term参数则使用term，否则使用当前keyword
 * 关闭搜索框后跳转到电影库页面并携带搜索参数
 */
function submitSearch(term) {
  const q = (term ?? keyword.value).trim()
  if (!q) return
  close()
  router.push({ name: 'movies', query: { q } })
}

/**
 * 选择电影
 * 关闭搜索框后跳转到电影详情页面
 */
function pickMovie(item) {
  close()
  router.push({ name: 'movie-detail', params: { id: item.movie_id } })
}

/**
 * 键盘事件处理
 * ESC键关闭搜索框，Tab键补全搜索建议后缀
 */
function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
  } else if (event.key === 'Tab' && completionSuffix.value) {
    event.preventDefault()
    keyword.value += completionSuffix.value
  }
}
</script>

<template>
  <!-- 搜索弹窗容器，open控制显示，监听键盘快捷键 -->
  <div v-if="open" class="header-search" @keydown="onKeydown">
    <div class="header-search__inner">
      <!-- 搜索表单，阻止默认提交，触发自定义搜索方法 -->
      <form class="header-search__form" @submit.prevent="submitSearch()">
        <!-- 左侧放大镜图标 -->
        <span class="header-search__form-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
          </svg>
        </span>
        <!-- 输入框外层容器，用于自动补全文字布局 -->
        <div class="header-search__input-wrapper">
          <!-- 隐藏测量元素，计算输入文字宽度 -->
          <span ref="measureRef" class="header-search__input-measure">{{ keyword }}</span>
          <!-- 主搜索输入框，双向绑定关键词 -->
          <input
            ref="inputRef"
            v-model="keyword"
            class="header-search__input"
            type="search"
            placeholder="搜索电影、导演、演员……"
            autocomplete="off"
          />
          <!-- 智能补全后缀文字 -->
          <span ref="completionRef" v-if="completionSuffix" class="header-search__completion">
            {{ completionSuffix }}
          </span>
        </div>
      </form>

      <!-- 输入关键词时展示搜索联想列表 -->
      <div v-if="keyword.trim() && suggestions.length" class="header-search__section">
        <p class="header-search__section-title">搜索结果</p>
        <!-- 循环渲染联想电影条目 -->
        <button
          v-for="item in suggestions"
          :key="item.movie_id"
          type="button"
          class="header-search__item"
          @click="pickMovie(item)"
        >
          <span class="header-search__item-icon" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
            </svg>
          </span>
          <span class="header-search__item-text">{{ item.title }}</span>
          <!-- 展示电影上映年份 -->
          <span v-if="item.release_year" class="header-search__item-meta">{{ item.release_year }}</span>
        </button>
      </div>

      <!-- 无输入时展示热门电影区域 -->
      <div v-else-if="popularMovies.length" class="header-search__section">
        <!-- 热门区标题+刷新按钮 -->
        <div class="header-search__section-header">
          <p class="header-search__section-title">
            <span class="header-search__trend-icon" aria-hidden="true">↗</span>
            热门电影
          </p>
          <!-- 换一批热门电影按钮 -->
          <button
            type="button"
            class="header-search__shuffle"
            @click="loadPopular"
            title="换一换"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
        <!-- 循环渲染热门电影，点击直接搜索该片名 -->
        <button
          v-for="item in popularMovies"
          :key="item.movie_id"
          type="button"
          class="header-search__item"
          @click="submitSearch(item.title)"
        >
          <span class="header-search__item-icon" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
            </svg>
          </span>
          <span class="header-search__item-text">{{ item.title }}</span>
          <span v-if="item.release_year" class="header-search__item-meta">{{ item.release_year }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

