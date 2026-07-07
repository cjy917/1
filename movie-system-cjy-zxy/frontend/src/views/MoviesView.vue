<script setup>
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { movieApi } from '../api'
import MovieCard from '../components/MovieCard.vue'
import MovieFilterSidebar from '../components/MovieFilterSidebar.vue'

const route = useRoute()
const router = useRouter()
const filters = ref({ years: [], genres: [], languages: [] })
const movies = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(1)
let syncingRoute = false

const defaultQuery = () => ({
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

const query = reactive(defaultQuery())

function splitCsv(value) {
  if (!value) return []
  return String(value).split(',').map((item) => item.trim()).filter(Boolean)
}

function parseRouteQuery(routeQuery = {}) {
  return {
    q: routeQuery.q || '',
    selectedGenres: splitCsv(routeQuery.genres),
    selectedLanguages: splitCsv(routeQuery.languages),
    year_from: routeQuery.year_from || '',
    year_to: routeQuery.year_to || '',
    sort: routeQuery.sort || 'rating_desc',
    min_rating: routeQuery.min_rating || '',
    max_rating: routeQuery.max_rating || '',
    min_votes: routeQuery.min_votes ? Number(routeQuery.min_votes) : 0,
  }
}

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

function routeQuerySignature(routeQuery = {}) {
  return JSON.stringify({
    ...parseRouteQuery(routeQuery),
    page: routeQuery.page ? Math.max(1, Number(routeQuery.page) || 1) : 1,
  })
}

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

async function loadFilters() {
  const { data } = await movieApi.filters()
  filters.value = data
}

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

function applyQueryPatch(patch = {}) {
  if (Array.isArray(patch.selectedGenres)) {
    query.selectedGenres.splice(0, query.selectedGenres.length, ...patch.selectedGenres)
  }
  if (Array.isArray(patch.selectedLanguages)) {
    query.selectedLanguages.splice(0, query.selectedLanguages.length, ...patch.selectedLanguages)
  }
  const { selectedGenres, selectedLanguages, ...rest } = patch
  if (Object.keys(rest).length) {
    Object.assign(query, rest)
  }
}

async function syncRouteQuery() {
  syncingRoute = true
  await router.replace({ name: 'movies', query: buildRouteQuery() })
  await nextTick()
  syncingRoute = false
}

async function onApply(patch = {}, reload = true) {
  applyQueryPatch(patch)
  if (reload) {
    page.value = 1
    await syncRouteQuery()
    loadMovies()
  }
}

async function onReset() {
  applyQueryPatch(defaultQuery())
  page.value = 1
  await syncRouteQuery()
  loadMovies()
}

async function goPage(nextPage) {
  page.value = nextPage
  await syncRouteQuery()
  loadMovies()
}

function restoreFromRoute(routeQuery = route.query) {
  applyQueryPatch(parseRouteQuery(routeQuery))
  page.value = routeQuery.page ? Math.max(1, Number(routeQuery.page) || 1) : 1
}

watch(
  () => route.query,
  (routeQuery) => {
    if (route.name !== 'movies' || syncingRoute) return
    if (routeQuerySignature(routeQuery) === stateQuerySignature()) return
    restoreFromRoute(routeQuery)
    loadMovies()
  },
  { deep: true },
)

onMounted(async () => {
  restoreFromRoute(route.query)
  await loadFilters()
  loadMovies()
})
</script>

<template>
  <div class="movies-page mx-auto max-w-7xl px-4 py-8">
    <div class="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold">电影库</h1>
        <p v-if="query.q" class="mt-1 text-sm text-muted">搜索「{{ query.q }}」，共 {{ total }} 部结果</p>
        <p v-else class="mt-1 text-sm text-muted">共 {{ total }} 部电影</p>
      </div>
    </div>
    <div class="grid gap-6 lg:grid-cols-[280px_1fr]">
      <MovieFilterSidebar :query="query" :filters="filters" @apply="onApply" @reset="onReset" />
      <section>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
          <MovieCard v-for="movie in movies" :key="movie.movie_id" :movie="movie" />
        </div>
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
.movies-page__pager {
  border: 1px solid var(--fywz-border);
  background: var(--fywz-surface-2);
  color: var(--fywz-text);
}

.movies-page__pager:hover:not(:disabled) {
  border-color: #01b4e4;
  color: #01b4e4;
}
</style>
