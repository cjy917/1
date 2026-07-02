<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { analyticsApi } from '../api'

const router = useRouter()
const items = ref([])

const leftColumn = computed(() => items.value.slice(0, 5))
const rightColumn = computed(() => items.value.slice(5, 10))

const maxCount = computed(() => {
  if (!items.value.length) return 1
  return Math.max(...items.value.map((m) => m.rating_count))
})

function countWidth(count) {
  return `${Math.max(4, (count / maxCount.value) * 100)}%`
}

function ratingWidth(score) {
  return `${Math.max(4, (score / 10) * 100)}%`
}

function formatCount(n) {
  return Number(n).toLocaleString('en-US')
}

function openMovie(movie) {
  router.push({ name: 'movie-detail', params: { id: movie.movie_id } })
}

onMounted(async () => {
  const { data } = await analyticsApi.ratingLeaderboard()
  items.value = data.items
})
</script>

<template>
  <section class="section-surface py-10">
    <div class="mx-auto max-w-[1400px] px-4 lg:px-8">
      <div class="mb-6 flex flex-wrap items-center gap-4">
        <h2 class="text-2xl font-bold">评分排行榜</h2>
        <div class="flex items-center gap-4 text-sm text-muted">
          <span class="flex items-center gap-1.5">
            <span class="inline-block h-2.5 w-2.5 rounded-full bg-[#21d07a]" />
            评分人数
          </span>
          <span class="flex items-center gap-1.5">
            <span class="inline-block h-2.5 w-2.5 rounded-full bg-[#db2360]" />
            综合评分
          </span>
        </div>
      </div>

      <div class="grid gap-x-10 gap-y-5 md:grid-cols-2">
        <div
          v-for="(column, colIdx) in [leftColumn, rightColumn]"
          :key="colIdx"
          class="space-y-5"
        >
          <button
            v-for="movie in column"
            :key="movie.movie_id"
            class="flex w-full items-start gap-3 text-left transition hover:opacity-90"
            @click="openMovie(movie)"
          >
            <img
              :src="movie.poster_url"
              :alt="movie.title"
              class="h-11 w-11 shrink-0 rounded-full object-cover ring-1 ring-black/10"
            />
            <div class="min-w-0 flex-1 pt-0.5">
              <p class="mb-2 truncate text-[15px] font-bold leading-tight">{{ movie.title }}</p>
              <div class="mb-1.5 flex items-center gap-2">
                <div class="h-2 flex-1 overflow-hidden rounded-sm bg-black/5">
                  <div
                    class="h-full rounded-sm bg-[#21d07a]"
                    :style="{ width: countWidth(movie.rating_count) }"
                  />
                </div>
                <span class="w-16 shrink-0 text-right text-xs font-semibold text-[#21d07a]">
                  {{ formatCount(movie.rating_count) }}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <div class="h-2 flex-1 overflow-hidden rounded-sm bg-black/5">
                  <div
                    class="h-full rounded-sm bg-[#db2360]"
                    :style="{ width: ratingWidth(movie.rating) }"
                  />
                </div>
                <span class="w-10 shrink-0 text-right text-xs font-semibold text-[#db2360]">
                  {{ movie.rating.toFixed(1) }}
                </span>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
[data-theme='dark'] .bg-black\/5 {
  background: rgba(255, 255, 255, 0.08);
}
</style>
