<script setup>
// 引入Vue3组合式API核心工具函数
import { ref, computed, onMounted } from 'vue'
// 引入路由实例，实现页面跳转
import { useRouter } from 'vue-router'
// 导入电影相关接口请求方法
import { movieApi } from '../api'

// 路由实例对象
const router = useRouter()

/**
 * 奖项类型配置数组
 * id：接口请求使用的唯一标识
 * name：页面展示的中文奖项名称
 */
const AWARD_TYPES = [
  { id: 'golden-globe', name: '金球奖' },
  { id: 'golden-lion', name: '金狮奖' },
  { id: 'golden-bear', name: '金熊奖' },
  { id: 'oscars', name: '奥斯卡金像奖' },
  { id: 'golden-palm', name: '金棕榈奖' },
]

// 生成年份数组，从2015开始连续12个年份，用于年份筛选按钮渲染
const YEARS = Array.from({ length: 12 }, (_, i) => 2015 + i)

// 当前选中的奖项，默认选中奥斯卡
const currentAward = ref('oscars')
// 当前筛选年份，null代表不限制年份，展示全部年份数据
const currentYear = ref(null)
// 存储接口返回的获奖电影列表
const movies = ref([])
// 页面加载状态标识，true为正在请求数据，展示loading动画
const loading = ref(false)

/**
 * 各奖项匹配关键词映射表
 * key：奖项唯一id
 * value：中英文关键词数组，用于匹配电影awards字段内对应的获奖信息
 */
const awardKeywords = {
  'oscars': ['奥斯卡', 'Oscar'],
  'golden-globe': ['金球奖', 'Golden Globe'],
  'golden-lion': ['金狮奖', 'Golden Lion'],
  'golden-bear': ['金熊奖', 'Golden Bear'],
  'golden-palm': ['金棕榈奖', '金棕榈', 'Golden Palm'],
}

/**
 * 计算属性：根据选中奖项id，获取对应中文名称，渲染页面顶部标题
 */
const currentAwardName = computed(() => {
  return AWARD_TYPES.find(a => a.id === currentAward.value)?.name || ''
})

/**
 * 解析单部电影的获奖文本，提取当前选中奖项的获奖/提名信息
 * @param {Object} movie 单条电影原始接口数据对象
 * @returns {Array<Object>} 格式化后的奖项标签数组，包含获奖类型、名称、年份
 */
function extractAwardDetails(movie) {
  // 电影无获奖字段，直接返回空数组
  if (!movie.awards) return []
  // 按竖线分割多条获奖记录
  const parts = movie.awards.split('|')
  // 获取当前选中奖项对应的匹配关键词
  const keywords = awardKeywords[currentAward.value] || []
  // 存储解析完成的奖项信息
  const details = []
  
  // 循环遍历每一条获奖记录文本
  for (const part of parts) {
    const trimmed = part.trim()
    // 空文本跳过处理
    if (!trimmed) continue
    
    // 判断本条获奖记录是否匹配当前选中奖项
    const isRelevant = keywords.some(k => trimmed.includes(k))
    if (!isRelevant) continue
    
    // 判断该记录为提名还是获奖，包含(提名)则为提名
    const isNominated = trimmed.includes('(提名)')
    // 去除文本中的提名标记
    const cleaned = trimmed.replace('(提名)', '').trim()
    
    // 标签展示文本初始化
    let badgeText = ''
    
    // 根据奖项关键词截取完整奖项名称文本
    for (const kw of keywords) {
      if (cleaned.includes(kw)) {
        const before = cleaned.substring(0, cleaned.indexOf(kw))
        const after = cleaned.substring(cleaned.indexOf(kw) + kw.length)
        const awardPart = before.split('；').pop()?.trim() + kw + after.split('；')[0]?.trim()
        badgeText = awardPart || kw
        break
      }
    }
    
    // 若上一步未提取到标签文本，执行多规则兜底提取
    if (!badgeText) {
      // 匹配“最佳XX”奖项
      const bestMatch = cleaned.match(/最佳(.+?)(?:；|\(|$)/)
      // 匹配五大奖项全称
      const awardMatch = cleaned.match(/(金棕榈奖|金狮奖|金熊奖|奥斯卡金像奖|金球奖)/)
      // 匹配主竞赛单元奖项
      const unitMatch = cleaned.match(/主竞赛单元(.+?)(?:；|\(|$)/)
      
      if (bestMatch) {
        badgeText = '最佳' + bestMatch[1].trim()
      } else if (awardMatch) {
        badgeText = awardMatch[1].trim()
      } else if (unitMatch) {
        badgeText = unitMatch[1].trim()
      } else {
        // 兜底取第一条分号前内容
        badgeText = cleaned.split('；')[0]?.trim()
      }
    }
    
    // 标签文本超长截断，最大25字符，末尾补充省略号
    if (badgeText.length > 25) {
      badgeText = badgeText.slice(0, 25) + '...'
    }
    
    // 组装单条奖项对象，存入结果数组
    details.push({
      type: isNominated ? 'nominated' : 'won', // nominated=提名 won=获奖
      name: badgeText,
      year: '',
    })
  }
  
  return details
}

/**
 * 请求接口加载对应奖项、年份的电影列表数据
 */
async function loadMovies() {
  // 开启加载状态
  loading.value = true
  try {
    // 基础请求参数：奖项类型、单页数据条数
    const params = {
      award_type: currentAward.value,
      page_size: 50,
    }
    // 选中指定年份时，追加年份筛选参数
    if (currentYear.value) {
      params.year = currentYear.value
    }
    // 调用接口获取获奖电影数据
    const { data } = await movieApi.awards(params)
    // 遍历原始数据，为每条电影追加解析完成的奖项详情字段
    movies.value = data.items.map(movie => ({
      ...movie,
      awardDetails: extractAwardDetails(movie),
    }))
  } catch (error) {
    // 请求异常打印错误日志，清空电影列表
    console.error('Failed to load movies:', error)
    movies.value = []
  } finally {
    // 请求结束，无论成功失败均关闭加载状态
    loading.value = false
  }
}

/**
 * 切换选中的奖项类型
 * @param {String} awardId 目标奖项唯一标识
 */
function selectAward(awardId) {
  // 更新当前选中奖项
  currentAward.value = awardId
  // 切换奖项后重置年份筛选，默认展示全部年份
  currentYear.value = null
  // 重新请求对应奖项电影数据
  loadMovies()
}

/**
 * 切换筛选年份，重复点击同一年份则取消年份筛选
 * @param {Number|null} year 选中年份，null为全部年份
 */
function selectYear(year) {
  // 当前已选中该年份则置空，否则赋值目标年份
  currentYear.value = currentYear.value === year ? null : year
  // 重新请求对应年份数据
  loadMovies()
}

/**
 * 跳转电影详情页面
 * @param {Number} movieId 目标电影唯一id
 */
function goMovieDetail(movieId) {
  // 路由跳转，传递电影id参数
  router.push({ name: 'movie-detail', params: { id: movieId } })
}

/**
 * 页面挂载完成生命周期钩子，页面初始化时加载一次数据
 */
onMounted(() => {
  loadMovies()
})
</script>

<template>
  <!-- 获奖电影页面根容器 -->
  <div class="awards-page">
    <!-- 页面头部标题区域 -->
    <div class="awards-page__header">
      <!-- 动态展示当前选中奖项名称 -->
      <h1 class="awards-page__title">{{ currentAwardName }}</h1>
    </div>

    <!-- 奖项切换标签容器 -->
    <div class="awards-page__tabs awards-page__tabs--award">
      <!-- 循环渲染所有奖项切换按钮 -->
      <button
        v-for="award in AWARD_TYPES"
        :key="award.id"
        type="button"
        class="awards-page__tab"
        :class="{ 'awards-page__tab--active': currentAward === award.id }"
        @click="selectAward(award.id)"
      >
        {{ award.name }}
      </button>
    </div>

    <!-- 年份筛选标签容器 -->
    <div class="awards-page__tabs awards-page__tabs--year">
      <!-- 全部年份筛选按钮 -->
      <button
        type="button"
        class="awards-page__tab awards-page__tab--year-item"
        :class="{ 'awards-page__tab--active': !currentYear }"
        @click="selectYear(null)"
      >
        全部年份
      </button>
      <!-- 循环渲染年份选择按钮 -->
      <button
        v-for="year in YEARS"
        :key="year"
        type="button"
        class="awards-page__tab awards-page__tab--year-item"
        :class="{ 'awards-page__tab--active': currentYear === year }"
        @click="selectYear(year)"
      >
        {{ year }}
      </button>
    </div>

    <!-- 列表主体内容区域 -->
    <div class="awards-page__content">
      <!-- 数据加载中状态展示 -->
      <div v-if="loading" class="awards-page__loading">
        <!-- 加载旋转动画 -->
        <div class="spinner" />
        <p>加载中...</p>
      </div>

      <!-- 无电影数据空状态提示 -->
      <div v-else-if="movies.length === 0" class="awards-page__empty">
        <p>暂无相关获奖电影数据</p>
      </div>

      <!-- 电影卡片列表容器 -->
      <div v-else class="awards-card-list">
        <!-- 单部电影卡片循环渲染 -->
        <article
          v-for="movie in movies"
          :key="movie.movie_id"
          class="awards-card"
          @click="goMovieDetail(movie.movie_id)"
        >
          <!-- 电影海报外层容器 -->
          <div class="awards-card__poster-wrapper">
            <!-- 电影海报图片，懒加载优化性能 -->
            <img
              :src="movie.poster_url"
              :alt="movie.title"
              class="awards-card__poster"
              loading="lazy"
            />
          </div>
          <!-- 电影文字信息区域 -->
          <div class="awards-card__info">
            <!-- 标题与奖项标签行 -->
            <div class="awards-card__header">
              <h3 class="awards-card__title">{{ movie.title }}</h3>
              <!-- 奖项标签容器，最多展示前3条奖项 -->
              <div v-if="movie.awardDetails.length" class="awards-card__badges">
                <span
                  v-for="(detail, idx) in movie.awardDetails.slice(0, 3)"
                  :key="idx"
                  class="awards-card__badge"
                  :class="{ 'awards-card__badge--won': detail.type === 'won' }"
                >
                  {{ detail.name }}
                </span>
              </div>
            </div>
            <!-- 导演信息行，存在导演数据才渲染 -->
            <div v-if="movie.directors" class="awards-card__director">
              <span class="awards-card__label">导演:</span>
              <span>{{ movie.directors }}</span>
            </div>
            <!-- 上映年份+评分行 -->
            <div class="awards-card__year-rating">
              <span>{{ movie.release_year }}年</span>
              <span class="awards-card__rating">评分 {{ movie.rating }}</span>
            </div>
            <!-- 电影简介区域，截取前120字符防止文本过长 -->
            <div class="awards-card__summary">
              <span class="awards-card__label">电影简介:</span>
              <p>{{ movie.summary?.slice(0, 120) }}...</p>
            </div>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面根容器全局基础样式，渐变背景，最小占满视口高度 */
.awards-page {
  min-height: 100vh;
  background: linear-gradient(180deg, var(--fywz-bg) 0%, var(--fywz-surface) 100%);
  padding-bottom: 2rem;
}

/* 页面头部标题容器，居中内边距 */
.awards-page__header {
  text-align: center;
  padding: 2rem 1rem 1rem;
}

/* 页面主标题文字样式，大字号、加粗、字间距加宽 */
.awards-page__title {
  font-size: 2.8rem;
  font-weight: 800;
  color: var(--fywz-accent);
  margin: 0;
  letter-spacing: 0.15em;
}

/* 通用标签栏基础样式：横向弹性布局，横向滚动，隐藏滚动条 */
.awards-page__tabs {
  display: flex;
  overflow-x: auto;
  scrollbar-width: none;
  margin-bottom: 1rem;
}

/* webkit浏览器隐藏横向滚动条 */
.awards-page__tabs::-webkit-scrollbar {
  display: none;
}

/* 奖项标签栏：居中对齐，左右预留内边距 */
.awards-page__tabs--award {
  justify-content: center;
  gap: 1rem;
  padding: 0 1rem;
}

/* 年份标签栏：左对齐，限制最大宽度并整体居中 */
.awards-page__tabs--year {
  justify-content: flex-start;
  gap: 0.5rem;
  padding: 0;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

/* 标签按钮通用基础样式，圆角胶囊按钮，过渡动画 */
.awards-page__tab {
  flex-shrink: 0;
  padding: 0.7rem 1.5rem;
  border-radius: 999px;
  border: 2px solid var(--fywz-accent);
  background: transparent;
  color: var(--fywz-accent);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
}

/* 标签悬浮hover背景淡色高亮 */
.awards-page__tab:hover {
  background: rgba(1, 180, 228, 0.1);
}

/* 当前选中激活态标签：填充主色，文字反白，添加阴影 */
.awards-page__tab--active {
  background: var(--fywz-accent);
  color: var(--fywz-accent-text);
  box-shadow: 0 4px 12px rgba(1, 180, 228, 0.4);
}

/* 年份筛选标签单独缩小尺寸、细边框 */
.awards-page__tab--year-item {
  padding: 0.45rem 1rem;
  font-size: 0.8rem;
  border-width: 1px;
}

/* 内容容器，限制页面最大宽度，左右自适应居中 */
.awards-page__content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* loading加载容器，垂直水平居中布局 */
.awards-page__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--fywz-text-muted);
}

/* 加载旋转圆圈样式 */
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(1, 180, 228, 0.2);
  border-top-color: var(--fywz-accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* 加载旋转动画关键帧，360度循环旋转 */
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 空数据提示区域，居中布局 */
.awards-page__empty {
  text-align: center;
  padding: 4rem;
  color: var(--fywz-text-muted);
}

/* 电影卡片网格布局，桌面端双列等宽 */
.awards-card-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

/* 单张电影卡片：横向弹性布局，圆角阴影，hover上浮动画 */
.awards-card {
  display: flex;
  gap: 1rem;
  border-radius: 16px;
  background: var(--fywz-surface);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s;
}

/* 卡片悬浮上浮、加深阴影交互效果 */
.awards-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}

/* 海报容器固定宽度，禁止自适应压缩 */
.awards-card__poster-wrapper {
  flex-shrink: 0;
  width: 140px;
  margin-left: 0.5rem;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

/* 海报图片固定高度，cover裁切保证不变形，圆角 */
.awards-card__poster {
  width: 100%;
  height: 190px;
  object-fit: cover;
  border-radius: 10px;
}

/* 文字信息区域自适应填充剩余宽度，纵向弹性布局 */
.awards-card__info {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

/* 标题+奖项标签行，左右分布 */
.awards-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

/* 电影标题加粗放大 */
.awards-card__title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--fywz-text);
  margin: 0;
  flex: 1;
}

/* 奖项标签容器，自动换行，标签间距 */
.awards-card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 奖项标签默认样式，浅底色灰色文字 */
.awards-card__badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--fywz-surface-2);
  color: var(--fywz-text-muted);
}

/* 获奖标签特殊渐变底色，白色文字区分提名 */
.awards-card__badge--won {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.8), rgba(217, 119, 6, 0.8));
  color: #ffffff;
}

/* 导演信息文本，浅灰小字 */
.awards-card__director {
  font-size: 0.85rem;
  color: var(--fywz-text-muted);
  margin-bottom: 0.5rem;
}

/* 页面内灰色前缀标签通用样式 */
.awards-card__label {
  color: var(--fywz-text-muted);
  margin-right: 0.25rem;
}

/* 年份、评分横向并排布局 */
.awards-card__year-rating {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: var(--fywz-text-muted);
  margin-bottom: 0.75rem;
}

/* 评分文字黄色高亮加粗 */
.awards-card__rating {
  color: #f59e0b;
  font-weight: 600;
}

/* 简介区域自适应填充卡片剩余高度，小字浅灰 */
.awards-card__summary {
  flex: 1;
  font-size: 0.85rem;
  color: var(--fywz-text-muted);
  line-height: 1.5;
}

/* 简介段落清除默认外边距 */
.awards-card__summary p {
  margin: 0;
}

/* 平板适配：屏幕宽度小于1024px，卡片网格改为单列 */
@media (max-width: 1024px) {
  .awards-card-list {
    grid-template-columns: 1fr;
  }
}

/* 移动端适配：屏幕宽度小于640px，卡片改为上下垂直布局 */
@media (max-width: 640px) {
  .awards-card {
    flex-direction: column;
  }
  
  .awards-card__poster-wrapper {
    width: 100%;
  }
  
  .awards-card__poster {
    height: 200px;
  }
  
  .awards-card__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
