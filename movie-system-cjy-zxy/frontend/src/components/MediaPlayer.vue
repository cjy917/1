<!--
  【首页 H2b / 详情 D2】统一媒体播放器
  支持：本地 mp4、YouTube/Bilibili iframe
  模式：heroMode（首页轮播）、cardMode（卡片悬停）、controls（详情正片）
-->
<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { resolveMediaUrl } from '../utils/mediaUrl'
import PlaybackFallbackButton from './PlaybackFallbackButton.vue'

// ─── Props：source 来自 trailer/play API 返回的 { type, embed_url, stream_url } ─
const props = defineProps({
  source: { type: Object, default: null },
  autoplay: { type: Boolean, default: false },
  muted: { type: Boolean, default: true },
  loop: { type: Boolean, default: false },
  cover: { type: Boolean, default: true },
  controls: { type: Boolean, default: false },
  playCheckMs: { type: Number, default: 3000 },
  fallbackLabel: { type: String, default: '查看详情' },
  enableFallback: { type: Boolean, default: true },
  heroMode: { type: Boolean, default: false },
  cardMode: { type: Boolean, default: false },
  preload: { type: String, default: '' },
  paused: { type: Boolean, default: false },
})

const emit = defineEmits(['open-detail', 'playback-confirmed', 'playback-failed'])

const videoRef = ref(null)
const showFallback = ref(false)      // 超时未播放 → 显示兜底按钮
const playingConfirmed = ref(false)
let checkTimer = null                // mp4 播放检测
let iframeConfirmTimer = null        // iframe 加载检测

function clearIframeConfirmTimer() {
  if (iframeConfirmTimer) {
    clearTimeout(iframeConfirmTimer)
    iframeConfirmTimer = null
  }
}

const hasSource = computed(() => {
  const s = props.source
  return s && s.type !== 'none' && (s.embed_url || s.stream_url)
})

const isMp4 = computed(() => props.source?.type === 'mp4')
const isIframe = computed(() => ['youtube', 'bilibili'].includes(props.source?.type))

const mp4Src = computed(() => resolveMediaUrl(props.source?.embed_url || props.source?.stream_url || ''))

const videoPreload = computed(() => {
  if (props.preload) return props.preload
  if (props.controls && !props.heroMode && !props.cardMode) return 'metadata'
  return 'auto'
})

const iframeSrc = computed(() => {
  if (!props.source?.embed_url) return ''
  let url = props.source.embed_url
  const muteFlag = props.muted ? 1 : 0
  if (props.autoplay && props.source.type === 'youtube') {
    const join = url.includes('?') ? '&' : '?'
    const heroExtras = props.heroMode
      ? '&iv_load_policy=3&disablekb=1&fs=0&cc_load_policy=0'
      : ''
    const ctrl = props.controls ? 1 : 0
    if (!url.includes('autoplay=1')) {
      url = `${url}${join}autoplay=1&mute=${muteFlag}&controls=${ctrl}&rel=0&modestbranding=1&playsinline=1${heroExtras}`
    } else {
      url = url.replace(/([?&]mute=)\d+/, `$1${muteFlag}`)
      if (!/[?&]mute=/.test(url)) {
        url = `${url}&mute=${muteFlag}`
      }
      if (props.heroMode && !url.includes('iv_load_policy=3')) {
        url = `${url}${heroExtras}`
      }
    }
  }
  if (props.autoplay && props.source.type === 'bilibili') {
    const join = url.includes('?') ? '&' : '?'
    if (!url.includes('autoplay=1')) {
      url = `${url}${join}autoplay=1&muted=${muteFlag}`
    } else {
      url = url.replace(/([?&]muted=)\d+/, `$1${muteFlag}`)
      if (!/[?&]muted=/.test(url)) {
        url = `${url}&muted=${muteFlag}`
      }
    }
  }
  return url
})

const activeIframeSrc = computed(() => (props.paused ? '' : iframeSrc.value))

// ─── 播放确认 / 超时 watchdog ─────────────────────────────────────────────────
function clearCheckTimer() {
  if (checkTimer) {
    clearTimeout(checkTimer)
    checkTimer = null
  }
}

function confirmPlaying() {
  if (playingConfirmed.value) return
  playingConfirmed.value = true
  showFallback.value = false
  clearCheckTimer()
  clearIframeConfirmTimer()
  emit('playback-confirmed')
}

function startHeroWatchdog() {
  clearCheckTimer()
  checkTimer = setTimeout(() => {
    if (!playingConfirmed.value) {
      if (props.enableFallback) {
        showFallback.value = true
      } else {
        emit('playback-failed')
      }
    }
  }, props.playCheckMs)
}

function resetPlaybackWatch() {
  playingConfirmed.value = false
  showFallback.value = false
  clearCheckTimer()
  clearIframeConfirmTimer()
  if (!hasSource.value) return
  if (props.heroMode || props.cardMode) {
    startHeroWatchdog()
    return
  }
  if (!props.enableFallback) return
  startHeroWatchdog()
}

function onVideoPlaying() {
  confirmPlaying()
}

function onVideoCanPlay() {
  if (isMp4.value && props.cardMode) {
    confirmPlaying()
  }
}

function onVideoTimeUpdate(event) {
  if (event.target?.currentTime > 0.05) {
    confirmPlaying()
  }
}

function onVideoError() {
  clearCheckTimer()
  clearIframeConfirmTimer()
  if (props.enableFallback) {
    showFallback.value = true
  } else {
    emit('playback-failed')
  }
}

async function pausePlayback() {
  if (videoRef.value) {
    videoRef.value.pause()
  }
}

async function resumePlayback() {
  if (!videoRef.value) return
  if (!props.muted) {
    videoRef.value.muted = false
  }
  try {
    await videoRef.value.play()
  } catch {
    videoRef.value.muted = true
    try {
      await videoRef.value.play()
    } catch {
      emit('playback-failed')
    }
  }
}

defineExpose({ pausePlayback, resumePlayback })

function onIframeLoad() {
  if (!props.autoplay) {
    confirmPlaying()
    return
  }
  if (props.autoplay && isIframe.value && (props.heroMode || props.cardMode)) {
    resetPlaybackWatch()
    iframeConfirmTimer = setTimeout(() => confirmPlaying(), props.cardMode ? 350 : 1000)
  }
}

watch(
  () => props.paused,
  (paused) => {
    if (!isMp4.value || !videoRef.value) return
    if (paused) {
      videoRef.value.pause()
    } else if (props.autoplay) {
      resumePlayback()
    }
  },
)

watch(
  () => props.muted,
  (muted) => {
    if (videoRef.value) {
      videoRef.value.muted = muted
    }
  },
)

watch(
  () => [props.autoplay, props.source?.embed_url, props.source?.type, mp4Src.value, props.muted],
  async () => {
    resetPlaybackWatch()
    if (!props.autoplay || props.paused || !isMp4.value || !videoRef.value) return
    try {
      videoRef.value.muted = props.muted
      videoRef.value.currentTime = 0
      await videoRef.value.play()
    } catch {
      if (!props.muted && videoRef.value) {
        videoRef.value.muted = true
        try {
          await videoRef.value.play()
        } catch {
          clearCheckTimer()
          clearIframeConfirmTimer()
          emit('playback-failed')
          return
        }
      } else {
        clearCheckTimer()
        clearIframeConfirmTimer()
        emit('playback-failed')
      }
    }
  },
)

watch(
  () => [iframeSrc.value, isIframe.value, hasSource.value, props.autoplay],
  () => {
    if (isIframe.value && iframeSrc.value) {
      resetPlaybackWatch()
    }
  },
)

onBeforeUnmount(() => {
  clearCheckTimer()
  clearIframeConfirmTimer()
})
</script>

<template>
  <div
    v-if="hasSource"
    class="media-player"
    :class="{
      'media-player--hero': heroMode,
      'media-player--card': cardMode,
      'media-player--contain': !cover && !heroMode && !cardMode,
    }"
  >
    <video
      v-if="isMp4"
      ref="videoRef"
      :src="mp4Src"
      class="media-video"
      :class="{ 'object-cover': cover, 'object-contain': !cover }"
      :autoplay="autoplay"
      :muted="muted"
      :loop="loop"
      :controls="controls"
      playsinline
      :preload="videoPreload"
      @error="onVideoError"
      @canplay="onVideoCanPlay"
      @playing="onVideoPlaying"
      @timeupdate="onVideoTimeUpdate"
    />
    <div
      v-else-if="isIframe"
      class="media-iframe-shell"
      :class="{
        'media-iframe-shell--hero': heroMode,
        'media-iframe-shell--card': cardMode,
      }"
    >
      <iframe
        :src="activeIframeSrc"
        class="media-iframe"
        :width="heroMode ? 1920 : undefined"
        :height="heroMode ? 1080 : undefined"
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
        allowfullscreen
        tabindex="-1"
        @load="onIframeLoad"
      />
    </div>

    <div v-if="enableFallback && showFallback" class="fallback-overlay">
      <PlaybackFallbackButton :label="fallbackLabel" @click="emit('open-detail')" />
    </div>
  </div>
</template>

<style scoped>
.media-player {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #000;
}

.media-video,
.media-iframe-shell .media-iframe {
  position: absolute;
  top: 50%;
  left: 50%;
  height: 100%;
  width: 100%;
  min-height: 100%;
  min-width: 100%;
  transform: translate(-50%, -50%);
  border: 0;
  object-fit: cover;
}

.media-iframe-shell {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.media-iframe-shell .media-iframe {
  width: 177.78vh;
  min-width: 100%;
}

@media (min-aspect-ratio: 16/9) {
  .media-iframe-shell .media-iframe {
    width: 100%;
    height: 56.25vw;
    min-height: 100%;
  }
}

.media-player--contain .media-video {
  object-fit: contain;
}

.media-player--contain .media-iframe-shell .media-iframe {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  transform: translate(-50%, -50%);
}

.media-player--hero .media-video {
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  min-width: 100%;
  min-height: 100%;
  transform: translate(-50%, -50%);
  object-fit: cover;
  object-position: center 36%;
}

/* 取景偏上保留人物头部；scale 略降减少上下裁切 */
.media-iframe-shell--hero {
  pointer-events: none;
}

.media-player--hero .media-iframe-shell .media-iframe {
  top: 50%;
  left: 50%;
  width: 100vw;
  height: 56.25vw;
  min-width: 177.78vh;
  min-height: 100%;
  transform: translate(-50%, -44%) scale(1.07);
  transform-origin: center center;
  pointer-events: none;
}

.media-player--card {
  pointer-events: none;
}

.media-player--card .media-video {
  object-fit: cover;
  object-position: center 36%;
}

.media-iframe-shell--card {
  pointer-events: none;
}

.media-player--card .media-iframe-shell .media-iframe {
  top: 50%;
  left: 50%;
  width: 220%;
  height: 100%;
  min-width: 100%;
  min-height: 100%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.fallback-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}
</style>
