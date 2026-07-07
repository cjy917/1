/**
 * 【详情页 D2】慢加载兜底 UI
 * 播放器/预告加载超过 delayMs 仍无响应 → showFallback=true，显示「重新加载」等按钮
 * 用于 02-DetailPlayerSection
 */
import { ref } from 'vue'

export function useDelayedFallback(delayMs) {
  const showFallback = ref(false)
  let timer = null

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  /** 开始计时；isLoading 为函数，超时时刻仍为 true 才显示 fallback */
  function start(isLoading) {
    clearTimer()
    showFallback.value = false
    timer = setTimeout(() => {
      if (isLoading()) {
        showFallback.value = true
      }
    }, delayMs)
  }

  /** 加载完成或切换 tab 时重置 */
  function reset() {
    clearTimer()
    showFallback.value = false
  }

  return { showFallback, start, reset }
}
