import { defineStore } from 'pinia'
import { ratingApi } from '../api'

export const useRatingsStore = defineStore('ratings', {
  state: () => ({
    byMovieId: {},
    loaded: false,
  }),
  getters: {
    scoreOf: (state) => (movieId) => state.byMovieId[movieId] || 0,
  },
  actions: {
    async fetchMine() {
      try {
        const { data } = await ratingApi.mine()
        this.byMovieId = Object.fromEntries(
          data.items.map((movie) => [movie.movie_id, movie.my_rating]),
        )
      } catch {
        this.byMovieId = {}
      }
      this.loaded = true
    },
    clear() {
      this.byMovieId = {}
      this.loaded = false
    },
    async save(movieId, score) {
      await ratingApi.rate({ movie_id: movieId, score })
      this.byMovieId[movieId] = score
    },
    async remove(movieId) {
      await ratingApi.remove(movieId)
      delete this.byMovieId[movieId]
    },
  },
})
