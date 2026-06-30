<script setup>
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
const strategy = ref('')
const strategyLabel = ref('')
const ratingCount = ref(0)

const hybridItems = ref([])
const alsItems = ref([])
const graphxItems = ref([])
const contentItems = ref([])
const popularItems = ref([])

const STRATEGY_MODE = {
  spark_hybrid: 'Spark 混合推荐',
  spark_pending: '待 Spark 刷新',
  online_hybrid: '在线混合推荐',
  hybrid: '在线混合推荐',
  cold_start: '冷启动 · 仅热门推荐',
}

const refreshing = ref(false)
const isSparkMode = ref(false)
const isSparkPending = ref(false)
const personalizedReady = ref(false)

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

const statusComputeText = computed(() => {
  if (refreshing.value) return 'VM Spark 批处理计算中…'
  if (isSparkMode.value) return 'Spark 批处理（Ubuntu VM）'
  if (strategy.value === 'cold_start') return '热门兜底（与首页一致）'
  if (isSparkPending.value) return '等待刷新触发 Spark'
  return '—'
})

const ratingProgress = computed(() => Math.min(ratingCount.value, RATING_GOAL))
const ratingProgressPercent = computed(() => Math.round((ratingProgress.value / RATING_GOAL) * 100))

const isColdStartStrategy = computed(() => strategy.value === 'cold_start')

const showGuestGuide = computed(() => !userStore.isLoggedIn && !loading.value)

const showRatingGuide = computed(
  () => userStore.isLoggedIn && ratingCount.value < RATING_GOAL && !loading.value,
)

const showSparkPendingBanner = computed(
  () =>
    userStore.isLoggedIn &&
    ratingCount.value >= RATING_GOAL &&
    isSparkPending.value &&
    !refreshing.value &&
    !loading.value,
)

const showOnlineBanner = computed(
  () =>
    userStore.isLoggedIn &&
    ratingCount.value >= RATING_GOAL &&
    isSparkMode.value &&
    personalizedReady.value &&
    !refreshing.value &&
    !loading.value,
)

const ratingGuideMessage = computed(() => {
  if (ratingCount.value <= 0) {
    return '你还没有评分记录，先给 3 部电影打分，系统将为你生成个性化推荐'
  }
  const remain = RATING_GOAL - ratingCount.value
  return `已评分 ${ratingCount.value} 部，再评 ${remain} 部即可解锁 Spark 个性化推荐`
})

function goRateMovies() {
  router.push({ name: 'movies' })
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: '/recommend' } })
}

const sections = computed(() => {
  const spark = isSparkMode.value
  const rows = [
    {
      key: 'hybrid',
      title: '为你综合推荐',
      subtitle: spark
        ? 'Spark ALS 0.7 + GraphX 0.2 + TF-IDF 0.1'
        : '在线 NMF 矩阵分解 0.7 + 在线协同 0.2 + 类型相似 0.1',
      movies: hybridItems.value,
    },
    {
      key: 'als',
      title: '协同过滤 · 猜你喜欢',
      subtitle: spark ? 'Spark MLlib ALS（含最新同步评分）' : '在线 NMF 矩阵分解（含你的最新评分）',
      movies: alsItems.value,
    },
    {
      key: 'graphx',
      title: '相似用户也在看',
      subtitle: spark ? 'Spark GraphX 图协同推荐' : '在线用户协同 / 图相似扩展',
      movies: graphxItems.value,
    },
    {
      key: 'content',
      title: '喜欢这类 · 同类推荐',
      subtitle: spark ? 'Spark TF-IDF 内容相似' : 'MySQL 类型/导演相似度',
      movies: contentItems.value,
    },
    {
      key: 'popular',
      title: '热门推荐',
      subtitle: '与首页「热门电影」相同 · 按评价人数排序',
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
  isSparkMode.value = data.source === 'spark' && data.strategy === 'spark_hybrid'
  isSparkPending.value = data.strategy === 'spark_pending'
  personalizedReady.value = !!data.personalized_ready
}

async function load() {
  loading.value = true
  try {
    if (!userStore.isLoggedIn) {
      const { data } = await recommendApi.guest()
      applyPayload(data)
      return
    }
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
    const { data } = await recommendApi.refresh()
    applyPayload(data)
    ElMessage.success('Spark 批处理完成，推荐已更新')
  } catch (err) {
    const msg = err.response?.data?.error || err.message || 'Spark 刷新失败'
    ElMessage.error(msg)
  } finally {
    refreshing.value = false
  }
}

onMounted(load)
onActivated(load)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
    <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold">智能推荐</h1>
        <p class="mt-2 text-sm text-muted">
          评满 3 部后由 Ubuntu VM 上的 Spark 批处理生成推荐；修改评分后请点击「刷新推荐」重算
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <button
          v-if="userStore.isLoggedIn"
          class="rounded-md bg-[#01B4E4] px-5 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
          :disabled="loading || refreshing"
          @click="refresh"
        >
          {{ refreshing ? 'Spark 计算中…' : '刷新推荐' }}
        </button>
      </div>
    </div>

    <!-- 未登录引导 -->
    <div v-if="showGuestGuide" class="onboard-banner onboard-banner--guest mb-6">
      <div class="onboard-banner__icon">🎬</div>
      <div class="onboard-banner__body">
        <h3 class="onboard-banner__title">开启个性化推荐</h3>
        <p class="onboard-banner__text">
          登录并给 3 部电影打分，然后点击「刷新推荐」在 VM 上运行 Spark 生成个性化结果。
        </p>
        <div class="onboard-banner__actions">
          <button type="button" class="onboard-btn onboard-btn--primary" @click="goLogin">
            去登录
          </button>
          <button type="button" class="onboard-btn onboard-btn--ghost" @click="goRateMovies">
            先浏览电影
          </button>
        </div>
      </div>
    </div>

    <!-- 新用户评分引导 -->
    <div v-else-if="showRatingGuide" class="onboard-banner mb-6">
      <div class="onboard-banner__icon">⭐</div>
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
          <button
            v-if="ratingCount > 0"
            type="button"
            class="onboard-btn onboard-btn--ghost"
            :disabled="loading"
            @click="refresh"
          >
            刷新推荐
          </button>
        </div>
      </div>
    </div>

    <!-- Spark 待刷新 -->
    <div v-else-if="showSparkPendingBanner" class="onboard-banner mb-6">
      <div class="onboard-banner__icon">⚡</div>
      <div class="onboard-banner__body">
        <h3 class="onboard-banner__title">已评满 {{ RATING_GOAL }} 部，请刷新 Spark 推荐</h3>
        <p class="onboard-banner__text">
          推荐由 Ubuntu 虚拟机上的 Spark（ALS / GraphX / TF-IDF）批处理生成。你有新评分后需点击「刷新推荐」才会重算；不刷新则保持上一次结果。
        </p>
        <div class="onboard-banner__actions">
          <button type="button" class="onboard-btn onboard-btn--primary" :disabled="refreshing" @click="refresh">
            {{ refreshing ? 'Spark 计算中…' : '刷新推荐（触发 VM Spark）' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Spark 推荐已就绪 -->
    <div v-else-if="showOnlineBanner" class="onboard-banner onboard-banner--success mb-6">
      <div class="onboard-banner__icon">✨</div>
      <div class="onboard-banner__body">
        <h3 class="onboard-banner__title">Spark 个性化推荐已就绪</h3>
        <p class="onboard-banner__text">
          当前展示的是 VM Spark 批处理结果。修改评分后请点击「刷新推荐」同步数据并重算（约 1～3 分钟）。
        </p>
        <div class="onboard-banner__actions">
          <button type="button" class="onboard-btn onboard-btn--primary" :disabled="refreshing" @click="refresh">
            {{ refreshing ? 'Spark 计算中…' : '刷新推荐' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="!loading && hasAnyItems" class="status-card mb-8">
      <div class="status-card__row">
        <span class="status-card__label">当前模式</span>
        <span class="status-card__value">{{ statusModeText }}</span>
      </div>
      <span class="status-card__dot">·</span>
      <div class="status-card__row">
        <span class="status-card__label">评分记录</span>
        <span class="status-card__value">{{ statusRatingText }}</span>
      </div>
      <span class="status-card__dot">·</span>
      <div class="status-card__row">
        <span class="status-card__label">计算方式</span>
        <span class="status-card__value" :class="{ 'status-card__value--ok': isSparkMode }">
          {{ statusComputeText }}
        </span>
      </div>
      <div class="status-card__tags">
        <span class="algo-tag algo-tag--als">ALS</span>
        <span class="algo-tag algo-tag--graphx">GraphX</span>
        <span class="algo-tag algo-tag--content">Content</span>
      </div>
    </div>

    <div v-if="refreshing" class="py-16 text-center text-muted">
      Spark 批处理计算中，约需 1～3 分钟，请稍候…
    </div>
    <div v-else-if="loading" class="py-16 text-center text-muted">加载推荐中...</div>
    <div v-else-if="!hasAnyItems" class="py-16 text-center text-muted">
      暂无推荐。评满 3 部后请点击「刷新推荐」，在 VM 上运行 Spark 生成结果。
    </div>
    <template v-else>
      <section v-for="section in sections" :key="section.key" class="mb-10">
        <div class="mb-4">
          <h2 class="text-xl font-bold">{{ section.title }}</h2>
          <p v-if="section.subtitle" class="mt-1 text-sm text-muted">{{ section.subtitle }}</p>
        </div>
        <div class="section-surface rounded-xl py-6">
          <div class="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            <MovieCard
              v-for="movie in section.movies"
              :key="`${section.key}-${movie.movie_id}`"
              :movie="movie"
              recommend-mode
              class="recommend-card w-full"
            />
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.status-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  border: 1px solid var(--fywz-border, rgba(255, 255, 255, 0.12));
  background: var(--fywz-surface, rgba(255, 255, 255, 0.04));
}

.status-card__row {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
}

.status-card__label {
  font-size: 12px;
  color: var(--fywz-muted, #9aa7c0);
}

.status-card__value {
  font-size: 14px;
  font-weight: 600;
}

.status-card__value--ok {
  color: #22c55e;
}

.status-card__dot {
  color: var(--fywz-muted, #9aa7c0);
  opacity: 0.6;
}

.status-card__tags {
  margin-left: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.algo-tag {
  display: inline-block;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
}

.algo-tag--als {
  background: rgba(37, 99, 235, 0.15);
  color: #2563eb;
}

.algo-tag--graphx {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.algo-tag--content {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

:deep(.recommend-card) {
  width: 100%;
  max-width: none;
}

@media (max-width: 640px) {
  .status-card__tags {
    margin-left: 0;
    width: 100%;
  }
}

.onboard-banner {
  display: flex;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  border-radius: 14px;
  border: 1px solid rgba(1, 180, 228, 0.35);
  background: linear-gradient(
    135deg,
    rgba(1, 180, 228, 0.12) 0%,
    rgba(37, 99, 235, 0.08) 100%
  );
}

.onboard-banner--guest {
  border-color: rgba(168, 85, 247, 0.35);
  background: linear-gradient(
    135deg,
    rgba(168, 85, 247, 0.1) 0%,
    rgba(1, 180, 228, 0.08) 100%
  );
}

.onboard-banner--success {
  border-color: rgba(34, 197, 94, 0.4);
  background: linear-gradient(
    135deg,
    rgba(34, 197, 94, 0.12) 0%,
    rgba(1, 180, 228, 0.06) 100%
  );
}

.onboard-banner__icon {
  flex-shrink: 0;
  font-size: 1.75rem;
  line-height: 1;
  padding-top: 0.15rem;
}

.onboard-banner__body {
  flex: 1;
  min-width: 0;
}

.onboard-banner__title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
}

.onboard-banner__text {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.55;
  color: var(--fywz-muted, #9aa7c0);
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
  background: rgba(255, 255, 255, 0.08);
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
  font-size: 0.85rem;
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
  border-radius: 8px;
  padding: 0.5rem 1.1rem;
  font-size: 0.875rem;
  font-weight: 600;
  transition: filter 0.2s ease;
}

.onboard-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.onboard-btn--primary {
  border: none;
  background: #01b4e4;
  color: #042541;
}

.onboard-btn--primary:hover:not(:disabled) {
  filter: brightness(1.08);
}

.onboard-btn--ghost {
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: transparent;
  color: inherit;
}

.onboard-btn--ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
}

@media (max-width: 640px) {
  .onboard-banner {
    flex-direction: column;
    gap: 0.65rem;
  }
}
</style>
