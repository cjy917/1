<template>
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

const props = defineProps({
  title: String,
  labels: {
    type: Array,
    default: () => []
  },
  values: {
    type: Array,
    default: () => []
  },
  smooth: {
    type: Boolean,
    default: true
  },
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
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
    top: '8%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: props.labels,
    axisLine: {
      lineStyle: {
        color: '#e5e5ea'
      }
    },
    axisLabel: {
      color: '#8e8e93',
      fontSize: 12,
      margin: 10
    },
    axisTick: {
      show: false
    }
  },
  yAxis: {
    type: 'value',
    axisLine: {
      show: false
    },
    axisLabel: {
      color: '#8e8e93',
      fontSize: 12
    },
    axisTick: {
      show: false
    },
    splitLine: {
      lineStyle: {
        color: '#e5e5ea',
        type: 'dashed'
      }
    }
  },
  series: [{
    type: 'line',
    data: props.values,
    smooth: props.smooth,
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(0, 122, 255, 0.3)' },
        { offset: 1, color: 'rgba(0, 122, 255, 0.05)' }
      ])
    },
    lineStyle: {
      color: '#007aff',
      width: 3
    },
    itemStyle: {
      color: '#007aff'
    },
    symbol: 'circle',
    symbolSize: 6,
    emphasis: {
      itemStyle: {
        color: '#007aff',
        borderColor: '#ffffff',
        borderWidth: 2
      },
      scale: true
    }
  }]
}))

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
