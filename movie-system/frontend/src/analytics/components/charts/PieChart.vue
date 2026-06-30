<template>
  <!-- 饼图组件 -->
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
 * 饼图组件
 * 
 * 用于展示各部分占总体的比例关系
 * 支持环形饼图和自定义颜色
 */

const props = defineProps({
  /** 图表标题 */
  title: String,
  /** 数据数组 [{name: '名称', value: 数值}] */
  data: {
    type: Array,
    default: () => []
  },
  /** 图表高度 */
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

/** 饼图配色方案 */
const chartColors = ['#007aff', '#34c759', '#ff9500', '#5856d6', '#af52de', '#ff3b30', '#00c6fb', '#ffcc00', '#ff2d55', '#8e8e93']

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
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    orient: 'horizontal',
    bottom: '0%',
    itemWidth: 10,
    itemHeight: 10,
    itemGap: 12,
    textStyle: { color: '#8e8e93', fontSize: 12 }
  },
  series: [{
    type: 'pie',
    radius: ['40%', '65%'],  // 环形饼图
    center: ['50%', '40%'],
    data: props.data.map((item, index) => ({
      value: item.value || item.count,
      name: item.name,
      itemStyle: { color: chartColors[index % chartColors.length] }
    })),
    label: { color: '#8e8e93', fontSize: 12, formatter: '{b}' },
    labelLine: { lineStyle: { color: '#e5e5ea' } },
    itemStyle: { borderColor: '#ffffff', borderWidth: 3 }
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
