<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { recommendApi } from '../api'
import { useUserStore } from '../stores/user'
import MovieRow from '../components/MovieRow.vue'

const userStore = useUserStore()
const items = ref([])

async function load() {
  if (!userStore.isLoggedIn) {
    const { data } = await recommendApi.guest()
    items.value = data.items
    return
  }
  const { data } = await recommendApi.personal()
  items.value = data.items
}

async function refresh() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  const { data } = await recommendApi.refresh()
  items.value = data.items
  ElMessage.success('推荐列表已更新')
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
    <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold">个性化推荐</h1>
        <p class="mt-2 text-sm text-muted">根据你的评分与偏好，为你挑选可能感兴趣的电影</p>
      </div>
      <button
        v-if="userStore.isLoggedIn"
        class="rounded-md bg-[#01B4E4] px-5 py-2 text-sm font-semibold text-white hover:brightness-110"
        @click="refresh"
      >
        刷新推荐
      </button>
    </div>
    <MovieRow title="为你推荐" :movies="items" />
  </div>
</template>
