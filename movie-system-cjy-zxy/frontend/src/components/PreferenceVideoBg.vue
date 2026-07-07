<!--
  【问卷·背景】PreferenceVideoBg
  挂载位置: AuthView.vue（pageType 含 preference 时）
  资源: public/sp/questionnaire-bg.mp4
  处理: Canvas 将蓝色背景转为白底，角色为深灰剪影；截断末尾黑场循环
  速查索引: src/code-map.js → AUTH_PAGE_MAP (A4)
-->
<template>  <div class="preference-video-bg" aria-hidden="true">
    <video
      ref="videoEl"
      class="preference-video-bg__source"
      src="/sp/questionnaire-bg.mp4"
      loop
      playsinline
      preload="auto"
    />
    <canvas ref="canvasEl"></canvas>
    <div class="preference-video-bg__scrim"></div>
    <div class="preference-video-bg__corner-cover"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const videoEl = ref(null)
const canvasEl = ref(null)

/** 原视频蓝色背景采样值 (RGB)，用于 Canvas 抠图 */
const BG_R = 13
const BG_G = 69
const BG_B = 113
const BG_DIST = 45
const DARK_LUM = 55
const CHAR_R = 52
const CHAR_G = 56
const CHAR_B = 66
const LOOP_TAIL_TRIM = 2.95
const VIDEO_VOLUME = 0.65

let rafId = null
let width = 0
let height = 0
let loopEndSec = null
let ctx = null
let onTimeUpdate = null
let onEnded = null
let onUnlockAudio = null

async function enableAudio() {
  const video = videoEl.value
  if (!video) return false

  video.volume = VIDEO_VOLUME
  video.muted = false

  try {
    await video.play()
    return true
  } catch {
    video.muted = true
    try {
      await video.play()
    } catch {
      /* ignore */
    }
    return false
  }
}

function setupAudioUnlock() {
  if (onUnlockAudio) return

  onUnlockAudio = async () => {
    const video = videoEl.value
    if (!video || !video.muted) return

    video.muted = false
    video.volume = VIDEO_VOLUME
    try {
      await video.play()
    } catch {
      /* ignore */
    }

    document.removeEventListener('pointerdown', onUnlockAudio)
    onUnlockAudio = null
  }

  document.addEventListener('pointerdown', onUnlockAudio, { once: true })
}

function processFrame() {
  const imageData = ctx.getImageData(0, 0, width, height)
  const d = imageData.data

  for (let i = 0; i < d.length; i += 4) {
    const r = d[i]
    const g = d[i + 1]
    const b = d[i + 2]
    const dr = r - BG_R
    const dg = g - BG_G
    const db = b - BG_B
    const dist = Math.sqrt(dr * dr + dg * dg + db * db)
    const lum = 0.299 * r + 0.587 * g + 0.114 * b

    if (dist < BG_DIST || lum < DARK_LUM) {
      d[i] = 255
      d[i + 1] = 255
      d[i + 2] = 255
    } else {
      d[i] = CHAR_R
      d[i + 1] = CHAR_G
      d[i + 2] = CHAR_B
    }
  }

  ctx.putImageData(imageData, 0, 0)
}

function restartLoop() {
  const video = videoEl.value
  if (!video) return
  video.currentTime = 0.001
  video.play().catch(() => {})
}

/** 在末尾黑场前 LOOP_TAIL_TRIM 秒跳回开头，避免循环闪黑 */
function setupLoop(video) {
  loopEndSec = Math.max(0.5, video.duration - LOOP_TAIL_TRIM)

  onTimeUpdate = () => {
    if (loopEndSec != null && video.currentTime >= loopEndSec) {
      restartLoop()
    }
  }

  onEnded = () => {
    restartLoop()
  }

  video.addEventListener('timeupdate', onTimeUpdate)
  video.addEventListener('ended', onEnded)
}

/** requestAnimationFrame 循环：video → canvas → processFrame 抠图 */
function render() {
  const video = videoEl.value
  const canvas = canvasEl.value
  if (!video || !canvas || !ctx || video.readyState < 2) {
    rafId = requestAnimationFrame(render)
    return
  }

  ctx.drawImage(video, 0, 0, width, height)
  processFrame()

  rafId = requestAnimationFrame(render)
}

/** 全屏 canvas 尺寸跟随窗口 */
function resize() {
  const canvas = canvasEl.value
  if (!canvas) return
  width = window.innerWidth
  height = window.innerHeight
  canvas.width = width
  canvas.height = height
  ctx = canvas.getContext('2d', { willReadFrequently: true })
}

// ─── 生命周期：初始化 Canvas 渲染环 + 音频策略 ─────────────────────────────
onMounted(async () => {
  resize()
  window.addEventListener('resize', resize)

  const video = videoEl.value
  if (!video) return

  video.addEventListener('loadedmetadata', () => {
    setupLoop(video)
  })

  video.addEventListener('loadeddata', () => {
    enableAudio()
  })

  if (video.readyState >= 1) {
    setupLoop(video)
  }

  const audioStarted = await enableAudio()
  if (!audioStarted) {
    setupAudioUnlock()
  }

  rafId = requestAnimationFrame(render)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (rafId) cancelAnimationFrame(rafId)
  if (onUnlockAudio) {
    document.removeEventListener('pointerdown', onUnlockAudio)
    onUnlockAudio = null
  }

  const video = videoEl.value
  if (video) {
    if (onTimeUpdate) video.removeEventListener('timeupdate', onTimeUpdate)
    if (onEnded) video.removeEventListener('ended', onEnded)
    video.pause()
  }
})
</script>

<style scoped>
/* 固定全屏底层；video 隐藏，仅 canvas 可见 */
.preference-video-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: #ffffff;
}

.preference-video-bg__source {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.preference-video-bg canvas {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preference-video-bg__scrim {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 70% 58%, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.12) 55%, transparent 100%);
}

/* 右上角白块：遮盖原视频水印区域 */
.preference-video-bg__corner-cover {
  position: absolute;
  top: 0;
  right: 0;
  width: min(360px, 42vw);
  height: min(150px, 20vh);
  background: #ffffff;
}
</style>
