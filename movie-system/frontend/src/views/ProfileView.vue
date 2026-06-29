<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { favoriteApi, listApi, ratingApi, watchlistApi } from '../api'
import ProfileMovieGrid from '../components/ProfileMovieGrid.vue'
import { useRatingsStore } from '../stores/ratings'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const ratingsStore = useRatingsStore()
const ratings = ref([])
const favorites = ref([])
const watchlist = ref([])
const lists = ref([])
const loading = ref(false)

async function loadAll() {
  if (!userStore.isLoggedIn) return
  loading.value = true
  try {
    const [r, f, w, l] = await Promise.all([
      ratingApi.mine(),
      favoriteApi.list(),
      watchlistApi.list(),
      listApi.list(),
    ])
    ratings.value = r.data.items || []
    favorites.value = f.data.items || []
    watchlist.value = w.data.items || []
    lists.value = l.data.items || []
  } finally {
    loading.value = false
  }
}

function removeFrom(listRef, movieId) {
  listRef.value = listRef.value.filter((item) => item.movie_id !== movieId)
}

async function removeRating(movieId) {
  try {
    await ratingsStore.remove(movieId)
    removeFrom(ratings, movieId)
    ElMessage.success('评分已删除')
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

async function removeFavorite(movieId) {
  try {
    await favoriteApi.remove(movieId)
    removeFrom(favorites, movieId)
    ElMessage.success('已取消收藏')
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

async function removeWatchlist(movieId) {
  try {
    await watchlistApi.remove(movieId)
    removeFrom(watchlist, movieId)
    ElMessage.success('已从待看片单移除')
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

async function removeList(movieId) {
  try {
    await listApi.remove(movieId)
    removeFrom(lists, movieId)
    ElMessage.success('已从片单移除')
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8">
    <h1 class="mb-2 text-3xl font-bold">个人中心</h1>
    <p v-if="userStore.isLoggedIn" class="mb-8 text-sm text-muted">
      {{ userStore.user?.username }} · 管理你的评分、收藏与片单
    </p>

    <div
      v-if="!userStore.isLoggedIn"
      class="section-surface rounded-2xl p-8 text-center ring-1"
      style="border-color: var(--fywz-border)"
    >
      <p class="text-muted">请先登录查看评分、收藏、片单和待看片单</p>
      <router-link to="/login" class="mt-4 inline-block rounded-full bg-[#01B4E4] px-6 py-2 font-semibold text-[#042541]">
        去登录
      </router-link>
    </div>

    <template v-else>
      <p v-if="loading" class="mb-6 text-sm text-muted">加载中…</p>

      <section class="mb-10">
        <h2 class="section-title">我的评分 <span class="profile-count">{{ ratings.length }}</span></h2>
        <ProfileMovieGrid
          :movies="ratings"
          empty-text="还没有评分，去电影详情页打星吧"
          remove-label="删评分"
          @remove="removeRating"
        />
      </section>

      <section class="mb-10">
        <h2 class="section-title">我的收藏 <span class="profile-count">{{ favorites.length }}</span></h2>
        <ProfileMovieGrid
          :movies="favorites"
          empty-text="还没有收藏的电影"
          remove-label="取消收藏"
          @remove="removeFavorite"
        />
      </section>

      <section class="mb-10">
        <h2 class="section-title">我的片单 <span class="profile-count">{{ lists.length }}</span></h2>
        <ProfileMovieGrid
          :movies="lists"
          empty-text="片单还是空的，在电影详情页点击「添加到片单」"
          remove-label="移出片单"
          @remove="removeList"
        />
      </section>

      <section>
        <h2 class="section-title">待看片单 <span class="profile-count">{{ watchlist.length }}</span></h2>
        <ProfileMovieGrid
          :movies="watchlist"
          empty-text="待看片单还是空的，在电影详情页点击「待看片单」"
          remove-label="移出待看"
          @remove="removeWatchlist"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.profile-count {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--fywz-muted);
}
</style>
