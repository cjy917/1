<script setup>
import MovieCard from './MovieCard.vue'

defineProps({
  movies: { type: Array, default: () => [] },
  emptyText: { type: String, default: '暂无内容' },
  removeLabel: { type: String, default: '移除' },
})

const emit = defineEmits(['remove'])
</script>

<template>
  <p v-if="!movies.length" class="profile-empty">{{ emptyText }}</p>
  <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
    <div v-for="movie in movies" :key="movie.movie_id" class="profile-movie-item">
      <MovieCard :movie="movie" />
      <button
        type="button"
        class="profile-movie-remove"
        :title="removeLabel"
        @click="emit('remove', movie.movie_id)"
      >
        {{ removeLabel }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.profile-empty {
  margin: 0;
  padding: 1.25rem 0;
  font-size: 0.95rem;
  color: var(--fywz-muted);
}

.profile-movie-item {
  position: relative;
}

.profile-movie-remove {
  position: absolute;
  top: 0.35rem;
  left: 0.35rem;
  z-index: 30;
  border: none;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.72);
  padding: 0.2rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}

.profile-movie-item:hover .profile-movie-remove,
.profile-movie-remove:focus-visible {
  opacity: 1;
}

.profile-movie-remove:hover {
  background: rgba(180, 40, 40, 0.92);
}
</style>
