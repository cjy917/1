<template>
  <div class="movie-showcase">
    <div class="section-header">
      <h2 class="headline">🏆 热门电影</h2>
      <p class="copy-sm">评分最高的电影精选</p>
    </div>
    <div class="movie-grid">
      <div 
        v-for="movie in movies" 
        :key="movie.movie_id" 
        class="movie-card"
        @click="handleMovieClick(movie)"
      >
        <div class="movie-poster-wrapper">
          <img 
            :src="getPosterUrl(movie.movie_id)" 
            :alt="movie.title"
            class="movie-poster"
            @error="handlePosterError($event)"
          />
          <div class="movie-rating">
            <span class="star">★</span>
            <span class="rating-value">{{ formatRating(movie.rating) }}</span>
          </div>
        </div>
        <div class="movie-info">
          <h3 class="movie-title">{{ truncateTitle(movie.title) }}</h3>
          <p class="movie-year">{{ movie.year }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  movies: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['movie-click'])

function handleMovieClick(movie) {
  emit('movie-click', movie)
}

function getPosterUrl(movieId) {
  return `/api/posters/${movieId}`
}

function truncateTitle(title, maxLength = 12) {
  if (title.length <= maxLength) {
    return title
  }
  return title.slice(0, maxLength) + '...'
}

function formatRating(rating) {
  if (typeof rating !== 'number') return '0.0'
  return rating.toFixed(1)
}

function handlePosterError(event) {
  event.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="140" height="210" viewBox="0 0 140 210"%3E%3Crect fill="%23e5e5ea" width="140" height="210" rx="8"/%3E%3Ctext fill="%238e8e93" font-family="sans-serif" font-size="12" x="50%" y="50%" text-anchor="middle" dominant-baseline="middle"%3E电影封面%3C/text%3E%3C/svg%3E'
}
</script>

<style scoped>
.movie-showcase {
  margin-bottom: calc(var(--spacing) * 13);
}

.movie-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: calc(var(--spacing) * 3);
}

.movie-card {
  display: flex;
  flex-direction: column;
  gap: calc(var(--spacing) * 2);
  cursor: pointer;
}

.movie-poster-wrapper {
  position: relative;
  aspect-ratio: 2/3;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.movie-card:hover .movie-poster-wrapper {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
}

.movie-poster {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.movie-rating {
  position: absolute;
  bottom: calc(var(--spacing) * 2);
  right: calc(var(--spacing) * 2);
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 999px;
  backdrop-filter: blur(4px);
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

.movie-info {
  text-align: center;
}

.movie-title {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--card-foreground);
  line-height: 1.3;
}

.movie-year {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--muted-foreground);
}

@media (max-width: 1200px) {
  .movie-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 832px) {
  .movie-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: calc(var(--spacing) * 2);
  }
  
  .movie-title {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .movie-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
