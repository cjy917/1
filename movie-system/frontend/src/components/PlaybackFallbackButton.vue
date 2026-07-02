<script setup>
defineProps({
  label: { type: String, default: '查看详情' },
})

defineEmits(['click'])
</script>

<template>
  <button type="button" class="playback-fallback-btn" @click.stop="$emit('click')">
    <slot>{{ label }}</slot>
  </button>
</template>

<style scoped>
.playback-fallback-btn {
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(1, 180, 228, 0.95);
  padding: 0.75rem 1.75rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: #042541;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  transition: transform 0.2s, filter 0.2s;
  cursor: pointer;
}

.playback-fallback-btn:hover {
  transform: scale(1.04);
  filter: brightness(1.05);
}
</style>
