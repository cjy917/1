<!--
  【登录注册·问卷】路由 /
  页面结构（按 pageType 切换）:
    [A1] 登录 / 注册卡片（左侧海报轮播 + 右侧表单）
    [A2] 偏好问卷 · 类型（气泡多选）
    [A2b] 偏好问卷 · 导演
    [A2c] 偏好问卷 · 演员
    [A2d] PreferenceVideoBg.vue — 问卷页视频背景
  代码搜索: handleLogin / handleRegister / handleSave / pageType
  速查索引: src/code-map.js → AUTH_PAGE_MAP (A1~A4)
-->
<template>
  <div class="guide-wrap" :class="{ 'dark-mode': isDark, 'guide-wrap--preference': isPreferencePage }">
    <PreferenceVideoBg v-if="isPreferencePage" />

    <div class="guide-container">
      <template v-if="!pageType.includes('preference')">
        <!-- [A1] 登录 / 注册 -->
        <div class="auth-card">
          <div class="auth-poster">
            <div
              v-for="(slide, index) in posterSlides"
              :key="slide.movieId"
              class="auth-poster__item"
              :class="{ 'is-active': posterIndex === index }"
            >
              <img :src="slide.poster" :alt="slide.title" loading="lazy" />
              <div class="auth-poster__desc">
                <h4>{{ slide.title }}</h4>
                <p v-if="slide.desc">{{ slide.desc }}</p>
              </div>
            </div>
          </div>

          <div class="auth-panel">
            <div v-if="pageType === 'login'">
              <h1 class="page-title">电影系统</h1>
              <p class="page-desc">登录/注册开启个性化电影推荐</p>

              <div class="form-item">
                <label>账号</label>
                <input v-model="account" type="text" placeholder="请输入账号" class="input-box" />
              </div>
              <div class="form-item">
                <label>密码</label>
                <input v-model="password" type="password" placeholder="请输入密码" class="input-box" />
              </div>

              <div class="auth-btn-group">
                <button class="login-btn" @click="handleLogin">登录</button>
                <button class="register-btn" @click="switchToRegister">注册账号</button>
              </div>
            </div>

            <div v-if="pageType === 'register'">
              <h1 class="page-title">新用户注册</h1>
              <p class="page-desc">注册后设置兴趣偏好，获取专属推荐</p>

              <div class="form-item">
                <label>账号</label>
                <input v-model="regAccount" type="text" placeholder="设置账号" class="input-box" />
              </div>
              <div class="form-item">
                <label>密码</label>
                <input v-model="regPwd" type="password" placeholder="设置密码" class="input-box" />
              </div>
              <div class="form-item">
                <label>确认密码</label>
                <input v-model="regPwd2" type="password" placeholder="再次输入密码" class="input-box" />
              </div>

              <div class="auth-btn-group">
                <button class="register-btn" @click="handleRegister">完成注册</button>
                <button class="login-btn" @click="switchToLogin">已有账号？去登录</button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ========== 电影类型偏好选择 ========== -->
      <div v-if="pageType === 'preference'" class="step-panel">
        <button class="skip-btn" @click="handleSkip">跳过</button>
        <h1 class="page-title">选择喜欢的电影分类</h1>
        <p class="page-desc">勾选后首页将优先推送此类影片，可不选</p>

        <div class="bubble-wrap">
          <div
            v-for="(genre, index) in allGenreList"
            :key="genre"
            class="bubble-tag"
            :class="{ active: form.likeGenres.includes(genre) }"
            :style="{
              width: genrePositions[index].size + 'px',
              height: genrePositions[index].size + 'px',
              left: genrePositions[index].x + '%',
              top: genrePositions[index].y + '%',
              animationDelay: genrePositions[index].delay + 's',
              animationDuration: genrePositions[index].duration + 's',
              '--float-offset': genrePositions[index].floatOffset + 'px'
            }"
            @click="toggleGenre(genre)"
          >
            {{ genre }}
          </div>
        </div>

        <div class="btn-row">
          <button class="clear-btn" @click="form.likeGenres = []">清空选择</button>
          <button class="save-btn" @click="goToDirectorPreference">下一步：选择导演</button>
        </div>
      </div>

      <!-- ========== 导演偏好选择 ========== -->
      <div v-if="pageType === 'preference_director'" class="step-panel">
        <button class="skip-btn" @click="handleSkip">跳过</button>
        <h1 class="page-title">选择喜欢的导演</h1>
        <p class="page-desc">勾选后首页将优先推荐该导演的作品，可不选</p>

        <div class="bubble-wrap">
          <div
            v-for="(director, index) in directorList"
            :key="director.name"
            class="bubble-tag"
            :class="{ active: form.likeDirectors.includes(director.name) }"
            :style="{
              width: directorPositions[index].size + 'px',
              height: directorPositions[index].size + 'px',
              left: directorPositions[index].x + '%',
              top: directorPositions[index].y + '%',
              animationDelay: directorPositions[index].delay + 's',
              animationDuration: directorPositions[index].duration + 's',
              '--float-offset': directorPositions[index].floatOffset + 'px'
            }"
            @click="toggleDirector(director.name)"
          >
            {{ director.name }}
          </div>
        </div>

        <div class="btn-row">
          <button class="clear-btn" @click="goBackToGenre">返回上一步</button>
          <button class="save-btn" @click="goToActorPreference">下一步：选择演员</button>
        </div>
      </div>

      <!-- ========== 演员偏好选择 ========== -->
      <div v-if="pageType === 'preference_actor'" class="step-panel">
        <button class="skip-btn" @click="handleSkip">跳过</button>
        <h1 class="page-title">选择喜欢的演员</h1>
        <p class="page-desc">勾选后首页将优先推荐该演员参演的影片，可不选</p>

        <div class="bubble-wrap">
          <div
            v-for="(actor, index) in actorList"
            :key="actor.name"
            class="bubble-tag"
            :class="{ active: form.likeActors.includes(actor.name) }"
            :style="{
              width: actorPositions[index].size + 'px',
              height: actorPositions[index].size + 'px',
              left: actorPositions[index].x + '%',
              top: actorPositions[index].y + '%',
              animationDelay: actorPositions[index].delay + 's',
              animationDuration: actorPositions[index].duration + 's',
              '--float-offset': actorPositions[index].floatOffset + 'px'
            }"
            @click="toggleActor(actor.name)"
          >
            {{ actor.name }}
          </div>
        </div>

        <div class="btn-row">
          <button class="clear-btn" @click="goBackToDirector">返回上一步</button>
          <button class="save-btn" @click="handleSave">保存偏好，进入首页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 【登录注册·问卷】AuthView 逻辑
 * - handleLogin / handleRegister → userStore → authApi
 * - 注册成功后 pageType → preference 三步问卷
 * - savePreference → localStorage + 跳转 /home
 */
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { useThemeStore } from '../stores/theme'
import { movieApi, preferenceApi } from '../api'
import { FALLBACK_ACTORS, FALLBACK_DIRECTORS } from '../utils/preferenceFallback'
import PreferenceVideoBg from '../components/PreferenceVideoBg.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.isDark)
const isPreferencePage = computed(() => pageType.value.includes('preference'))

// ─── 页面状态 ───────────────────────────────────────────────────────────────
// pageType: login | register | preference | preference_director | preference_actor
const pageType = ref('login')

function syncAuthModeFromRoute() {
  if (pageType.value.includes('preference')) return
  pageType.value = route.query.mode === 'register' ? 'register' : 'login'
}

const posterIndex = ref(0)
const posterSlides = ref([])

// ─── [A1] 登录卡片左侧海报轮播 ───────────────────────────────────────────────
async function loadPosterSlides() {
  try {
    const { data } = await movieApi.home()
    const banner = (data.banner || []).filter((movie) => movie.movie_id)
    posterSlides.value = banner.slice(0, 5).map((movie) => ({
      movieId: movie.movie_id,
      title: movie.title,
      desc: movie.rating ? `评分 ${movie.rating}` : '',
      poster: movie.poster_url || `/api/posters/${movie.movie_id}`,
    }))
  } catch {
    posterSlides.value = []
  }
}

let posterTimer = null

function startPosterTimer() {
  posterTimer = setInterval(() => {
    if (posterSlides.value.length <= 1) return
    posterIndex.value = (posterIndex.value + 1) % posterSlides.value.length
  }, 4000)
}

function stopPosterTimer() {
  if (posterTimer) {
    clearInterval(posterTimer)
    posterTimer = null
  }
}

onMounted(async () => {
  syncAuthModeFromRoute()
  await loadPosterSlides()
  if (!pageType.value.includes('preference')) {
    startPosterTimer()
  }
})

watch(
  () => route.query.mode,
  () => syncAuthModeFromRoute(),
)

onBeforeUnmount(() => {
  stopPosterTimer()
})

// ─── [A1] 登录 / 注册表单 ───────────────────────────────────────────────────
const account = ref('')
const password = ref('')

const regAccount = ref('')
const regPwd = ref('')
const regPwd2 = ref('')

// ─── [A2] 问卷 · 类型 / 导演 / 演员气泡 ─────────────────────────────────────
const allGenreList = [
  '剧情','喜剧','惊悚','动作','恐怖','爱情','犯罪','动画',
  '冒险','悬疑','奇幻','科幻','家庭','历史','音乐','战争',
  '纪录','电视电影','同性','传记','歌舞','西部','古装',
  '真人秀','儿童','运动','灾难','武侠','脱口秀','情色','戏曲'
]

// 气泡随机布局（类型 / 导演 / 演员共用）
function genNonOverlappingBubbles(count) {
  const positions = []
  const existing = []
  const containerWidth = 1200
  const containerHeight = 500
  
  for (let i = 0; i < count; i++) {
    let attempts = 0
    let valid = false
    
    while (!valid && attempts < 500) {
      attempts++
      
      const size = Math.random() < 0.15 ? 110 + Math.floor(Math.random() * 40) :
                   Math.random() < 0.35 ? 80 + Math.floor(Math.random() * 30) :
                   Math.random() < 0.65 ? 60 + Math.floor(Math.random() * 25) :
                   50 + Math.floor(Math.random() * 15)
      
      const padding = size / 2 + 10
      const x = padding + Math.random() * (containerWidth - padding * 2)
      const y = padding + Math.random() * (containerHeight - padding * 2)
      
      let overlap = false
      for (const pos of existing) {
        const dx = x - pos.x
        const dy = y - pos.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        const minDist = (size + pos.size) / 2 + 8
        
        if (distance < minDist) {
          overlap = true
          break
        }
      }
      
      if (!overlap) {
        valid = true
        existing.push({ x, y, size })
        positions.push({
          size,
          x: (x / containerWidth) * 100,
          y: (y / containerHeight) * 100,
          delay: Math.random() * 3,
          duration: 4 + Math.random() * 3,
          floatOffset: 5 + Math.random() * 10
        })
      }
    }
    
    if (!valid) {
      const size = 55 + Math.floor(Math.random() * 20)
      const padding = size / 2 + 10
      positions.push({
        size,
        x: (padding + Math.random() * (containerWidth - padding * 2)) / containerWidth * 100,
        y: (padding + Math.random() * (containerHeight - padding * 2)) / containerHeight * 100,
        delay: Math.random() * 3,
        duration: 4 + Math.random() * 3,
        floatOffset: 5 + Math.random() * 10
      })
    }
  }
  
  return positions
}

const genrePositions = genNonOverlappingBubbles(allGenreList.length)

const directorList = ref([])
const directorPositions = ref([])
const actorList = ref([])
const actorPositions = ref([])

const form = reactive({
  likeGenres: [...userStore.preference.likeGenres],
  likeDirectors: [],
  likeActors: [],
})

/** 【API·问卷】GET /api/preferences/directors */
const fetchDirectors = async () => {
  try {
    const { data } = await preferenceApi.directors()
    directorList.value = data.items?.length ? data.items : FALLBACK_DIRECTORS
  } catch {
    ElMessage.warning('导演列表加载失败，已显示默认选项')
    directorList.value = FALLBACK_DIRECTORS
  }
  directorPositions.value = genNonOverlappingBubbles(directorList.value.length)
}

/** 【API·问卷】GET /api/preferences/actors */
const fetchActors = async () => {
  try {
    const { data } = await preferenceApi.actors()
    actorList.value = data.items?.length ? data.items : FALLBACK_ACTORS
  } catch {
    ElMessage.warning('演员列表加载失败，已显示默认选项')
    actorList.value = FALLBACK_ACTORS
  }
  actorPositions.value = genNonOverlappingBubbles(actorList.value.length)
}

const toggleGenre = (name) => {
  const index = form.likeGenres.indexOf(name)
  if (index > -1) form.likeGenres.splice(index, 1)
  else form.likeGenres.push(name)
}

const toggleDirector = (name) => {
  const index = form.likeDirectors.indexOf(name)
  if (index > -1) form.likeDirectors.splice(index, 1)
  else form.likeDirectors.push(name)
}

const toggleActor = (name) => {
  const index = form.likeActors.indexOf(name)
  if (index > -1) form.likeActors.splice(index, 1)
  else form.likeActors.push(name)
}

// ─── 页面切换 / 提交 ───────────────────────────────────────────────────────
const switchToLogin = () => {
  pageType.value = 'login'
  router.replace({ path: '/', query: {} })
}
const switchToRegister = () => {
  pageType.value = 'register'
  router.replace({ path: '/', query: { mode: 'register' } })
}

const goToDirectorPreference = async () => {
  await fetchDirectors()
  pageType.value = 'preference_director'
}

const goBackToGenre = () => {
  pageType.value = 'preference'
}

const goToActorPreference = async () => {
  await fetchActors()
  pageType.value = 'preference_actor'
}

const goBackToDirector = () => {
  pageType.value = 'preference_director'
}

/** 跳过问卷，保存当前选择并进入首页 */
const handleSkip = () => {
  userStore.savePreference(form)
  router.push('/home')
}

/** 【API·A1】POST /api/auth/login */
const handleLogin = async () => {
  if (!account.value || !password.value) {
    ElMessage.warning('账号密码不能为空')
    return
  }
  try {
    await userStore.login({ username: account.value, password: password.value })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect
    router.push(typeof redirect === 'string' ? redirect : '/home')
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '登录失败')
  }
}

/** 【API·A1】POST /api/auth/register → 进入问卷 */
const handleRegister = async () => {
  if (!regAccount.value || !regPwd.value || !regPwd2.value) {
    ElMessage.warning('表单不能为空')
    return
  }
  if (regPwd.value !== regPwd2.value) {
    ElMessage.warning('两次密码不一致')
    return
  }
  if (regPwd.value.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  try {
    await userStore.register({
      username: regAccount.value,
      email: `${regAccount.value}@fywz.local`,
      password: regPwd.value,
    })
    ElMessage.success('注册成功')
    form.likeGenres = []
    form.likeDirectors = []
    form.likeActors = []
    stopPosterTimer()
    pageType.value = 'preference'
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '注册失败')
  }
}

/** 问卷完成：savePreference → /home */
const handleSave = () => {
  userStore.savePreference(form)
  router.push('/home')
}
</script>

<style scoped>
/* 【登录注册·问卷】AuthView 样式 — 明暗主题变量 + 气泡问卷 */
.guide-wrap {
  --text-normal: #111111;
  --text-muted: #666666;
  --tag-bg: #ffffff;
  --tag-border: #dddddd;
  --btn-clear-border: #dddddd;
  --btn-clear-bg: transparent;
  --btn-clear-text: #666666;

  position: relative;
  min-height: 100vh;
  padding: 14px 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

/* 深色模式变量覆盖 */
.guide-wrap.dark-mode {
  --text-normal: #ffffff;
  --text-muted: #bbbbbb;
  --tag-bg: #1e293b;
  --tag-border: #475569;
  --btn-clear-border: #475569;
  --btn-clear-bg: #1e293b;
  --btn-clear-text: #dddddd;

  background: #0f172a;
}

.guide-wrap--preference {
  background: #ffffff;
}

.guide-wrap--preference .guide-container {
  position: relative;
  z-index: 1;
}

.guide-container {
  max-width: 720px;
  margin: 0 auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  position: relative;
}

.page-title {
  font-size: 22px;
  margin: 0 0 4px;
  color: var(--text-normal);
  text-align: center;
}

.page-desc {
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 16px;
  text-align: center;
}

/* 认证卡片布局 */
.auth-card {
  display: flex;
  flex-direction: row;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.guide-wrap.dark-mode .auth-card {
  background: rgba(30, 41, 59, 0.9);
}

/* 左侧海报轮播区 */
.auth-poster {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-width: 350px;
}

.auth-poster__item {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.5s ease-in-out;
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
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
  color: #fff;
}

.auth-poster__desc h4 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
}

.auth-poster__desc p {
  margin: 0;
  font-size: 14px;
  opacity: 0.85;
}

/* 登录注册表单样式 */
.auth-panel {
  flex: 1;
  padding: 40px;
  display: flex;
  flex-direction: column;
  max-width: 450px;
}

.form-item {
  margin-bottom: 18px;
}

.form-item label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-normal);
}

.input-box {
  width: 100%;
  box-sizing: border-box;
  height: 46px;
  border-radius: 24px;
  border: 1px solid var(--tag-border);
  background: var(--tag-bg);
  color: var(--text-normal);
  padding: 0 20px;
  font-size: 15px;
  outline: none;
}

.auth-btn-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 25px;
}

.login-btn {
  height: 46px;
  border-radius: 25px;
  border: 1px solid var(--btn-clear-border);
  background: var(--btn-clear-bg);
  color: var(--btn-clear-text);
  font-size: 16px;
  cursor: pointer;
}

.register-btn {
  height: 46px;
  border-radius: 25px;
  border: none;
  background: #00b4e5;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
}

.skip-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 16px;
  transition: all 0.2s;
}

.skip-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-normal);
}

.guide-wrap.dark-mode .skip-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.step-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.bubble-wrap {
  flex: 1;
  padding: 10px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
  min-height: 400px;
}

.bubble-tag {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.85) 0%, rgba(255, 255, 255, 0.6) 100%);
  color: var(--text-normal);
  text-align: center;
  font-size: 12px;
  cursor: pointer;
  animation: floatUpDown ease-in-out infinite;
  user-select: none;
  padding: 2px 6px;
  word-break: keep-all;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  font-weight: 500;
  letter-spacing: 0.3px;
  box-shadow: 
    0 4px 15px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transform: translate(-50%, -50%);
}

.guide-wrap.dark-mode .bubble-tag {
  border-color: rgba(255, 255, 255, 0.15);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.7) 100%);
  box-shadow:
    0 4px 15px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.bubble-tag:hover {
  transform: translate(-50%, -50%) scale(1.12);
  z-index: 10;
  box-shadow: 
    0 8px 25px rgba(0, 180, 229, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.guide-wrap.dark-mode .bubble-tag:hover {
  box-shadow:
    0 8px 25px rgba(0, 180, 229, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

@keyframes floatUpDown {
  0% { 
    transform: translate(-50%, -50%) translateY(0px) scale(1); 
  }
  50% { 
    transform: translate(-50%, -50%) translateY(calc(-8px - var(--float-offset, 0px))) scale(1.02); 
  }
  100% { 
    transform: translate(-50%, -50%) translateY(0px) scale(1); 
  }
}

.bubble-tag.active {
  background: linear-gradient(135deg, #00b4e5 0%, #0086b3 100%) !important;
  border-color: #00b4e5 !important;
  color: #ffffff !important;
  font-weight: 600;
  box-shadow: 
    0 0 30px rgba(0, 180, 229, 0.6),
    0 8px 25px rgba(0, 180, 229, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
  transform: translate(-50%, -50%) scale(1.08);
  animation: floatUpDownActive ease-in-out infinite;
}

.guide-wrap.dark-mode .bubble-tag.active {
  box-shadow:
    0 0 40px rgba(0, 180, 229, 0.7),
    0 8px 30px rgba(0, 180, 229, 0.5),
    0 0 1px 1px rgba(0, 180, 229, 0.9),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

@keyframes floatUpDownActive {
  0% { 
    transform: translate(-50%, -50%) translateY(0px) scale(1.08); 
  }
  50% { 
    transform: translate(-50%, -50%) translateY(calc(-10px - var(--float-offset, 0px))) scale(1.1); 
  }
  100% { 
    transform: translate(-50%, -50%) translateY(0px) scale(1.08); 
  }
}

.btn-row {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
  padding-bottom: 2px;
}

.clear-btn {
  flex: 1;
  height: 46px;
  border-radius: 25px;
  border: 1px solid var(--btn-clear-border);
  background: var(--btn-clear-bg);
  color: var(--btn-clear-text);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.guide-wrap.dark-mode .clear-btn:hover {
  background: rgba(255, 255, 255, 0.08);
}

.save-btn {
  flex: 2;
  height: 46px;
  border-radius: 25px;
  border: none;
  background: #00b4e5;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.save-btn:hover {
  background: #009dc9;
}
</style>