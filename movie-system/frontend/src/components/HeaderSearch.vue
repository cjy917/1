<script setup>
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { movieApi } from '../api'

const props = defineProps({
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const router = useRouter()
const keyword = ref('')
const suggestions = ref([])
const popularMovies = ref([])
const inputRef = ref(null)
let timer = null

async function loadPopular() {
  if (popularMovies.value.length) return
  try {
    const { data } = await movieApi.home()
    popularMovies.value = (data.popular || []).slice(0, 8)
  } catch {
    popularMovies.value = []
  }
}

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

watch(keyword, (val) => {
  clearTimeout(timer)
  const q = val.trim()
  if (!q) {
    suggestions.value = []
    return
  }
  timer = setTimeout(async () => {
    try {
      const { data } = await movieApi.search(q)
      suggestions.value = data.items || []
    } catch {
      suggestions.value = []
    }
  }, 250)
})

function close() {
  emit('close')
}

function submitSearch(term) {
  const q = (term ?? keyword.value).trim()
  if (!q) return
  close()
  router.push({ name: 'movies', query: { q } })
}

function pickMovie(item) {
  close()
  router.push({ name: 'movie-detail', params: { id: item.movie_id } })
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
  }
}
</script>

<template>
  <div v-if="open" class="header-search" @keydown="onKeydown">
    <div class="header-search__inner">
      <form class="header-search__form" @submit.prevent="submitSearch()">
        <span class="header-search__form-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
          </svg>
        </span>
        <input
          ref="inputRef"
          v-model="keyword"
          class="header-search__input"
          type="search"
          placeholder="搜索电影、导演、演员……"
          autocomplete="off"
        />
      </form>

      <div v-if="keyword.trim() && suggestions.length" class="header-search__section">
        <p class="header-search__section-title">搜索结果</p>
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
          <span v-if="item.release_year" class="header-search__item-meta">{{ item.release_year }}</span>
        </button>
      </div>

      <div v-else-if="popularMovies.length" class="header-search__section">
        <p class="header-search__section-title">
          <span class="header-search__trend-icon" aria-hidden="true">↗</span>
          热门电影
        </p>
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
