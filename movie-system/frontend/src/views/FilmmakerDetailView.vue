<script setup>
/**
 * 影人详情页（/charts/filmmaker/:role/:name）
 * - role: director | actor
 * - 展示该影人全部作品 + 底部相关导演/演员
 */
import { computed, ref, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { chartsApi } from '../api'
import MovieCard from '../components/MovieCard.vue'
import FilmmakerPersonCard from '../components/FilmmakerPersonCard.vue'

const route = useRoute()
const loading = ref(true)
const detail = ref(null)

const roleLabel = computed(() => detail.value?.role_label || (route.params.role === 'director' ? '导演' : '演员'))
const relatedPeople = computed(() => detail.value?.related || [])
const relatedHint = computed(() =>
  route.params.role === 'director'
    ? '关联方式包括：共同执导同一部电影，或由同一演员分别出演两位导演的作品'
    : '下列演员曾与当前影人在同一部电影中共同出演',
)

async function loadDetail() {
  loading.value = true
  try {
    // GET /api/charts/filmmaker/{role}/{name}
    const { data } = await chartsApi.filmmaker(route.params.role, route.params.name)
    detail.value = data
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

function scrollToWorks() {
  nextTick(() => {
    document.getElementById('filmmaker-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

watch(
  () => [route.params.role, route.params.name, route.hash],
  async () => {
    await loadDetail()
    // 从相关影人卡片点进来时带 #filmmaker-works，滚到作品区
    if (route.hash === '#filmmaker-works') {
      scrollToWorks()
    } else {
      window.scrollTo({ top: 0, behavior: 'instant' })
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="filmmaker-detail mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
    <div v-if="loading" class="py-16 text-center text-muted">加载中...</div>
    <div v-else-if="!detail" class="py-16 text-center text-muted">未找到该影人相关电影</div>
    <template v-else>
      <div id="filmmaker-works" class="scroll-mt-24">
        <div class="filmmaker-header mb-8">
          <h2 class="filmmaker-header__role">{{ roleLabel }}</h2>
          <p class="filmmaker-header__name">{{ detail.name }}</p>
          <p class="filmmaker-header__meta">
            库内共{{ detail.movie_count }}部作品，按评分从高到低展示
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          <MovieCard v-for="movie in detail.movies" :key="movie.movie_id" :movie="movie" />
        </div>
      </div>

      <section v-if="relatedPeople.length" class="related-section">
        <div class="related-section__head">
          <h2 class="related-section__title">{{ detail.related_label }}</h2>
          <p class="related-section__hint">{{ relatedHint }}</p>
        </div>
        <div class="related-grid">
          <FilmmakerPersonCard
            v-for="person in relatedPeople"
            :key="person.name"
            :person="person"
            :role="route.params.role"
            :subject-name="detail.name"
            relation
          />
        </div>
      </section>
    </template>
  </div>
</template>


<style scoped>
.filmmaker-header__role,
.related-section__title {
  font-size: 1.375rem;
  font-weight: 800;
  color: var(--fywz-text);
}

.filmmaker-header__name {
  margin-top: 0.35rem;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.filmmaker-header__meta {
  margin-top: 0.35rem;
  font-size: 0.8125rem;
  color: var(--fywz-text-muted);
}

.related-section {
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 1px solid var(--fywz-border);
}

.related-section__head {
  margin-bottom: 1.25rem;
}

.related-section__hint {
  margin-top: 0.35rem;
  font-size: 0.8125rem;
  color: var(--fywz-text-muted);
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

@media (min-width: 640px) {
  .related-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.15rem;
  }
}

@media (min-width: 1024px) {
  .related-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1.25rem;
  }
}

@media (min-width: 1280px) {
  .related-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}
</style>


