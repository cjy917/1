import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MoviesView from '../views/MoviesView.vue'
import MovieDetailView from '../views/MovieDetailView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import RecommendView from '../views/RecommendView.vue'
import ProfileView from '../views/ProfileView.vue'
import AuthView from '../views/AuthView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/movies', name: 'movies', component: MoviesView },
    { path: '/movie/:id', name: 'movie-detail', component: MovieDetailView },
    { path: '/analytics', name: 'analytics', component: AnalyticsView },
    { path: '/recommend', name: 'recommend', component: RecommendView },
    { path: '/profile', name: 'profile', component: ProfileView },
    { path: '/login', name: 'login', component: AuthView, meta: { hideShell: true } },
    { path: '/register', name: 'register', component: AuthView, meta: { hideShell: true } },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
