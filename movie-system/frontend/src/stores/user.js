import { defineStore } from 'pinia'
import { authApi } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    loaded: false,
  }),
  getters: {
    isLoggedIn: (state) => !!state.user,
  },
  actions: {
    async fetchMe() {
      try {
        const { data } = await authApi.me()
        this.user = data.user
      } catch {
        this.user = null
      } finally {
        this.loaded = true
      }
    },
    async login(form) {
      const { data } = await authApi.login(form)
      this.user = data.user
      return data
    },
    async register(form) {
      const { data } = await authApi.register(form)
      this.user = data.user
      return data
    },
    async logout() {
      await authApi.logout()
      this.user = null
    },
  },
})
