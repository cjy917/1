<script setup>
import { onMounted, ref } from 'vue'
import { adminApi } from '../api'

const preview = ref(null)

onMounted(async () => {
  const { data } = await adminApi.preview()
  preview.value = data
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8">
    <h1 class="mb-2 text-3xl font-bold">数据预处理预览</h1>
    <p class="mb-8 text-sm text-[#9aa5b1]">展示爬虫原始数据入库结果与 Spark 清洗流程</p>
    <div v-if="preview" class="space-y-6">
      <div class="grid gap-4 md:grid-cols-3">
        <div class="rounded-2xl bg-[#0b2a44] p-5 ring-1 ring-white/10">
          <p class="text-sm text-[#9aa5b1]">MySQL 表</p>
          <p class="mt-2 text-xl font-bold">{{ preview.mysql_table }}</p>
        </div>
        <div class="rounded-2xl bg-[#0b2a44] p-5 ring-1 ring-white/10">
          <p class="text-sm text-[#9aa5b1]">电影总数</p>
          <p class="mt-2 text-xl font-bold text-[#01B4E4]">{{ preview.total_movies }}</p>
        </div>
        <div class="rounded-2xl bg-[#0b2a44] p-5 ring-1 ring-white/10">
          <p class="text-sm text-[#9aa5b1]">爬虫评分样本</p>
          <p class="mt-2 text-xl font-bold text-[#01B4E4]">{{ preview.crawled_ratings_count }}</p>
        </div>
      </div>
      <div class="rounded-2xl bg-[#0b2a44] p-6 ring-1 ring-white/10">
        <h2 class="mb-3 font-semibold">数据处理流水线</h2>
        <div class="flex flex-wrap gap-2">
          <span v-for="step in preview.pipeline" :key="step" class="rounded-full bg-[#01B4E4]/15 px-3 py-1 text-sm text-[#01B4E4]">{{ step }}</span>
        </div>
      </div>
      <div class="rounded-2xl bg-[#0b2a44] p-6 ring-1 ring-white/10">
        <h2 class="mb-4 font-semibold">样本电影（清洗后）</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="text-[#9aa5b1]">
              <tr>
                <th class="pb-3 pr-4">标题</th>
                <th class="pb-3 pr-4">评分</th>
                <th class="pb-3 pr-4">年份</th>
                <th class="pb-3 pr-4">类型</th>
                <th class="pb-3">来源</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in preview.sample_movies" :key="m.movie_id" class="border-t border-white/5">
                <td class="py-3 pr-4">{{ m.title }}</td>
                <td class="py-3 pr-4">{{ m.rating }}</td>
                <td class="py-3 pr-4">{{ m.release_year }}</td>
                <td class="py-3 pr-4">{{ m.genres }}</td>
                <td class="py-3">{{ m.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
