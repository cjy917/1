<template>
  <div class="tag-cloud-wordcloud" ref="containerRef"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

const containerRef = ref(null)
let chartInstance = null
let resizeObserver = null

const LIGHT_COLORS = [
  '#ff6b6b', '#007aff', '#34c759', '#ff9500',
  '#5856d6', '#af52de', '#5ac8fa', '#00c7be',
  '#ffd60a', '#ff2d55', '#7c5cfc', '#30d158',
  '#64d2ff', '#bf5af2', '#ff453a', '#0a84ff'
]

const DARK_COLORS = [
  '#ff7eb3', '#64d2ff', '#4cd964', '#ff9f0a',
  '#a389f4', '#b388ff', '#5ac8fa', '#50e3c2',
  '#ffe600', '#ff3b30', '#ff6b6b', '#34c759',
  '#00c6fb', '#af52de', '#ff2d55', '#007aff'
]

const isDark = computed(() => document.documentElement.getAttribute('data-theme') === 'dark')

function getColors() {
  return isDark.value ? DARK_COLORS : LIGHT_COLORS
}

function pickColor(name, index) {
  const colors = getColors()
  if (name === '剧情') return '#ff6b6b'
  if (name === '喜剧') return '#007aff'
  if (name.includes('恐怖') && name.includes('惊悚')) return '#34c759'
  return colors[index % colors.length]
}

function buildChartData() {
  return (props.data || []).map((item, index) => ({
    name: item.name,
    value: item.value,
    itemStyle: { color: pickColor(item.name, index) }
  }))
}

function initChart() {
  if (!containerRef.value) return

  chartInstance = echarts.init(containerRef.value)
  updateChart()

  window.addEventListener('resize', handleResize)
  resizeObserver = new ResizeObserver(() => handleResize())
  resizeObserver.observe(containerRef.value)
}

function handleResize() {
  chartInstance?.resize()
}

function updateChart() {
  if (!chartInstance || !props.data?.length) return

  const colors = getColors()
  const chartData = buildChartData()

  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: isDark.value ? 'rgba(17, 24, 39, 0.95)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark.value ? 'rgba(0, 212, 255, 0.3)' : 'rgba(0, 122, 255, 0.2)',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: {
        color: isDark.value ? '#f5f5f7' : '#1d1d1f',
        fontSize: 13
      },
      formatter: (params) => {
        return `<span style="font-weight: 700; font-size: 14px;">${params.name}</span><br/>
                <span style="color: ${isDark.value ? '#9ca3af' : '#8e8e93'};">${params.value} 部电影</span>`
      }
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '92%',
      height: '88%',
      gridSize: 8,
      sizeRange: [14, 72],
      rotationRange: [-15, 15],
      rotationStep: 15,
      shrinkToFit: true,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'Noto Sans SC, PingFang SC, sans-serif',
        fontWeight: 'bold',
        color: () => colors[Math.floor(Math.random() * colors.length)]
      },
      emphasis: {
        scale: true,
        scaleSize: 14,
        focus: 'self',
        textStyle: {
          shadowBlur: 20,
          shadowColor: colors[0]
        }
      },
      data: chartData
    }]
  }, true)

  nextTick(() => chartInstance?.resize())
}

onMounted(() => {
  nextTick(() => initChart())
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  chartInstance?.dispose()
})

watch(() => props.data, () => {
  updateChart()
}, { deep: true })

watch(isDark, () => {
  updateChart()
})
</script>

<style scoped>
.tag-cloud-wordcloud {
  width: 100%;
  height: 380px;
  border-radius: 12px;
}
</style>
