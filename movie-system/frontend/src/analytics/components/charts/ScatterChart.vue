<template>
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

const props = defineProps({
  title: String,
  data: {
    type: Array,
    default: () => []
  },
  xName: {
    type: String,
    default: 'X轴'
  },
  yName: {
    type: String,
    default: 'Y轴'
  },
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e5e5ea',
    borderWidth: 1,
    textStyle: {
      color: '#1d1d1f',
      fontSize: 13
    },
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
    nameTextStyle: {
      color: '#8e8e93',
      fontSize: 12
    },
    axisLine: {
      lineStyle: {
        color: '#e5e5ea'
      }
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
  yAxis: {
    type: 'value',
    name: props.yName,
    nameTextStyle: {
      color: '#8e8e93',
      fontSize: 12
    },
    axisLine: {
      lineStyle: {
        color: '#e5e5ea'
      }
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
    type: 'scatter',
    data: props.data.map(item => [item.rating, item.duration]),
    symbolSize: 8,
    itemStyle: {
      color: '#007aff',
      opacity: 0.6
    },
    emphasis: {
      itemStyle: {
        color: '#007aff',
        opacity: 1,
        borderColor: '#ffffff',
        borderWidth: 2
      },
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
