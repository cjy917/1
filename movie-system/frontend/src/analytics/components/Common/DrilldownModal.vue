<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="handleClose">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="headline">{{ modalTitle }}</h3>
          <button @click="handleClose" class="btn-close">×</button>
        </div>
        <div class="modal-body">
          <div v-if="type === 'director'" class="drilldown-info">
            <div class="info-row">
              <span class="info-label">导演</span>
              <span class="info-value">{{ data?.name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">作品数量</span>
              <span class="info-value">{{ data?.count }}</span>
            </div>
            <div class="movie-list">
              <h4 class="subhead">代表作品</h4>
              <div v-if="movies.length" class="movies">
                <div v-for="movie in movies" :key="movie.movie_id" class="movie-item">
                  <span class="movie-title">{{ movie.title }}</span>
                  <span class="movie-rating">⭐ {{ formatRating(movie.rating) }}</span>
                </div>
              </div>
              <div v-else class="no-data">暂无数据</div>
            </div>
          </div>
          
          <div v-else-if="type === 'actor'" class="drilldown-info">
            <div class="info-row">
              <span class="info-label">演员</span>
              <span class="info-value">{{ data?.name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">参演数量</span>
              <span class="info-value">{{ data?.count }}</span>
            </div>
            <div class="movie-list">
              <h4 class="subhead">参演作品</h4>
              <div v-if="movies.length" class="movies">
                <div v-for="movie in movies" :key="movie.movie_id" class="movie-item">
                  <span class="movie-title">{{ movie.title }}</span>
                  <span class="movie-rating">⭐ {{ formatRating(movie.rating) }}</span>
                </div>
              </div>
              <div v-else class="no-data">暂无数据</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  type: String,
  data: Object
})

const emit = defineEmits(['update:visible'])

const movies = ref([])

const modalTitle = computed(() => {
  switch (props.type) {
    case 'director': return '导演详情'
    case 'actor': return '演员详情'
    default: return '详情'
  }
})

watch(() => props.visible, async (newVal) => {
  if (newVal && props.data) {
    await loadDetailData()
  }
})

async function loadDetailData() {
  movies.value = []
}

function handleClose() {
  emit('update:visible', false)
}

function formatRating(rating) {
  if (typeof rating !== 'number') return '0.0'
  return rating.toFixed(1)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 20px;
  width: 90%;
  max-width: 560px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: var(--shadow-xl);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  margin: 0;
}

.btn-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--secondary);
  border: none;
  border-radius: 10px;
  font-size: 18px;
  color: #8e8e93;
  cursor: pointer;
  transition: all 180ms ease;
}

.btn-close:hover {
  background: rgba(0, 0, 0, 0.08);
  color: #1d1d1f;
}

.modal-body {
  padding: 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
}

.info-label {
  color: #8e8e93;
  font-size: 14px;
}

.info-value {
  color: #1d1d1f;
  font-weight: 500;
  font-size: 14px;
}

.movie-list h4 {
  margin: 20px 0 14px;
}

.movies {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.movie-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: var(--secondary);
  border-radius: 12px;
}

.movie-title {
  color: #1d1d1f;
  font-size: 14px;
}

.movie-rating {
  color: #ff9500;
  font-size: 14px;
  font-weight: 500;
}

.no-data {
  color: #8e8e93;
  text-align: center;
  padding: 40px 20px;
  font-size: 14px;
}
</style>
