/**
 * Mac 本地 Vite 配置副本 — 勿替换 movie-system/frontend/vite.config.js
 *
 * 用法：
 *   cd movie-system/frontend
 *   npm run dev -- --config ../../local/mac/vite.config.js
 *
 * 默认将 API 代理到 5001（规避 macOS AirPlay 占用 5000）
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const BACKEND_PORT = process.env.BACKEND_PORT || '5001'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
})
