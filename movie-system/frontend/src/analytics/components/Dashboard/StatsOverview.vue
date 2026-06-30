<template>
  <!-- 数据概览卡片组 -->
  <div class="stats-overview">
    <StatsCard 
      icon="🎬"
      label="电影总数"
      :value="overview?.total_movies || 0"
    />
    <StatsCard 
      icon="⭐"
      label="平均评分"
      :value="overview?.avg_rating || 0"
      :decimals="1"
    />
    <StatsCard 
      icon="👥"
      label="总评分人数"
      :value="overview?.total_ratings || 0"
    />
    <StatsCard 
      icon="💬"
      label="总影评数"
      :value="overview?.total_reviews || 0"
    />
  </div>
</template>

<script setup>
import StatsCard from './StatsCard.vue'

/**
 * 数据概览组件
 * 
 * 展示数据分析页面顶部的四个核心统计指标：
 * - 电影总数
 * - 平均评分
 * - 总评分人数
 * - 总影评数
 */

defineProps({
  /** 概览统计数据 */
  overview: {
    type: Object,
    default: null
  }
})
</script>

<style scoped>
.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 48px;
}

@media (max-width: 1024px) {
  .stats-overview {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-overview {
    grid-template-columns: 1fr;
  }
}
</style>
