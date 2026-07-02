<script setup>
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
</script>

<template>
  <footer style="background: var(--fywz-nav)" class="text-white">
    <div class="mx-auto max-w-[1400px] px-4 py-12 lg:px-8">
      <div class="mb-8 flex flex-wrap items-center gap-6">
        <div class="flex items-center gap-2">
          <span class="rounded bg-[#01B4E4] px-3 py-1 text-xl font-black text-[#032541]">FYWZ</span>
          <span class="text-lg font-semibold">movies</span>
        </div>
        <div v-if="userStore.isLoggedIn" class="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-[#032541]">
          你好，{{ userStore.user.username }}
        </div>
      </div>

      <div class="grid gap-8 text-sm sm:grid-cols-3">
        <div>
          <h4 class="mb-3 font-bold text-[#01B4E4]">浏览</h4>
          <ul class="space-y-2 text-white/75">
            <li><router-link to="/movies" class="hover:text-white">电影库</router-link></li>
            <li><router-link to="/recommend" class="hover:text-white">个性化推荐</router-link></li>
            <li><router-link to="/analytics" class="hover:text-white">数据分析</router-link></li>
          </ul>
        </div>
        <div>
          <h4 class="mb-3 font-bold text-[#01B4E4]">账户</h4>
          <ul class="space-y-2 text-white/75">
            <li><router-link to="/profile" class="hover:text-white">个人中心</router-link></li>
            <template v-if="userStore.isLoggedIn">
              <li>
                <button type="button" class="hover:text-white" @click="userStore.logout()">退出登录</button>
              </li>
            </template>
            <template v-else>
              <li><router-link to="/login" class="hover:text-white">登录</router-link></li>
              <li><router-link to="/register" class="hover:text-white">注册</router-link></li>
            </template>
          </ul>
        </div>
        <div>
          <h4 class="mb-3 font-bold text-[#01B4E4]">关于</h4>
          <p class="leading-7 text-white/75">
            FYWZ movies 提供电影检索、数据洞察与智能推荐服务，帮助你更快发现值得观看的影片。
          </p>
        </div>
      </div>

      <p class="mt-10 border-t border-white/10 pt-6 text-center text-xs text-white/50">
        © 2026 FYWZ movies. All rights reserved.
      </p>
    </div>
  </footer>
</template>
