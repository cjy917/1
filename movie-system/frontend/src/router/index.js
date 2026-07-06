import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MoviesView from '../views/MoviesView.vue'
import MovieDetailView from '../views/MovieDetailView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import RecommendView from '../views/RecommendView.vue'
import ProfileView from '../views/ProfileView.vue'
import ChartsView from '../views/ChartsView.vue'
import FilmmakerDetailView from '../views/FilmmakerDetailView.vue'
import AuthView from '../views/AuthView.vue'
import AwardsView from '../views/AwardsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/movies', name: 'movies', component: MoviesView },
    { path: '/awards', name: 'awards', component: AwardsView },
    { path: '/movie/:id', name: 'movie-detail', component: MovieDetailView },
    // 影人列表页（导航「影人」→ /charts）
    { path: '/charts', name: 'charts', component: ChartsView },
    // 影人详情页（点击卡片进入）
    {
      path: '/charts/filmmaker/:role(director|actor)/:name',
      name: 'chart-filmmaker-detail',
      component: FilmmakerDetailView,
    },
    { path: '/filmmakers', redirect: { name: 'charts', hash: '#chart-filmmakers-directors' } },
    {
      path: '/filmmakers/:role(director|actor)/:name',
      redirect: (to) => ({
        name: 'chart-filmmaker-detail',
        params: { role: to.params.role, name: to.params.name },
      }),
    },
    { path: '/analytics', name: 'analytics', component: AnalyticsView },
    // 智能推荐页
    { path: '/recommend', name: 'recommend', component: RecommendView },
    { path: '/profile', name: 'profile', component: ProfileView },
    { path: '/login', name: 'login', component: AuthView, meta: { hideShell: true } },
    { path: '/register', name: 'register', component: AuthView, meta: { hideShell: true } },
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, top: 88, behavior: 'smooth' }
    return { top: 0 }
  },
})

export default router
