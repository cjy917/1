<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import { useUserStore } from './stores/user'
import { useThemeStore } from './stores/theme'
import { useRatingsStore } from './stores/ratings'

const route = useRoute()
const userStore = useUserStore()
const themeStore = useThemeStore()
const ratingsStore = useRatingsStore()

const hideShell = computed(() => route.meta.hideShell === true)

onMounted(() => {
  themeStore.init()
  userStore.fetchMe()
})

watch(
  () => userStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) ratingsStore.fetchMine()
    else ratingsStore.clear()
  },
  { immediate: true },
)
</script>

<template>
  <div class="min-h-screen" style="background: var(--fywz-bg)">
    <template v-if="!hideShell">
      <AppHeader />
      <main class="page-shell">
        <router-view />
      </main>
      <AppFooter />
    </template>
    <router-view v-else />
  </div>
</template>
