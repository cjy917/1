<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { useThemeStore } from '../stores/theme'
import ThemeToggle from '../components/ThemeToggle.vue'
import { movieApi } from '../api'

const SLIDE_INTERVAL_MS = 2500

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()

const loading = ref(false)
const errorMsg = ref('')
const posterIndex = ref(0)
let slideTimer = null

const posterSlides = ref([])

const activeTab = ref(route.name === 'register' ? 'register' : 'login')

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', repwd: '' })

const navItems = [
  { label: '电影', to: '/movies' },
  { label: '数据分析', to: '/analytics' },
  { label: '推荐', to: '/recommend' },
]

function posterUrl(slide) {
  return slide.poster || `/api/posters/${slide.movieId}`
}

async function loadPosterSlides() {
  try {
    const { data } = await movieApi.home()
    const banner = (data.banner || []).filter((movie) => movie.movie_id)
    posterSlides.value = banner.slice(0, 6).map((movie) => ({
      movieId: movie.movie_id,
      title: movie.title,
      desc: movie.rating ? `评分 ${movie.rating}` : '',
      poster: movie.poster_url || `/api/posters/${movie.movie_id}`,
    }))
  } catch {
    posterSlides.value = []
  }
}

function stopSlide() {
  if (slideTimer) {
    clearInterval(slideTimer)
    slideTimer = null
  }
}

function startSlide() {
  stopSlide()
  if (posterSlides.value.length <= 1) return
  slideTimer = setInterval(() => {
    posterIndex.value = (posterIndex.value + 1) % posterSlides.value.length
  }, SLIDE_INTERVAL_MS)
}

function switchTab(tab) {
  activeTab.value = tab
  errorMsg.value = ''
  router.replace({ name: tab === 'register' ? 'register' : 'login', query: route.query })
}

async function submitLogin() {
  loading.value = true
  errorMsg.value = ''
  try {
    await userStore.login(loginForm)
    ElMessage.success('登录成功')
    router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (e) {
    errorMsg.value = e.response?.data?.error || '登录失败'
  } finally {
    loading.value = false
  }
}

async function submitRegister() {
  if (registerForm.password !== registerForm.repwd) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await userStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
    })
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
    errorMsg.value = e.response?.data?.error || '注册失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => route.name,
  (name) => {
    activeTab.value = name === 'register' ? 'register' : 'login'
  },
)

const isDark = computed(() => themeStore.isDark)

onMounted(async () => {
  await loadPosterSlides()
  startSlide()
})

onBeforeUnmount(() => {
  stopSlide()
})
</script>

<template>
  <div class="auth-page" :class="{ 'auth-page--dark': isDark }">
    <nav class="auth-nav">
      <div class="auth-nav__left">
        <router-link to="/" class="auth-brand">
          FYWZ <span>movies</span>
        </router-link>
        <div class="auth-nav__menu">
          <router-link v-for="item in navItems" :key="item.to" :to="item.to">
            {{ item.label }}
          </router-link>
        </div>
      </div>
      <div class="auth-nav__right">
        <ThemeToggle />
        <button type="button" class="auth-nav__link" @click="switchTab('login')">登录</button>
        <button type="button" class="auth-nav__link" @click="switchTab('register')">注册</button>
      </div>
    </nav>

    <div class="auth-wrap">
      <div class="auth-card">
        <div class="auth-poster">
          <div
            v-for="(slide, index) in posterSlides"
            :key="slide.movieId"
            class="auth-poster__item"
            :class="{ 'is-active': posterIndex === index }"
          >
            <img :src="posterUrl(slide)" :alt="slide.title" loading="lazy" />
            <div class="auth-poster__desc">
              <h4>{{ slide.title }}</h4>
              <p v-if="slide.desc">{{ slide.desc }}</p>
            </div>
          </div>
        </div>

        <div class="auth-panel">
          <div class="auth-tabs">
            <button
              type="button"
              class="auth-tabs__item"
              :class="{ 'is-active': activeTab === 'login' }"
              @click="switchTab('login')"
            >
              登录
            </button>
            <button
              type="button"
              class="auth-tabs__item"
              :class="{ 'is-active': activeTab === 'register' }"
              @click="switchTab('register')"
            >
              注册
            </button>
          </div>

          <div class="auth-form-wrap">
            <div v-if="errorMsg" class="auth-alert">{{ errorMsg }}</div>

            <form v-show="activeTab === 'login'" class="auth-form" @submit.prevent="submitLogin">
              <div class="auth-field">
                <label>用户名</label>
                <input
                  v-model="loginForm.username"
                  type="text"
                  placeholder="请输入用户名"
                  required
                  autocomplete="username"
                />
              </div>
              <div class="auth-field auth-field--lg">
                <label>密码</label>
                <input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  required
                  autocomplete="current-password"
                />
              </div>
              <button type="submit" class="auth-submit" :disabled="loading">
                {{ loading ? '登录中…' : '登录' }}
              </button>
              <p class="auth-tip">
                还没有账号？
                <button type="button" @click="switchTab('register')">立即注册</button>
              </p>
            </form>

            <form v-show="activeTab === 'register'" class="auth-form" @submit.prevent="submitRegister">
              <div class="auth-field">
                <label>设置用户名</label>
                <input
                  v-model="registerForm.username"
                  type="text"
                  placeholder="自定义账号"
                  required
                  autocomplete="username"
                />
              </div>
              <div class="auth-field">
                <label>邮箱</label>
                <input
                  v-model="registerForm.email"
                  type="email"
                  placeholder="用于找回账号与通知"
                  required
                  autocomplete="email"
                />
              </div>
              <div class="auth-field">
                <label>设置密码</label>
                <input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="6位以上密码"
                  required
                  minlength="6"
                  autocomplete="new-password"
                />
              </div>
              <div class="auth-field auth-field--lg">
                <label>确认密码</label>
                <input
                  v-model="registerForm.repwd"
                  type="password"
                  placeholder="再次输入密码"
                  required
                  minlength="6"
                  autocomplete="new-password"
                />
              </div>
              <button type="submit" class="auth-submit" :disabled="loading">
                {{ loading ? '注册中…' : '完成注册' }}
              </button>
              <p class="auth-tip">
                已有账号？
                <button type="button" @click="switchTab('login')">去登录</button>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa, #eef2f7);
  color: #000;
}

.auth-page--dark {
  background: linear-gradient(135deg, #12141d, #1c2030);
  color: #fff;
}

.auth-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
  background: #0a3452;
  color: #fff;
}

.auth-nav__left {
  display: flex;
  align-items: center;
  gap: 28px;
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
}

.auth-brand span::before {
  content: '●';
  color: #36d1f5;
  margin-right: 4px;
}

.auth-nav__menu {
  display: flex;
  gap: 8px;
}

.auth-nav__menu a {
  color: #fff;
  text-decoration: none;
  margin: 0 10px;
  font-size: 16px;
  opacity: 0.85;
}

.auth-nav__menu a:hover {
  opacity: 1;
}

.auth-nav__right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.auth-nav__link {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 16px;
  opacity: 0.85;
  cursor: pointer;
}

.auth-nav__link:hover {
  opacity: 1;
}

.auth-wrap {
  min-height: calc(100vh - 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.auth-card {
  display: flex;
  width: min(920px, 100%);
  height: 560px;
  background: var(--fywz-surface, #fff);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}

.auth-page--dark .auth-card {
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
}

.auth-poster {
  position: relative;
  width: 50%;
  background: #000;
  overflow: hidden;
}

.auth-poster__item {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.7s ease-in-out;
}

.auth-poster__item.is-active {
  opacity: 1;
}

.auth-poster__item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.auth-poster__desc {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  padding: 25px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.85));
  color: #fff;
}

.auth-poster__desc h4 {
  margin: 0 0 6px;
  font-size: 1.25rem;
}

.auth-poster__desc p {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.9;
}

.auth-panel {
  width: 50%;
  display: flex;
  flex-direction: column;
  background: var(--fywz-surface, #fff);
}

.auth-tabs {
  display: flex;
  border-bottom: 1px solid var(--fywz-border, #eee);
}

.auth-tabs__item {
  flex: 1;
  padding: 18px 0;
  border: none;
  background: transparent;
  font-size: 18px;
  color: var(--fywz-text-muted, #666);
  cursor: pointer;
  position: relative;
}

.auth-tabs__item.is-active {
  color: #00b4e5;
  font-weight: 500;
}

.auth-tabs__item.is-active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 25%;
  width: 50%;
  height: 3px;
  background: #00b4e5;
}

.auth-form-wrap {
  flex: 1;
  padding: 35px;
  overflow-y: auto;
}

.auth-alert {
  margin-bottom: 18px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(245, 108, 108, 0.12);
  color: #e74c3c;
  font-size: 14px;
  text-align: center;
}

.auth-field {
  margin-bottom: 18px;
}

.auth-field--lg {
  margin-bottom: 24px;
}

.auth-field label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--fywz-text, #000);
}

.auth-field input {
  width: 100%;
  height: 48px;
  padding: 0 14px;
  border: 1px solid var(--fywz-border, #eee);
  border-radius: 8px;
  font-size: 15px;
  background: var(--fywz-bg, #fff);
  color: var(--fywz-text, #000);
  outline: none;
}

.auth-field input:focus {
  border-color: #00b4e5;
}

.auth-submit {
  width: 100%;
  height: 50px;
  border: none;
  border-radius: 25px;
  background: #00b4e5;
  color: #fff;
  font-size: 17px;
  font-weight: 500;
  cursor: pointer;
}

.auth-submit:hover:not(:disabled) {
  background: #009dc9;
}

.auth-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.auth-tip {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  color: var(--fywz-text-muted, #666);
}

.auth-tip button {
  border: none;
  background: transparent;
  color: #00b4e5;
  cursor: pointer;
  font-size: inherit;
}

@media (max-width: 768px) {
  .auth-nav__menu {
    display: none;
  }

  .auth-card {
    flex-direction: column;
    height: auto;
  }

  .auth-poster,
  .auth-panel {
    width: 100%;
  }

  .auth-poster {
    height: 220px;
  }
}
</style>
