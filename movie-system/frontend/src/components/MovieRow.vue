<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import MovieCard from './MovieCard.vue'

defineProps({
  title: { type: String, required: true },
  movies: { type: Array, default: () => [] },
  subtitle: { type: String, default: '' },
  moreTo: { type: [String, Object], default: null },
  moreLabel: { type: String, default: '查看全部' },
})

const track = ref(null)

onMounted(() => {
  let isDown = false
  let startX = 0
  let scrollLeft = 0
  const el = track.value
  if (!el) return

  el.addEventListener('mousedown', (e) => {
    isDown = true
    startX = e.pageX - el.offsetLeft
    scrollLeft = el.scrollLeft
  })
  el.addEventListener('mouseleave', () => { isDown = false })
  el.addEventListener('mouseup', () => { isDown = false })
  el.addEventListener('mousemove', (e) => {
    if (!isDown) return
    e.preventDefault()
    el.scrollLeft = scrollLeft - (e.pageX - el.offsetLeft - startX)
  })
})
</script>

<template>
  <section class="section-surface py-8">
    <div class="mx-auto max-w-[1400px] px-4 lg:px-8">
      <div class="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 v-if="title" class="text-2xl font-bold">{{ title }}</h2>
          <p v-if="subtitle" class="mt-1 text-sm text-muted">{{ subtitle }}</p>
        </div>
        <RouterLink
          v-if="moreTo"
          :to="moreTo"
          class="text-sm font-semibold text-[#01B4E4] hover:underline"
        >
          {{ moreLabel }} →
        </RouterLink>
      </div>
      <div ref="track" class="flex gap-4 overflow-x-auto pb-3 scroll-smooth">
        <MovieCard v-for="movie in movies" :key="movie.movie_id" :movie="movie" />
      </div>
    </div>
  </section>
</template>

<style scoped>
::-webkit-scrollbar-thumb {
  background: var(--fywz-accent);
  opacity: 0.5;
  border-radius: 999px;
}
</style>
