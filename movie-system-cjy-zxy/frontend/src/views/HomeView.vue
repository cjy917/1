<!--
  【首页·入口】路由 /home
  页面结构（自上而下）:
    [H1] HeroCarousel.vue           → 顶部轮播
    [H1b] MovieRow (scroll)         → 问卷偏好推荐（有偏好时显示）
    [H2] MovieRow.vue × 3         → 热门/高分/新上映
    [H3] HomeCommentShowcase      → 短评展示
  速查索引: src/code-map.js
-->
<script setup>
import { onMounted, ref, watch } from 'vue'
import { movieApi, recommendApi } from '../api'
import HeroCarousel from '../components/HeroCarousel.vue'
import HomeCommentShowcase from '../components/HomeCommentShowcase.vue'
import MovieRow from '../components/MovieRow.vue'
import { useUserStore } from '../stores/user'
import { initLocalTrailerIds } from '../utils/trailerCache'

const userStore = useUserStore()

/** 【首页-H2】三个电影分区配置 */
const ROW_SECTIONS = [
  { title: '热门电影', key: 'popular' },
  { title: '高分电影', key: 'top_rated' },
  { title: '新上映', key: 'latest' },
]

const sections = ref({ banner: [], popular: [], top_rated: [], latest: [] })
const preferenceMovies = ref([])

/** 【API·偏好推荐】POST /api/recommend/preference */
async function loadPreferenceMovies() {
  userStore.loadUserFromLocal()
  if (!userStore.hasPreference) {
    preferenceMovies.value = []
    return
  }
  try {
    const { data } = await recommendApi.byPreference(userStore.preference)
    preferenceMovies.value = data.items || []
  } catch {
    preferenceMovies.value = []
  }
}

/** 【API·首页】GET /api/movies/home → movie_service.get_home_sections */
onMounted(async () => {
  await Promise.all([
    initLocalTrailerIds(),
    movieApi.home().then(({ data }) => { sections.value = data }),
    loadPreferenceMovies(),
  ])
})

watch(
  () => userStore.preference,
  () => loadPreferenceMovies(),
  { deep: true },
)
</script>

<template>
  <div>
    <!-- 【首页·区块1】顶部轮播 → HeroCarousel.vue，搜 loadTrailer -->
    <HeroCarousel :movies="sections.banner" />

    <!-- 【首页·偏好推荐】问卷结果，横向滚动一行 -->
    <MovieRow
      v-if="userStore.hasPreference && preferenceMovies.length"
      title="根据你的偏好推荐"
      :movies="preferenceMovies"
      layout="scroll"
    />

    <!-- 【首页·区块2】电影列表 → MovieRow.vue，数据来自 movieApi.home -->
    <MovieRow
      v-for="row in ROW_SECTIONS"
      :key="row.key"
      :title="row.title"
      :movies="sections[row.key]"
      layout="grid"
      :grid-rows="2"
    />

    <!-- 【首页·区块3】短评展示 → HomeCommentShowcase.vue，搜 homeComments -->
    <HomeCommentShowcase />
  </div>
</template>
