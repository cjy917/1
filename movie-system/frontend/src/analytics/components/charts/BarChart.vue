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
  rotate: {
    type: Boolean,
    default: false
  },
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

const chartOption = computed(() => {
  if (props.rotate) {
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
        axisLabel: {
          color: '#8e8e93',
          fontSize: 12
        },
        axisTick: { show: false },
        splitLine: {
          lineStyle: {
            color: '#e5e5ea',
            type: 'dashed'
          }
        }
      },
      yAxis: {
        type: 'category',
        data: props.labels,
        axisLine: { show: false },
        axisLabel: {
          color: '#1d1d1f',
          fontSize: 12
        },
        axisTick: { show: false }
      },
      series: [{
        type: 'bar',
        data: props.values,
        itemStyle: {
          color: '#007aff',
          borderRadius: [0, 6, 6, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#0051d5'
          }
        }
      }]
    }
  }
  
  return {
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
      axisLine: { show: false },
      axisLabel: {
        color: '#8e8e93',
        fontSize: 12
      },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: {
        color: '#8e8e93',
        fontSize: 12
      },
      axisTick: { show: false },
      splitLine: {
        lineStyle: {
          color: '#e5e5ea',
          type: 'dashed'
        }
      }
    },
    series: [{
      type: 'bar',
      data: props.values,
      itemStyle: {
        color: '#007aff',
        borderRadius: [6, 6, 0, 0]
      },
      emphasis: {
        itemStyle: {
          color: '#0051d5'
        }
      }
    }]
  }
})

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
