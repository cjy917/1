<script setup>
import { onMounted, ref } from 'vue'
import MovieCard from './MovieCard.vue'

defineProps({
  title: { type: String, required: true },
  movies: { type: Array, default: () => [] },
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
      <h2 v-if="title" class="mb-5 text-2xl font-bold">{{ title }}</h2>
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
