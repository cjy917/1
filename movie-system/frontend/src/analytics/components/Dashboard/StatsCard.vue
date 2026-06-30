<template>
  <div class="stats-card">
    <div class="stats-icon">
      <span class="icon">{{ icon }}</span>
    </div>
    <div class="stats-content">
      <div class="stats-label eyebrow">{{ label }}</div>
      <div class="stats-value title-1">{{ formattedValue }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: String,
  label: String,
  value: [Number, String],
  decimals: {
    type: Number,
    default: null
  }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    if (props.value >= 100000000) {
      return (props.value / 100000000).toFixed(2) + '亿'
    } else if (props.value >= 10000) {
      return (props.value / 10000).toFixed(1) + '万'
    } else if (props.value >= 1000) {
      return (props.value / 1000).toFixed(1) + 'K'
    }
    if (props.decimals !== null) {
      return props.value.toFixed(props.decimals)
    }
    return props.value.toFixed(props.value % 1 === 0 ? 0 : 2)
  }
  return props.value
})
</script>

<style scoped>
.stats-card {
  display: flex;
  align-items: flex-start;
  gap: calc(var(--spacing) * 4);
  padding: calc(var(--spacing) * 7) calc(var(--spacing) * 5);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  cursor: default;
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.stats-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--secondary), var(--accent));
  border-radius: calc(var(--radius) - 4px);
  flex-shrink: 0;
}

.stats-icon .icon {
  font-size: 20px;
  line-height: 1;
}

.stats-content {
  flex: 1;
  min-width: 0;
}

.stats-label {
  margin-bottom: 4px;
}

.stats-value {
  margin: 0;
  color: var(--card-foreground);
}

@media (max-width: 832px) {
  .stats-card {
    padding: calc(var(--spacing) * 6) calc(var(--spacing) * 4);
  }
  
  .stats-value {
    font-size: 20px;
  }
}
</style>
