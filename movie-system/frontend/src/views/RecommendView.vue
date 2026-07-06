<script setup>
/**
 * 智能推荐页（/recommend）
 * 状态机：未登录 → 评分不足 → 待刷新 → 已有个性化推荐
 * 刷新时 POST /api/recommend/refresh，触发 VM Spark 增量计算
 */
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { recommendApi } from '../api'
import { useUserStore } from '../stores/user'
import MovieCard from '../components/MovieCard.vue'

const RATING_GOAL = 3

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
// 后端返回的 strategy：cold_start | spark_pending | spark_hybrid
const strategy = ref('')
const strategyLabel = ref('')
const ratingCount = ref(0)

const hybridItems = ref([])
const alsItems = ref([])
const graphxItems = ref([])
const contentItems = ref([])
const popularItems = ref([])

const STRATEGY_MODE = {
  spark_hybrid: '个性化推荐',
  spark_pending: '待刷新推荐',
  cold_start: '热门推荐',
}

const refreshing = ref(false)
const isSparkPending = ref(false)

const statusModeText = computed(() => {
  if (strategy.value && STRATEGY_MODE[strategy.value]) {
    return STRATEGY_MODE[strategy.value]
  }
  return strategyLabel.value || '个性化推荐'
})

const statusRatingText = computed(() => {
  if (!userStore.isLoggedIn) return '未登录'
  if (ratingCount.value <= 0) return '尚未评分'
  return `已评分 ${ratingCount.value} 部`
})

const ratingProgress = computed(() => Math.min(ratingCount.value, RATING_GOAL))
const ratingProgressPercent = computed(() => Math.round((ratingProgress.value / RATING_GOAL) * 100))

const showGuestGuide = computed(() => !userStore.isLoggedIn && !loading.value)

/** 已登录但评分 < 3：显示进度条引导去电影库评分 */
const showRatingGuide = computed(
  () => userStore.isLoggedIn && ratingCount.value < RATING_GOAL && !loading.value,
)

/** 评满 3 部但尚未跑 Spark：提示点「刷新推荐」 */
const showSparkPendingBanner = computed(
  () =>
    userStore.isLoggedIn &&
    ratingCount.value >= RATING_GOAL &&
    isSparkPending.value &&
    !refreshing.value &&
    !loading.value,
)

const ratingGuideMessage = computed(() => {
  if (ratingCount.value <= 0) {
    return '给 3 部电影打分后，系统就能更懂你的口味'
  }
  const remain = RATING_GOAL - ratingCount.value
  return `已完成 ${ratingCount.value} 部，再评 ${remain} 部即可解锁专属推荐`
})

function goRateMovies() {
  router.push({ name: 'movies' })
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: '/recommend' } })
}

/** 根据后端各分区数据 + 用户状态，决定展示哪些推荐区块 */
const sections = computed(() => {
  const rows = [
    {
      key: 'hybrid',
      title: '为你综合推荐',
      subtitle: '融合协同过滤、社交图谱与内容相似度',
      movies: hybridItems.value,
    },
    {
      key: 'als',
      title: '猜你喜欢',
      subtitle: '根据你的评分偏好智能匹配',
      movies: alsItems.value,
    },
    {
      key: 'graphx',
      title: '相似用户也在看',
      subtitle: '口味相近的用户还在看这些',
      movies: graphxItems.value,
    },
    {
      key: 'content',
      title: '同类推荐',
      subtitle: '风格、类型与你喜欢的电影相近',
      movies: contentItems.value,
    },
    {
      key: 'popular',
      title: '热门推荐',
      subtitle: '高口碑、高人气的精选影片',
      movies: popularItems.value,
    },
  ]
  let visible = rows.filter((row) => row.movies.length > 0)
  if (ratingCount.value < RATING_GOAL) {
    visible = visible.filter((row) => row.key === 'popular')
  } else if (isSparkPending.value) {
    visible = visible.filter((row) => row.key === 'popular')
  }
  return visible
})

const hasAnyItems = computed(() => sections.value.length > 0)

function applyPayload(data) {
  hybridItems.value = data.hybrid_items || []
  alsItems.value = data.als_items || []
  graphxItems.value = data.graphx_items || []
  contentItems.value = data.content_items || []
  popularItems.value = data.popular_items || []
  strategy.value = data.strategy || ''
  strategyLabel.value = data.strategy_label || '个性化推荐'
  ratingCount.value = data.rating_count ?? 0
  isSparkPending.value = data.strategy === 'spark_pending'
}

async function load() {
  loading.value = true
  try {
    if (!userStore.isLoggedIn) {
      // 访客：GET /api/recommend/guest → 仅热门电影
      const { data } = await recommendApi.guest()
      applyPayload(data)
      return
    }
    // 已登录：GET /api/recommend/personal
    const { data } = await recommendApi.personal()
    applyPayload(data)
  } finally {
    loading.value = false
  }
}

async function refresh() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  refreshing.value = true
  try {
    // POST /api/recommend/refresh → 后端同步评分、跑 Spark、拉回 JSON
    const { data } = await recommendApi.refresh()
    applyPayload(data)
    ElMessage.success('推荐已更新')
  } catch (err) {
    const msg = err.response?.data?.error || err.message || '刷新失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    refreshing.value = false
  }
}

onMounted(load)
onActivated(load)
</script>

<template>
  <div class="recommend-page mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
    <section class="recommend-hero mb-8">
      <div class="recommend-hero__toolbar">
        <div class="recommend-hero__stat">
          <span class="recommend-hero__stat-label">当前模式</span>
          <span class="recommend-hero__stat-value">{{ statusModeText }}</span>
        </div>
        <div class="recommend-hero__stat">
          <span class="recommend-hero__stat-label">我的评分</span>
          <span class="recommend-hero__stat-value">{{ statusRatingText }}</span>
        </div>
        <button
          v-if="userStore.isLoggedIn"
          type="button"
          class="recommend-refresh-btn"
          :disabled="loading || refreshing"
          @click="refresh"
        >
          {{ refreshing ? '生成中…' : '刷新推荐' }}
        </button>
      </div>
    </section>

    <!-- 未登录引导 -->
    <div v-if="showGuestGuide" class="onboard-banner onboard-banner--guest mb-8">
      <div class="onboard-banner__badge">1</div>
      <div class="onboard-banner__body">
        <h3 class="onboard-banner__title">开启您的专属推荐~</h3>
        <p class="onboard-banner__text">
          登录并为3部电影打分，生成您的个性化片单~
        </p>
        <div class="onboard-banner__actions">
          <button type="button" class="onboard-btn onboard-btn--primary" @click="goLogin">
            登录开始
          </button>
          <button type="button" class="onboard-btn onboard-btn--ghost" @click="goRateMovies">
            先逛逛电影库
          </button>
        </div>
      </div>
    </div>

    <!-- 新用户评分引导 -->
    <div v-else-if="showRatingGuide" class="onboard-banner mb-8">
      <div class="onboard-banner__badge">2</div>
      <div class="onboard-banner__body">
        <h3 class="onboard-banner__title">还差几步，推荐会更懂你</h3>
        <p class="onboard-banner__text">{{ ratingGuideMessage }}</p>
        <div class="onboard-banner__progress">
          <div class="onboard-banner__progress-track">
            <div
              class="onboard-banner__progress-bar"
              :style="{ width: `${ratingProgressPercent}%` }"
            />
          </div>
          <span class="onboard-banner__progress-label">{{ ratingProgress }} / {{ RATING_GOAL }}</span>
        </div>
        <div class="onboard-banner__actions">
          <button type="button" class="onboard-btn onboard-btn--primary" @click="goRateMovies">
            去评分
          </button>
        </div>
      </div>
    </div>

    <!-- 待刷新 -->
    <div v-else-if="showSparkPendingBanner" class="onboard-banner mb-8">
      <div class="onboard-banner__badge">3</div>
      <div class="onboard-banner__body">
        <h3 class="onboard-banner__title">评分已够，一键生成您的专属推荐~</h3>
        <p class="onboard-banner__text">
          你已评满 {{ RATING_GOAL }} 部，点击刷新即可获取最新推荐哦~
        </p>
        <div class="onboard-banner__actions">
          <button type="button" class="onboard-btn onboard-btn--primary" :disabled="refreshing" @click="refresh">
            {{ refreshing ? '生成中…' : '立即刷新推荐' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="refreshing" class="recommend-loading">
      <div class="recommend-loading__spinner" />
      <p>正在为你生成推荐，大约需要 15～60 秒</p>
    </div>
    <div v-else-if="loading" class="recommend-loading">
      <p>加载推荐中…</p>
    </div>
    <div v-else-if="!hasAnyItems" class="recommend-empty">
      <p>暂无推荐内容</p>
      <p class="recommend-empty__hint">评满 3 部电影后，点击「刷新推荐」即可生成专属片单</p>
    </div>
    <template v-else>
      <section v-for="section in sections" :key="section.key" class="recommend-section">
        <div class="recommend-section__head">
          <h2 class="recommend-section__title">{{ section.title }}</h2>
          <p v-if="section.subtitle" class="recommend-section__subtitle">{{ section.subtitle }}</p>
        </div>
        <div class="recommend-section__grid">
          <MovieCard
            v-for="movie in section.movies"
            :key="`${section.key}-${movie.movie_id}`"
            :movie="movie"
            recommend-mode
            class="recommend-card w-full"
          />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.recommend-hero {
  display: flex;
  justify-content: flex-end;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--fywz-border);
}

.recommend-hero__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 1.25rem 1.75rem;
}

.recommend-hero__stat {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  text-align: right;
}

.recommend-hero__stat-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--fywz-text-muted);
}

.recommend-hero__stat-value {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.recommend-refresh-btn {
  border: none;
  border-radius: 999px;
  padding: 0.55rem 1.35rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: #032541;
  background: linear-gradient(135deg, #01b4e4, #0096c7);
  box-shadow: 0 8px 20px rgba(1, 180, 228, 0.28);
  transition: transform 0.2s ease, filter 0.2s ease;
}

.recommend-refresh-btn:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: translateY(-1px);
}

.recommend-refresh-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.recommend-section {
  margin-bottom: 2.5rem;
}

.recommend-section__head {
  margin-bottom: 1rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--fywz-border);
  position: relative;
}

.recommend-section__head::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 3rem;
  height: 2px;
  border-radius: 999px;
  background: #01b4e4;
}

.recommend-section__title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--fywz-text);
}

.recommend-section__subtitle {
  margin-top: 0.3rem;
  font-size: 0.8125rem;
  color: var(--fywz-text-muted);
}

.recommend-section__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem 1rem;
}

.recommend-loading,
.recommend-empty {
  padding: 4rem 1rem;
  text-align: center;
  color: var(--fywz-text-muted);
}

.recommend-loading__spinner {
  width: 2rem;
  height: 2rem;
  margin: 0 auto 1rem;
  border-radius: 999px;
  border: 3px solid rgba(1, 180, 228, 0.2);
  border-top-color: #01b4e4;
  animation: recommend-spin 0.8s linear infinite;
}

.recommend-empty__hint {
  margin-top: 0.35rem;
  font-size: 0.8125rem;
}

@keyframes recommend-spin {
  to {
    transform: rotate(360deg);
  }
}

:deep(.recommend-card) {
  width: 100%;
  max-width: none;
}

.onboard-banner {
  display: flex;
  gap: 1rem;
  padding: 1.25rem 1.35rem;
  border-radius: 1rem;
  border: 1px solid rgba(1, 180, 228, 0.28);
  background: linear-gradient(135deg, rgba(1, 180, 228, 0.1) 0%, rgba(37, 99, 235, 0.06) 100%);
  box-shadow: 0 10px 28px var(--fywz-card-shadow);
}

.onboard-banner--guest {
  border-color: rgba(168, 85, 247, 0.28);
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(1, 180, 228, 0.06) 100%);
}

.onboard-banner__badge {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  background: rgba(1, 180, 228, 0.15);
  color: #01b4e4;
  font-size: 0.9375rem;
  font-weight: 800;
}

.onboard-banner__body {
  flex: 1;
  min-width: 0;
}

.onboard-banner__title {
  font-size: 1.05rem;
  font-weight: 800;
  margin: 0 0 0.35rem;
  color: var(--fywz-text);
}

.onboard-banner__text {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--fywz-text-muted);
}

.onboard-banner__progress {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.85rem;
}

.onboard-banner__progress-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: rgba(1, 180, 228, 0.12);
  overflow: hidden;
}

.onboard-banner__progress-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #01b4e4, #2563eb);
  transition: width 0.35s ease;
}

.onboard-banner__progress-label {
  flex-shrink: 0;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #01b4e4;
}

.onboard-banner__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1rem;
}

.onboard-btn {
  border-radius: 999px;
  padding: 0.5rem 1.15rem;
  font-size: 0.8125rem;
  font-weight: 700;
  transition: filter 0.2s ease, background 0.2s ease;
}

.onboard-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.onboard-btn--primary {
  border: none;
  background: #01b4e4;
  color: #032541;
}

.onboard-btn--primary:hover:not(:disabled) {
  filter: brightness(1.06);
}

.onboard-btn--ghost {
  border: 1px solid var(--fywz-border);
  background: transparent;
  color: var(--fywz-text);
}

.onboard-btn--ghost:hover:not(:disabled) {
  background: var(--fywz-tab-hover);
}

@media (min-width: 640px) {
  .recommend-section__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .recommend-section__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .recommend-section__grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .recommend-hero__toolbar {
    width: 100%;
    justify-content: space-between;
  }

  .onboard-banner {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>
