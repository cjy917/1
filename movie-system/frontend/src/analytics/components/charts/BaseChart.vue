<template>
  <!-- ECharts 基础图表组件 -->
  <div ref="chartRef" class="base-chart" :style="{ height: chartHeight }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'

/**
 * ECharts 基础封装组件
 * 
 * 提供统一的图表初始化、响应式尺寸调整和事件处理
 * 所有具体图表组件（BarChart、LineChart、PieChart等）都基于此组件
 */

const props = defineProps({
  /** ECharts 配置项 */
  option: {
    type: Object,
    required: true
  },
  /** 图表高度（支持数字或字符串） */
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

const chartRef = ref(null)       // 图表容器引用
let chartInstance = null         // ECharts 实例
let resizeObserver = null        // ResizeObserver 实例
let resizeFrame = null          // 防抖用的 requestAnimationFrame ID

/** 计算最终的高度样式 */
const chartHeight = computed(() => {
  return typeof props.height === 'number' ? `${props.height}px` : props.height
})

onMounted(async () => {
  await nextTick()
  initChart()
  scheduleResize()
})

onUnmounted(() => {
  // 清理事件监听和实例
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  if (resizeFrame) cancelAnimationFrame(resizeFrame)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

/** 防抖的 resize 调度 */
function scheduleResize() {
  if (resizeFrame) cancelAnimationFrame(resizeFrame)
  resizeFrame = requestAnimationFrame(() => {
    chartInstance?.resize()
  })
}

/** 初始化图表 */
function initChart() {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(props.option)

  // 绑定点击事件
  chartInstance.on('click', (params) => {
    emit('click', params)
  })

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
  resizeObserver = new ResizeObserver(() => scheduleResize())
  resizeObserver.observe(chartRef.value)
}

/** 处理窗口 resize */
function handleResize() {
  scheduleResize()
}

/** 监听配置项变化，更新图表 */
watch(() => props.option, (newOption) => {
  chartInstance?.setOption(newOption)
  scheduleResize()
}, { deep: true })

/** 监听高度变化，调整图表 */
watch(chartHeight, () => {
  scheduleResize()
})

/** 暴露 resize 方法供外部调用 */
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
