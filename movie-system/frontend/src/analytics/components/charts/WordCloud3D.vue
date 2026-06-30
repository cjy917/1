<template>
  <div class="wordcloud3d-wrapper">
    <div ref="tagContainer" class="tagcloud-container"></div>
    <div v-if="tooltip.visible" class="wordcloud-tooltip" :style="tooltip.style">
      <span class="tooltip-name">{{ tooltip.name }}</span>
      <span class="tooltip-value">{{ tooltip.value }} 部电影</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import TagCloud from 'TagCloud'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

const tagContainer = ref(null)
const tooltip = ref({ visible: false, name: '', value: 0, style: {} })
let cloudInstance = null

const PALETTE = [
  '#007aff', '#5856d6', '#af52de', '#ff2d55',
  '#ff9500', '#34c759', '#5ac8fa', '#ff6b6b',
  '#7c5cfc', '#00c7be', '#ffd60a', '#64d2ff',
  '#bf5af2', '#30d158', '#ff453a', '#0a84ff'
]

function buildTexts(data) {
  if (!data || data.length === 0) return []
  const maxVal = Math.max(...data.map(d => d.value))
  const minVal = Math.min(...data.map(d => d.value))
  const range = maxVal - minVal || 1
  return data.map((item, i) => {
    const ratio = (item.value - minVal) / range
    const size = 13 + ratio * 22
    const color = PALETTE[i % PALETTE.length]
    const opacity = 0.55 + ratio * 0.45
    return {
      text: item.name,
      value: item.value,
      size,
      color,
      opacity
    }
  })
}

function initCloud(texts) {
  if (!tagContainer.value || texts.length === 0) return

  if (cloudInstance) {
    cloudInstance.destroy()
    cloudInstance = null
  }

  const container = tagContainer.value
  container.innerHTML = ''

  // Pass text strings so TagCloud creates DOM elements, then override styles
  const textStrings = texts.map(t => t.text)
  const radius = Math.min(container.offsetWidth, container.offsetHeight) * 0.38

  cloudInstance = new TagCloud(container, textStrings, {
    radius: radius,
    maxSpeed: 'normal',
    initSpeed: 'normal',
    keep: true,
    direction: 135,
    useContainerInlineStyles: false,
    useItemInlineStyles: false,
    useHTML: false,
    containerClass: 'wordcloud3d',
    itemClass: 'wordcloud3d-item'
  })

  // Apply custom styles to each tag based on frequency data
  const items = container.querySelectorAll('.wordcloud3d-item')
  items.forEach((el, i) => {
    const t = texts[i]
    if (!t) return
    el.style.fontSize = t.size + 'px'
    el.style.color = t.color
    el.style.opacity = t.opacity
    el.style.fontWeight = t.size > 24 ? '700' : '500'
    el.style.fontFamily = "'Noto Sans SC', 'PingFang SC', sans-serif"
    el.style.cursor = 'pointer'
    el.style.transition = 'opacity 0.2s ease, transform 0.2s ease'
    el.dataset.name = t.text
    el.dataset.value = t.value
  })

  container.addEventListener('mousemove', handleMouseMove)
  container.addEventListener('mouseleave', handleMouseLeave)
}

function handleMouseMove(e) {
  const target = e.target.closest('.wordcloud3d-item')
  if (target && target.dataset.name) {
    tooltip.value = {
      visible: true,
      name: target.dataset.name,
      value: target.dataset.value,
      style: {
        left: e.offsetX + 14 + 'px',
        top: e.offsetY - 10 + 'px'
      }
    }
  } else {
    tooltip.value.visible = false
  }
}

function handleMouseLeave() {
  tooltip.value.visible = false
}

onMounted(() => {
  const texts = buildTexts(props.data)
  nextTick(() => initCloud(texts))
})

watch(() => props.data, (newData) => {
  const texts = buildTexts(newData)
  nextTick(() => initCloud(texts))
}, { deep: true })

onBeforeUnmount(() => {
  if (cloudInstance) {
    cloudInstance.destroy()
    cloudInstance = null
  }
})
</script>

<style scoped>
.wordcloud3d-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: calc(var(--radius) * 0.8);
  background: radial-gradient(ellipse at center, rgba(0, 122, 255, 0.03) 0%, transparent 70%);
}

.tagcloud-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.tagcloud-container :deep(.wordcloud3d) {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
}

.tagcloud-container :deep(.wordcloud3d-item) {
  position: absolute !important;
  top: 50% !important;
  left: 50% !important;
  will-change: transform, opacity;
  user-select: none;
  white-space: nowrap;
}

.tagcloud-container :deep(.wordcloud3d-item:hover) {
  opacity: 1 !important;
  transform: scale(1.25);
  filter: brightness(1.2);
}

.wordcloud-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(28, 28, 30, 0.88);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 8px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 10;
  box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.3);
  animation: tooltip-in 0.18s ease;
}

@keyframes tooltip-in {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.tooltip-name {
  font-size: 14px;
  font-weight: 600;
  color: #f5f5f7;
  letter-spacing: 0.01em;
}

.tooltip-value {
  font-size: 12px;
  color: #aeaeb2;
  font-weight: 400;
}
</style>
