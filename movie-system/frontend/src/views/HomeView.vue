<script setup>
import { onMounted, ref } from 'vue'
import { movieApi } from '../api'
import HeroCarousel from '../components/HeroCarousel.vue'
import MovieRow from '../components/MovieRow.vue'
import RatingLeaderboard from '../components/RatingLeaderboard.vue'
import { initLocalTrailerIds } from '../utils/trailerCache'

const sections = ref({ banner: [], popular: [], top_rated: [], latest: [] })

onMounted(async () => {
  await Promise.all([initLocalTrailerIds(), movieApi.home().then(({ data }) => { sections.value = data })])
})
</script>

<template>
  <div>
    <HeroCarousel :movies="sections.banner" />

    <MovieRow title="热门电影" :movies="sections.popular" />
    <MovieRow title="高分电影" :movies="sections.top_rated" />
    <MovieRow title="新上映" :movies="sections.latest" />
    <RatingLeaderboard />
  </div>
</template>
