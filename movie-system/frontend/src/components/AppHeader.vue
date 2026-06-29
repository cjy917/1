<script setup>
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useSearchPanel } from '../composables/useSearchPanel'
import HeaderSearch from './HeaderSearch.vue'
import ThemeToggle from './ThemeToggle.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { searchOpen, toggleSearch, closeSearch } = useSearchPanel()

const navItems = [
  { label: '电影', to: '/movies' },
  { label: '数据分析', to: '/analytics' },
  { label: '推荐', to: '/recommend' },
]

async function handleLogout() {
  await userStore.logout()
  router.push('/')
}

function onDocumentClick(event) {
  if (!searchOpen.value) return
  const target = event.target
  if (!(target instanceof Element)) return
  if (target.closest('.site-header-shell') || target.closest('.header-search')) return
  closeSearch()
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.documentElement.classList.remove('search-panel-open')
})

watch(
  () => route.fullPath,
  () => closeSearch(),
)

watch(searchOpen, (open) => {
  document.documentElement.classList.toggle('search-panel-open', open)
  if (open && route.path === '/') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
})
</script>

<template>
  <header
    class="site-header-shell site-header fixed inset-x-0 top-0 z-50"
  >
    <div class="site-header__inner">
      <div class="site-header__left">
        <router-link to="/" class="site-header-logo">
          <span class="site-header-logo__mark">FYWZ</span>
          <span class="site-header-logo__pill" aria-hidden="true" />
          <span class="site-header-logo__suffix">movies</span>
        </router-link>

        <nav class="site-header-nav">
          <router-link
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="site-nav-link"
            :class="{ 'is-active': route.path === item.to }"
          >
            {{ item.label }}
          </router-link>
        </nav>
      </div>

      <div class="site-header__right">
        <ThemeToggle />

        <template v-if="userStore.isLoggedIn">
          <span class="site-header-user hidden md:inline">{{ userStore.user?.username }}</span>
          <router-link to="/profile" class="site-header-avatar" :title="userStore.user?.username">
            {{ (userStore.user?.username || '?').slice(0, 1).toUpperCase() }}
          </router-link>
          <button type="button" class="site-header-action site-header-action--text" @click="handleLogout">
            退出
          </button>
        </template>
        <template v-else>
          <router-link to="/login" class="site-header-action site-header-action--text">登录</router-link>
          <router-link to="/register" class="site-header-action site-header-action--text">注册</router-link>
        </template>

        <button
          type="button"
          class="site-header-search"
          :class="{ 'site-header-search--active': searchOpen }"
          aria-label="搜索"
          :aria-expanded="searchOpen"
          @click.stop="toggleSearch"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z"
            />
          </svg>
        </button>
      </div>
    </div>
  </header>

  <Transition name="search-panel">
    <HeaderSearch v-if="searchOpen" :open="searchOpen" class="header-search--flow" @close="closeSearch" />
  </Transition>
</template>
