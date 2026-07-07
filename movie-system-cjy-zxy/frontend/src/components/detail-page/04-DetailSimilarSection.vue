<!--
  【详情页·区块4】同类相似推荐
  代码搜索: 相似推荐 MovieRow recommend similar
  API/后端: 见 code-map.js
-->
<template>
  <div class="mx-auto max-w-7xl px-4 pb-8 lg:px-8">
    <MovieRow title="同类相似推荐" :movies="d.similar" />
  </div>
</template>

<script setup>
import { inject } from 'vue'
import MovieRow from '../MovieRow.vue'

/** 从 MovieDetailView provide 的 composable 对象中取 similar 列表 */
const d = inject('movieDetail')
</script>
