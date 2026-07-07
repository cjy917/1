<!--
  【详情页·入口】路由 /movie/:id
  代码搜索: MovieDetailView / useMovieDetailPage
  页面结构（自上而下）:
    01-DetailHeroSection.vue  → Hero 信息与操作按钮
    02-DetailPlayerSection.vue → 正片/预告播放器
    03-DetailReviewsSection.vue → 短评
    04-DetailSimilarSection.vue → 相似推荐
  速查索引: src/code-map.js
-->
<script setup>
import { provide } from 'vue'
import { useMovieDetailPage } from '../composables/detail/useMovieDetailPage'
import DetailHeroSection from '../components/detail-page/01-DetailHeroSection.vue'
import DetailPlayerSection from '../components/detail-page/02-DetailPlayerSection.vue'
import DetailReviewsSection from '../components/detail-page/03-DetailReviewsSection.vue'
import DetailSimilarSection from '../components/detail-page/04-DetailSimilarSection.vue'

const movieDetail = useMovieDetailPage()
provide('movieDetail', movieDetail)
</script>

<template>
  <!-- 【详情·加载中】 -->
  <div v-if="movieDetail.pageLoading" class="detail-page-loading">
    <div class="detail-page-loading__hero" />
  </div>

  <div v-else-if="movieDetail.movie">
    <!-- 【详情·区块1】Hero → 01-DetailHeroSection.vue -->
    <DetailHeroSection />

    <!-- 【详情·区块2】播放器 → 02-DetailPlayerSection.vue -->
    <DetailPlayerSection />

    <!-- 【详情·区块3】短评 → 03-DetailReviewsSection.vue -->
    <DetailReviewsSection />

    <!-- 【详情·区块4】相似推荐 → 04-DetailSimilarSection.vue -->
    <DetailSimilarSection />
  </div>
</template>

<style scoped>
.detail-page-loading {
  min-height: 60vh;
  background: var(--fywz-bg);
}

.detail-page-loading__hero {
  min-height: 60vh;
  background: linear-gradient(
    to right,
    rgba(3, 37, 65, 0.96) 0%,
    rgba(13, 37, 63, 0.88) 42%,
    rgba(20, 33, 61, 0.72) 100%
  );
}
</style>
