<script setup>
import { computed } from 'vue'
import SearchBar from './SearchBar.vue'

const props = defineProps({
  movies: { type: Array, default: () => [] },
})

const bgPosters = computed(() => props.movies.slice(0, 4))
</script>

<template>
  <section class="relative overflow-hidden bg-[#032541]">
    <!-- 背景海报拼贴 + 青色遮罩，贴近 TMDB 欢迎区 -->
    <div class="absolute inset-0 flex">
      <img
        v-for="(movie, idx) in bgPosters"
        :key="movie.movie_id"
        :src="movie.poster_url || `/api/posters/${movie.movie_id}`"
        :alt="movie.title"
        class="h-full flex-1 object-cover opacity-30"
        :class="idx % 2 === 0 ? 'scale-105' : 'scale-110'"
      />
    </div>
    <div class="absolute inset-0 bg-[#01B4E4]/75 mix-blend-multiply" />
    <div class="absolute inset-0 bg-gradient-to-r from-[#01B4E4]/90 via-[#01B4E4]/70 to-[#01B4E4]/50" />

    <div class="relative mx-auto max-w-[1400px] px-4 py-16 lg:px-8 lg:py-20">
      <div class="max-w-3xl space-y-4">
        <h1 class="text-4xl font-bold text-white md:text-5xl">欢迎。</h1>
        <p class="text-lg leading-8 text-white/95 md:text-xl">
          这里有海量的电影数据、评分与推荐结果，快来探索发现吧！
        </p>
        <div class="pt-4">
          <SearchBar variant="hero" />
        </div>
      </div>
    </div>
  </section>
</template>
