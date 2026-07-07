/**
 * =============================================================================
 * 【登录注册·问卷】用户状态 Store
 * =============================================================================
 * 用法: useUserStore() — AuthView / router 守卫 / HomeView 偏好推荐
 * - login / register → authApi → session cookie
 * - preference → localStorage（userPreference）
 * 速查索引: src/code-map.js → AUTH_PAGE_MAP (A5)
 * =============================================================================
 */
import { defineStore } from 'pinia'

import { authApi } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    loaded: false,
    /** 问卷偏好：类型 / 导演 / 演员（本地持久化） */
    preference: {
      likeGenres: [],
      likeDirectors: [],
      likeActors: [],
    },
  }),

  getters: {
    isLoggedIn: (state) => !!state.user,
    /** 是否填写过任一问卷项（首页偏好推荐用） */
    hasPreference: (state) => {
      const p = state.preference
      return !!(p.likeGenres.length || p.likeDirectors.length || p.likeActors.length)
    },
  },

  actions: {
    /** 【A3】GET /api/auth/me — 路由守卫与 App 启动时拉取登录态 */
    async fetchMe() {
      try {
        const { data } = await authApi.me()
        this.user = data.user
      } catch {
        this.user = null
      } finally {
        this.loaded = true
        this.loadUserFromLocal()
      }
    },

    /** 从 localStorage 恢复问卷偏好 */
    loadUserFromLocal() {
      const localPref = localStorage.getItem('userPreference')
      if (localPref) {
        try {
          this.preference = { ...this.preference, ...JSON.parse(localPref) }
        } catch {
          localStorage.removeItem('userPreference')
        }
      }
    },

    /** 【A1】POST /api/auth/login */
    async login(form) {
      const { data } = await authApi.login(form)
      this.user = data.user
      this.loadUserFromLocal()
      return data
    },

    /** 【A1】POST /api/auth/register */
    async register(form) {
      const { data } = await authApi.register(form)
      this.user = data.user
      return data
    },

    /** 【A2】问卷完成 / 跳过时写入 localStorage */
    savePreference(data) {
      this.preference.likeGenres = [...(data.likeGenres || [])]
      this.preference.likeDirectors = [...(data.likeDirectors || [])]
      this.preference.likeActors = [...(data.likeActors || [])]
      localStorage.setItem('userPreference', JSON.stringify(this.preference))
    },

    /** POST /api/auth/logout */
    async logout() {
      try {
        await authApi.logout()
      } finally {
        this.user = null
      }
    },
  },
})
