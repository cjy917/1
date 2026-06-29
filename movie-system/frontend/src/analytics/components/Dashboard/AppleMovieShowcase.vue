<template>
  <div class="carousel-wrap" ref="wrapRef">
    <div class="carousel-box" ref="carouselRef">
      <div 
        v-for="(movie, index) in allMovies" 
        :key="index"
        class="carousel-item"
        :style="{ backgroundImage: `url(${getPosterUrl(movie.movie_id)})` }"
        @click="handleMovieClick(movie)"
      >
        <div class="movie-rating">
          <span class="star">★</span>
          <span class="rating-value">{{ formatRating(movie.rating) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  movies: {
    type: Array,
    default: () => []
  }
})

const wrapRef = ref(null)
const carouselRef = ref(null)

const allMovies = ref([...props.movies])

watch(() => props.movies, (newMovies) => {
  allMovies.value = [...newMovies, ...newMovies]
}, { immediate: true })

function getPosterUrl(movieId) {
  return `/api/posters/${movieId}`
}

function formatRating(rating) {
  if (typeof rating !== 'number') return '0.0'
  return rating.toFixed(1)
}

let animationId = null

function updateDepthEffect() {
  const wrap = wrapRef.value
  const carousel = carouselRef.value
  
  if (!wrap || !carousel) {
    animationId = requestAnimationFrame(updateDepthEffect)
    return
  }
  
  const items = carousel.querySelectorAll('.carousel-item')
  const wrapWidth = wrap.offsetWidth
  const centerX = wrapWidth / 2
  
  items.forEach(item => {
    const itemRect = item.getBoundingClientRect()
    const itemCenter = itemRect.left + itemRect.width / 2
    const distance = Math.abs(itemCenter - centerX)
    const maxDist = 420
    const rate = Math.min(distance / maxDist, 1)
    
    const scale = 1 - rate * 0.28
    const brightness = 1 - rate * 0.15
    const opacity = 1 - rate * 0.2
    
    item.style.transform = `scale(${scale})`
    item.style.filter = `brightness(${brightness})`
    item.style.opacity = opacity
    item.style.zIndex = Math.floor(100 - rate * 90)
  })
  
  animationId = requestAnimationFrame(updateDepthEffect)
}

const emit = defineEmits(['movie-click'])

function handleMovieClick(movie) {
  emit('movie-click', movie)
}

onMounted(() => {
  updateDepthEffect()
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
})
</script>

<style scoped>
.carousel-wrap {
  width: 100%;
  height: 480px;
  overflow: hidden;
  position: relative;
  margin: 40px 0;
  perspective: 1200px;
}

.carousel-box {
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  animation: scrollLeft 30s linear infinite;
}

.carousel-item {
  width: 280px;
  height: 420px;
  flex-shrink: 0;
  margin: 0 -56px;
  border-radius: 8px;
  background-size: cover;
  background-position: center;
  transition: all 0.12s ease-out;
  will-change: transform, filter;
  position: relative;
  cursor: pointer;
}

.carousel-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.4) 0%, transparent 50%);
  pointer-events: none;
}

.movie-rating {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 999px;
  backdrop-filter: blur(8px);
  z-index: 10;
}

.star {
  color: #ffcc00;
  font-size: 12px;
}

.rating-value {
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
}

@keyframes scrollLeft {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

@media (max-width: 1024px) {
  .carousel-wrap {
    height: 400px;
  }
  
  .carousel-item {
    width: 224px;
    height: 336px;
    margin: 0 -45px;
  }
}

@media (max-width: 768px) {
  .carousel-wrap {
    height: 340px;
  }
  
  .carousel-item {
    width: 184px;
    height: 276px;
    margin: 0 -37px;
  }
}

@media (max-width: 480px) {
  .carousel-wrap {
    height: 260px;
  }
  
  .carousel-item {
    width: 140px;
    height: 210px;
    margin: 0 -28px;
  }
  
  .movie-rating {
    padding: 3px 8px;
  }
  
  .star, .rating-value {
    font-size: 10px;
  }
}
</style>