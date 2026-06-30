<template>
  <!-- 折线图组件 -->
  <div class="chart-container">
    <BaseChart 
      :option="chartOption" 
      :height="height"
      @click="handleClick"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import * as echarts from 'echarts'
import BaseChart from './BaseChart.vue'

/**
 * 折线图组件
 * 
 * 用于展示数据随时间或顺序变化的趋势
 * 支持平滑曲线和渐变填充区域
 */

const props = defineProps({
  /** 图表标题 */
  title: String,
  /** X轴标签 */
  labels: {
    type: Array,
    default: () => []
  },
  /** 数值数组 */
  values: {
    type: Array,
    default: () => []
  },
  /** 是否使用平滑曲线 */
  smooth: {
    type: Boolean,
    default: true
  },
  /** 图表高度 */
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

/** ECharts 配置项 */
const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e5e5ea',
    borderWidth: 1,
    textStyle: { color: '#1d1d1f', fontSize: 13 },
    padding: [10, 14],
    borderRadius: 10
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '8%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: props.labels,
    axisLine: { lineStyle: { color: '#e5e5ea' } },
    axisLabel: { color: '#8e8e93', fontSize: 12, margin: 10 },
    axisTick: { show: false }
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    axisLabel: { color: '#8e8e93', fontSize: 12 },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#e5e5ea', type: 'dashed' } }
  },
  series: [{
    type: 'line',
    data: props.values,
    smooth: props.smooth,
    // 渐变填充区域
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(0, 122, 255, 0.3)' },
        { offset: 1, color: 'rgba(0, 122, 255, 0.05)' }
      ])
    },
    lineStyle: { color: '#007aff', width: 3 },
    itemStyle: { color: '#007aff' },
    symbol: 'circle',
    symbolSize: 6,
    emphasis: {
      itemStyle: { color: '#007aff', borderColor: '#ffffff', borderWidth: 2 },
      scale: true
    }
  }]
}))

/** 处理图表点击事件 */
function handleClick(params) {
  emit('click', params)
}
</script>

<style scoped>
.chart-container {
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
</style>
