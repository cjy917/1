/**
 * =============================================================================
 * 前端路由
 * =============================================================================
 * 【登录注册·问卷】相关:
 *   /           → AuthView（默认入口，hideShell）
 *   /login      → 重定向 /
 *   /register   → 重定向 /?mode=register
 *   beforeEach  → 未登录拦截，已登录访问 / 跳转 /home
 * 速查索引: src/code-map.js → AUTH_PAGE_MAP (A3)
 * =============================================================================
 */
import { createRouter, createWebHistory } from 'vue-router'
import AuthView from '../views/AuthView.vue'
import HomeView from '../views/HomeView.vue'
import MoviesView from '../views/MoviesView.vue'
import MovieDetailView from '../views/MovieDetailView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import RecommendView from '../views/RecommendView.vue'
import ProfileView from '../views/ProfileView.vue'
import PersonView from '../views/PersonView.vue'

/** 登录/注册/问卷入口（打开系统默认页） */
const AUTH_PATH = '/'

/** 无需登录即可访问的路径 */
const PUBLIC_PATHS = new Set([AUTH_PATH, '/login', '/register'])

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: AUTH_PATH,
      name: 'auth',
      component: AuthView,
      meta: { hideShell: true, public: true },
    },
    {
      path: '/home',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/movies',
      name: 'movies',
      component: MoviesView,
      meta: { requiresAuth: true },
    },
    {
      path: '/movie/:id',
      name: 'movie-detail',
      component: MovieDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/person/:name',
      name: 'person-detail',
      component: PersonView,
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: AnalyticsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/recommend',
      name: 'recommend',
      component: RecommendView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    { path: '/login', redirect: AUTH_PATH },
    {
      path: '/register',
      redirect: { path: AUTH_PATH, query: { mode: 'register' } },
    },
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return false
    return { top: 0 }
  },
})

/** 【A3】登录态守卫：未登录 → /，已登录访问 / → /home */
router.beforeEach(async (to) => {
  const { useUserStore } = await import('../stores/user')
  const userStore = useUserStore()

  if (!userStore.loaded) {
    userStore.loadUserFromLocal()
    await userStore.fetchMe()
  }

  const isLoggedIn = userStore.isLoggedIn
  const isPublic = PUBLIC_PATHS.has(to.path) || to.meta.public === true

  if (isLoggedIn && to.path === AUTH_PATH) {
    return '/home'
  }

  if (!isLoggedIn && (to.meta.requiresAuth || !isPublic)) {
    return {
      path: AUTH_PATH,
      query: to.fullPath !== AUTH_PATH ? { redirect: to.fullPath } : {},
    }
  }

  return true
})

export default router
