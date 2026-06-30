<template>
  <!-- 散点图组件 -->
  <div class="chart-container">
    <BaseChart 
      :option="chartOption" 
      :height="height"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

/**
 * 散点图组件
 * 
 * 用于展示两个数值变量之间的关系和分布
 * 数据项格式: [{rating: 评分, duration: 时长, ...}]
 */

const props = defineProps({
  /** 图表标题 */
  title: String,
  /** 数据数组 [{rating: 评分, duration: 时长}] */
  data: {
    type: Array,
    default: () => []
  },
  /** X轴名称 */
  xName: {
    type: String,
    default: 'X轴'
  },
  /** Y轴名称 */
  yName: {
    type: String,
    default: 'Y轴'
  },
  /** 图表高度 */
  height: {
    type: [String, Number],
    default: '350px'
  }
})

/** ECharts 配置项 */
const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e5e5ea',
    borderWidth: 1,
    textStyle: { color: '#1d1d1f', fontSize: 13 },
    padding: [10, 14],
    borderRadius: 10,
    formatter: (params) => `${props.xName}: ${params.data[0]}<br>${props.yName}: ${params.data[1]}`
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '8%',
    containLabel: true
  },
  xAxis: {
    type: 'value',
    name: props.xName,
    nameTextStyle: { color: '#8e8e93', fontSize: 12 },
    axisLine: { lineStyle: { color: '#e5e5ea' } },
    axisLabel: { color: '#8e8e93', fontSize: 12 },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#e5e5ea', type: 'dashed' } }
  },
  yAxis: {
    type: 'value',
    name: props.yName,
    nameTextStyle: { color: '#8e8e93', fontSize: 12 },
    axisLine: { lineStyle: { color: '#e5e5ea' } },
    axisLabel: { color: '#8e8e93', fontSize: 12 },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#e5e5ea', type: 'dashed' } }
  },
  series: [{
    type: 'scatter',
    data: props.data.map(item => [item.rating, item.duration]),  // 将数据映射为 [x, y] 格式
    symbolSize: 8,
    itemStyle: { color: '#007aff', opacity: 0.6 },
    emphasis: {
      itemStyle: { color: '#007aff', opacity: 1, borderColor: '#ffffff', borderWidth: 2 },
      scale: true
    }
  }]
}))
</script>

<style scoped>
.chart-container {
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
</style>
