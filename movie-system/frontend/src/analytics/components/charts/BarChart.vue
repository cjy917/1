<template>
  <!-- 柱状图组件 -->
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
import BaseChart from './BaseChart.vue'

/**
 * 柱状图组件
 * 
 * 支持水平/垂直两种方向的柱状图
 * 用于展示分类数据的数值对比
 */

const props = defineProps({
  /** 图表标题 */
  title: String,
  /** X轴标签（水平）或Y轴标签（垂直） */
  labels: {
    type: Array,
    default: () => []
  },
  /** 数值数组 */
  values: {
    type: Array,
    default: () => []
  },
  /** 是否旋转为水平柱状图 */
  rotate: {
    type: Boolean,
    default: false
  },
  /** 图表高度 */
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

/** ECharts 配置项 */
const chartOption = computed(() => {
  if (props.rotate) {
    // 水平柱状图配置
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e5ea',
        borderWidth: 1,
        textStyle: {
          color: '#1d1d1f',
          fontSize: 13
        },
        padding: [10, 14],
        borderRadius: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: { color: '#8e8e93', fontSize: 12 },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#e5e5ea', type: 'dashed' } }
      },
      yAxis: {
        type: 'category',
        data: props.labels,
        axisLine: { show: false },
        axisLabel: { color: '#1d1d1f', fontSize: 12 },
        axisTick: { show: false }
      },
      series: [{
        type: 'bar',
        data: props.values,
        itemStyle: { color: '#007aff', borderRadius: [0, 6, 6, 0] },
        emphasis: { itemStyle: { color: '#0051d5' } }
      }]
    }
  }
  
  // 垂直柱状图配置
  return {
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
      axisLine: { show: false },
      axisLabel: { color: '#8e8e93', fontSize: 12 },
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
      type: 'bar',
      data: props.values,
      itemStyle: { color: '#007aff', borderRadius: [6, 6, 0, 0] },
      emphasis: { itemStyle: { color: '#0051d5' } }
    }]
  }
})

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
