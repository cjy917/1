import { defineStore } from 'pinia'

const STORAGE_KEY = 'fywz-theme'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: localStorage.getItem(STORAGE_KEY) || 'light',
  }),
  getters: {
    isDark: (state) => state.mode === 'dark',
  },
  actions: {
    apply() {
      document.documentElement.setAttribute('data-theme', this.mode)
      document.documentElement.classList.toggle('dark', this.mode === 'dark')
      localStorage.setItem(STORAGE_KEY, this.mode)
    },
    init() {
      this.apply()
    },
    toggle() {
      this.mode = this.mode === 'light' ? 'dark' : 'light'
      this.apply()
    },
    set(mode) {
      this.mode = mode
      this.apply()
    },
  },
})
