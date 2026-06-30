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
  data: {
    type: Array,
    default: () => []
  },
  height: {
    type: [String, Number],
    default: '350px'
  }
})

const emit = defineEmits(['click'])

const chartColors = ['#007aff', '#34c759', '#ff9500', '#5856d6', '#af52de', '#ff3b30', '#00c6fb', '#ffcc00', '#ff2d55', '#8e8e93']

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
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    orient: 'horizontal',
    bottom: '0%',
    itemWidth: 10,
    itemHeight: 10,
    itemGap: 12,
    textStyle: {
      color: '#8e8e93',
      fontSize: 12
    }
  },
  series: [{
    type: 'pie',
    radius: ['40%', '65%'],
    center: ['50%', '40%'],
    data: props.data.map((item, index) => ({
      value: item.value || item.count,
      name: item.name,
      itemStyle: {
        color: chartColors[index % chartColors.length]
      }
    })),
    label: {
      color: '#8e8e93',
      fontSize: 12,
      formatter: '{b}'
    },
    labelLine: {
      lineStyle: {
        color: '#e5e5ea'
      }
    },
    itemStyle: {
      borderColor: '#ffffff',
      borderWidth: 3
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
