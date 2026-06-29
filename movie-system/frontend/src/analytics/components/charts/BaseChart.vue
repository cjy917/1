<template>
  <div ref="chartRef" class="base-chart" :style="{ height: chartHeight }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: {
    type: Object,
    required: true
  },
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null
let resizeFrame = null

const chartHeight = computed(() => {
  return typeof props.height === 'number' ? `${props.height}px` : props.height
})

onMounted(async () => {
  await nextTick()
  initChart()
  scheduleResize()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  if (resizeFrame) cancelAnimationFrame(resizeFrame)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

function scheduleResize() {
  if (resizeFrame) cancelAnimationFrame(resizeFrame)
  resizeFrame = requestAnimationFrame(() => {
    chartInstance?.resize()
  })
}

function initChart() {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(props.option)

  chartInstance.on('click', (params) => {
    emit('click', params)
  })

  window.addEventListener('resize', handleResize)
  resizeObserver = new ResizeObserver(() => scheduleResize())
  resizeObserver.observe(chartRef.value)
}

function handleResize() {
  scheduleResize()
}

watch(() => props.option, (newOption) => {
  chartInstance?.setOption(newOption)
  scheduleResize()
}, { deep: true })

watch(chartHeight, () => {
  scheduleResize()
})

defineExpose({
  resize: scheduleResize
})
</script>

<style scoped>
.base-chart {
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
</style>
