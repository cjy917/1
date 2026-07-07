<!--
  【详情页·区块1】影片信息 Hero
  代码搜索: 海报 评分 收藏 片单 待看 简介 演职员 我的评分
  API/后端: 见 code-map.js
-->
<template>
  <section id="movie-info" class="detail-hero">
    <div v-if="!d.themeStore.isDark" class="detail-hero__backdrop" aria-hidden="true">
      <div class="detail-hero__backdrop-blur">
        <img
          class="detail-hero__backdrop-img"
          :src="d.movie.poster_url"
          alt=""
          decoding="async"
        />
      </div>
    </div>
    <div v-if="!d.themeStore.isDark" class="detail-hero__flow" :style="d.heroFlowStyle" aria-hidden="true" />
    <div v-if="!d.themeStore.isDark" class="detail-hero__scrim" :style="d.heroScrimStyle" aria-hidden="true" />
    <div class="detail-hero__content relative mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-[240px_1fr] lg:px-8">
      <div class="detail-hero__poster-wrap mx-auto w-56 md:w-full">
        <img
          :src="d.movie.poster_url"
          :alt="d.movie.title"
          class="detail-hero__poster w-full"
          fetchpriority="high"
          decoding="async"
        />
      </div>
      <div class="detail-hero__main space-y-4">
        <h1 class="detail-hero__title">{{ d.movie.title }}</h1>
        <p v-if="d.movie.aliases" class="detail-hero__muted">{{ d.movie.aliases }}</p>
        <div class="detail-hero__meta-row">
          <span v-if="d.movie.rating" class="detail-hero__rating-badge">
            {{ Number(d.movie.rating).toFixed(1) }}
          </span>
          <span v-if="d.movie.release_year">
            <router-link class="detail-hero__meta-link" :to="buildMoviesYearRoute(d.movie.release_year)">
              {{ d.movie.release_year }}
            </router-link>
          </span>
          <span v-if="d.movie.duration">{{ d.movie.duration }}</span>
          <span v-if="d.movie.countries">{{ d.movie.countries }}</span>
        </div>

        <div class="detail-actions">
          <button
            type="button"
            class="detail-action-btn"
            :class="{ 'detail-action-btn--active': d.movie.in_list }"
            title="添加到片单"
            @click="d.toggleList"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 5h18v2H3V5zm0 6h12v2H3v-2zm0 6h18v2H3v-2z"/></svg>
          </button>
          <button
            type="button"
            class="detail-action-btn"
            :class="{ 'detail-action-btn--active': d.movie.is_favorite }"
            title="标记为收藏"
            @click="d.toggleFavorite"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
          </button>
          <button
            type="button"
            class="detail-action-btn"
            :class="{ 'detail-action-btn--active': d.movie.is_watchlist }"
            title="添加到待看片单"
            @click="d.toggleWatchlist"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>
          </button>
          <button
            v-if="d.hasLocalMovie"
            type="button"
            class="detail-play-trailer detail-play-trailer--movie"
            @click="d.switchToMovieTab"
          >
            <span class="detail-play-trailer__icon" aria-hidden="true">▶</span>
            播放正片
          </button>
          <button type="button" class="detail-play-trailer" @click="d.playTrailer">
            <span class="detail-play-trailer__icon" aria-hidden="true">▶</span>
            播放预告片
          </button>
        </div>

        <div v-if="d.movie.summary" class="detail-hero__summary-wrap">
          <p
            class="detail-hero__summary"
            :class="{ 'detail-hero__summary--collapsed': isSummaryLong(d.movie.summary) && !d.summaryExpanded }"
          >
            {{ d.displaySummary }}
          </p>
          <button
            v-if="isSummaryLong(d.movie.summary)"
            type="button"
            class="detail-hero__summary-toggle"
            @click="d.toggleSummaryExpand"
          >
            {{ d.summaryExpanded ? '收起' : '展开全部' }}
          </button>
        </div>
        <div class="detail-hero__credits">
          <DetailCreditRow
            v-for="row in d.creditRows"
            :key="row.label"
            :label="row.label"
            :names="row.names"
            :to="row.to"
          />
        </div>
        <div class="detail-hero__rate-row">
          <div class="flex flex-wrap items-center gap-3">
            <span class="text-sm detail-hero__label">我的评分</span>
            <el-rate
              v-model="d.starScore"
              allow-half
              clearable
              :max="5"
              :colors="['#01B4E4', '#01B4E4', '#01B4E4']"
              @change="d.onStarChange"
            />
            <span v-if="d.myScore > 0" class="text-sm font-semibold text-[#01B4E4]">{{ d.myScore.toFixed(1) }}</span>
          </div>
          <button class="detail-hero__btn detail-hero__btn--primary" @click="d.submitRating">
            提交评分
          </button>
          <button
            v-if="d.savedScore > 0"
            class="detail-hero__btn detail-hero__btn--ghost"
            @click="d.deleteRating"
          >
            删除评分
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { inject } from 'vue'
import DetailCreditRow from '../DetailCreditRow.vue'
import { buildMoviesYearRoute } from '../../utils/credits'
import { isSummaryLong } from '../../utils/summary'

const d = inject('movieDetail')
</script>

<style scoped>
.detail-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  color: var(--fywz-hero-text);
  padding-bottom: 1.5rem;
}

.detail-hero__backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.detail-hero__backdrop-blur {
  position: absolute;
  inset: -34%;
  animation: hero-backdrop-kenburns 10s ease-in-out infinite alternate;
}

.detail-hero__backdrop-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  filter: blur(20px) saturate(1.55) brightness(0.78);
  transform: scale(1.12);
}

.detail-hero__flow {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: 0% 25%;
  animation: hero-gradient-flow 5s ease-in-out infinite alternate;
}

.detail-hero__scrim {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

@keyframes hero-backdrop-kenburns {
  0% {
    transform: scale(1.02) translate(7%, 5%);
  }

  100% {
    transform: scale(1.38) translate(-9%, -7%);
  }
}

@keyframes hero-gradient-flow {
  0% {
    background-position: 0% 20%;
  }

  100% {
    background-position: 100% 80%;
  }
}

@keyframes hero-poster-float {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  50% {
    transform: translateY(-18px) scale(1.02);
  }
}

@media (prefers-reduced-motion: reduce) {
  .detail-hero__backdrop-blur,
  .detail-hero__flow,
  .detail-hero__poster-wrap {
    animation: none;
  }
}

.detail-hero::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  height: 6.5rem;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    color-mix(in srgb, var(--fywz-bg) 28%, transparent) 42%,
    color-mix(in srgb, var(--fywz-bg) 72%, transparent) 72%,
    var(--fywz-bg) 100%
  );
  pointer-events: none;
}

.detail-hero__content {
  position: relative;
  z-index: 3;
}

.detail-hero__main,
.detail-hero__poster-wrap {
  position: relative;
}

.detail-hero__poster-wrap {
  animation: hero-poster-float 4.5s ease-in-out infinite;
}

.detail-hero__poster {
  border-radius: 12px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.35);
  transition: box-shadow 0.35s ease, transform 0.35s ease;
}

.detail-hero__poster-wrap:hover .detail-hero__poster {
  transform: scale(1.02);
  box-shadow: 0 22px 48px rgba(0, 0, 0, 0.42);
}

.detail-hero__title {
  font-size: clamp(1.75rem, 4vw, 2.5rem);
  font-weight: 800;
  line-height: 1.15;
  color: var(--fywz-hero-text);
}

.detail-hero__muted,
.detail-hero__summary,
.detail-hero__credits {
  color: var(--fywz-hero-text-muted);
}

.detail-hero__summary-wrap {
  max-width: 48rem;
}

.detail-hero__summary {
  margin: 0;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-hero__summary--collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: normal;
}

.detail-hero__summary-toggle {
  margin-top: 0.35rem;
  border: none;
  background: none;
  padding: 0;
  font-size: 0.875rem;
  color: var(--fywz-link);
  cursor: pointer;
}

.detail-hero__summary-toggle:hover {
  text-decoration: underline;
}

.detail-hero__meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.9rem;
  color: var(--fywz-hero-meta);
}

.detail-hero__meta-link {
  color: inherit;
  text-decoration: none;
  transition: color 0.2s ease, text-decoration-color 0.2s ease;
}

.detail-hero__meta-link:hover {
  color: var(--fywz-accent);
  text-decoration: underline;
}

.detail-hero__rating-badge {
  border-radius: 999px;
  background: rgba(1, 180, 228, 0.18);
  padding: 0.15rem 0.55rem;
  font-weight: 700;
  color: var(--fywz-accent);
}

.detail-hero__credits {
  display: grid;
  gap: 0.35rem;
  font-size: 0.9rem;
}

@media (min-width: 768px) {
  .detail-hero__credits {
    grid-template-columns: 1fr 1fr;
  }
}

.detail-hero__label {
  font-weight: 600;
  color: var(--fywz-hero-text);
}

.detail-hero__credit-row {
  margin: 0;
}

.detail-hero__credit-list {
  display: inline;
}

.detail-hero__credit-link {
  color: var(--fywz-link);
  text-decoration: none;
  transition: color 0.2s ease, text-decoration-color 0.2s ease;
}

.detail-hero__credit-link:hover {
  color: var(--fywz-accent);
  text-decoration: underline;
}

.detail-hero__credit-sep {
  margin: 0 0.15rem;
  color: var(--fywz-hero-text-muted);
}

.detail-hero__rate-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  padding-top: 0.25rem;
}

.detail-hero__btn {
  border-radius: 999px;
  padding: 0.45rem 1.15rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.2s;
}

.detail-hero__btn--primary {
  border: none;
  background: var(--fywz-accent);
  color: var(--fywz-accent-text);
}

.detail-hero__btn--ghost {
  border: 1px solid var(--fywz-border);
  background: transparent;
  color: var(--fywz-hero-text);
}

.detail-hero__btn:hover {
  filter: brightness(1.05);
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
}

.detail-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--fywz-detail-action-bg);
  color: var(--fywz-detail-action-color);
  cursor: pointer;
  transition: transform 0.15s, background 0.15s, color 0.15s;
}

.detail-action-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.detail-action-btn:hover {
  transform: scale(1.05);
  filter: brightness(1.08);
}

.detail-action-btn--active {
  background: var(--fywz-detail-action-active-bg);
  color: var(--fywz-detail-action-active-color);
}

.detail-play-trailer {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 0.25rem;
  border: none;
  background: transparent;
  font-size: 1rem;
  font-weight: 600;
  color: var(--fywz-play-trailer-text);
  cursor: pointer;
}

.detail-play-trailer__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--fywz-play-trailer-icon-bg);
  color: var(--fywz-play-trailer-icon-color);
  font-size: 0.75rem;
}

.detail-play-trailer--movie {
  color: var(--fywz-accent);
}
</style>
