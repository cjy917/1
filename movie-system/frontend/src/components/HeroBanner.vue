<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  movies: { type: Array, default: () => [] },
})

const router = useRouter()
const index = ref(0)
let timer = null

const current = computed(() => props.movies[index.value] || null)
const poster = computed(() => current.value?.poster_url || `/api/posters/${current.value?.movie_id}`)

onMounted(() => {
  timer = setInterval(() => {
    if (!props.movies.length) return
    index.value = (index.value + 1) % props.movies.length
  }, 6000)
})

function openDetail() {
  if (current.value) router.push({ name: 'movie-detail', params: { id: current.value.movie_id } })
}
</script>

<template>
  <section v-if="current" class="relative h-[70vh] min-h-[420px] overflow-hidden">
    <img :src="poster" :alt="current.title" class="absolute inset-0 h-full w-full object-cover opacity-40 blur-sm scale-110" />
    <div class="absolute inset-0 bg-gradient-to-r from-[#031d31] via-[#042541]/90 to-transparent" />
    <div class="absolute inset-0 bg-gradient-to-t from-[#031d31] via-transparent to-transparent" />
    <div class="relative mx-auto flex h-full max-w-7xl items-end px-4 pb-12">
      <div class="max-w-2xl space-y-4">
        <span class="rounded bg-[#01B4E4] px-3 py-1 text-xs font-bold text-[#042541]">热门推荐</span>
        <h1 class="text-4xl font-black md:text-5xl">{{ current.title }}</h1>
        <p class="line-clamp-3 text-base leading-7 text-[#d7dee6]">{{ current.summary }}</p>
        <div class="flex flex-wrap items-center gap-3 text-sm text-[#9aa5b1]">
          <span class="text-lg font-bold text-[#01B4E4]">{{ Number(current.rating).toFixed(1) }}</span>
          <span>{{ current.release_year }}</span>
          <span>{{ current.genres }}</span>
        </div>
        <button class="rounded-full bg-[#01B4E4] px-6 py-2 font-semibold text-[#042541]" @click="openDetail">查看详情</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
