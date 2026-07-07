<!--
  【详情页·区块2】正片/预告播放器
  代码搜索: 播放正片 预告片 MediaPlayer 在线观看 重新加载
  API/后端: 见 code-map.js
-->
<template>
  <div id="movie-player" class="mx-auto max-w-6xl px-4 py-7 lg:px-8">
    <section class="movie-player">
      <div class="mb-2 flex flex-wrap items-center gap-2">
        <button
          class="tab-btn"
          :class="d.activeTab === 'movie' ? 'tab-btn--active' : 'tab-btn--idle'"
          @click="d.switchToMovieTab"
        >
          播放正片
        </button>
        <button
          class="tab-btn"
          :class="d.activeTab === 'trailer' ? 'tab-btn--active' : 'tab-btn--idle'"
          @click="d.playTrailer"
        >
          预告片
        </button>
        <span class="ml-auto text-xs text-muted">
          {{ d.activeTab === 'movie' ? d.sourceLabel : d.trailerLabel }}
        </span>
      </div>

      <div class="movie-player__screen relative overflow-hidden bg-black">
        <div
          v-if="d.loadingPlayback && d.activeTab === 'movie'"
          class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-black px-6"
        >
          <p v-if="!d.showPlaybackLoadFallback" class="text-sm text-white/70">正在加载正片…</p>
          <template v-else>
            <p class="text-sm text-white/70">加载较慢，可先选择以下方式</p>
            <div v-if="d.streamingLinks.length" class="watch-platform-list">
              <button
                v-for="link in d.streamingLinks"
                :key="link.platform"
                type="button"
                class="watch-platform-btn"
                :class="{ 'watch-platform-btn--primary': link.url === d.watchLinks?.primary_url }"
                @click="d.openWatchPage(link.url)"
              >
                {{ link.label || '在线观看' }}
              </button>
            </div>
            <div v-if="d.hasDetailInfo" class="watch-detail-row">
              <span v-if="d.streamingLinks.length" class="watch-detail-row__hint">或</span>
              <button type="button" class="watch-detail-btn" @click="d.openDetailPage()">
                {{ d.primaryDetailLabel }}
              </button>
            </div>
            <PlaybackFallbackButton
              v-if="!d.streamingLinks.length && !d.hasDetailInfo"
              label="查看影片信息"
              @click="d.scrollToInfo"
            />
          </template>
        </div>

        <div
          v-else-if="d.loadingTrailer && d.activeTab === 'trailer' && !d.trailer"
          class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-black/80"
        >
          <img
            :src="d.movie.poster_url"
            alt=""
            class="absolute inset-0 h-full w-full object-cover opacity-25 blur-sm"
          />
          <p v-if="!d.showTrailerLoadFallback" class="relative z-10 text-sm text-white/70">正在加载预告…</p>
          <template v-else>
            <PlaybackFallbackButton
              v-if="d.hasDetailInfo"
              :label="d.primaryDetailLabel"
              @click="d.openDetailPage()"
            />
            <PlaybackFallbackButton
              v-else
              label="查看影片信息"
              @click="d.scrollToInfo"
            />
            <p class="relative z-10 px-6 text-center text-xs text-white/50">
              {{ d.hasDetailInfo ? '预告加载较慢，可先了解影片详情' : '预告加载较慢，可先查看上方影片详情' }}
            </p>
          </template>
        </div>

        <template v-else-if="d.activeTab === 'movie'">
          <div v-if="d.moviePlaybackSource" class="movie-player__video-shell relative h-full">
            <MediaPlayer
              :source="d.moviePlaybackSource"
              :autoplay="d.movieAutoplay"
              controls
              :cover="false"
              preload="metadata"
              :play-check-ms="15000"
              :enable-fallback="false"
              @playback-failed="d.onMoviePlaybackFailed"
            />
            <p v-if="d.moviePlaybackError" class="movie-player__error">
              正片暂时无法播放，请稍后重试或点击「重新加载」
            </p>
          </div>
          <div v-else class="flex h-full flex-col items-center justify-center gap-4 px-6 text-center text-sm text-white/70">
            <p>{{ d.playback?.message || '本站暂无正片，可前往以下平台观看' }}</p>
            <div v-if="d.streamingLinks.length" class="watch-platform-list">
              <button
                v-for="link in d.streamingLinks"
                :key="link.platform"
                type="button"
                class="watch-platform-btn"
                :class="{ 'watch-platform-btn--primary': link.url === d.watchLinks?.primary_url }"
                @click="d.openWatchPage(link.url)"
              >
                {{ link.label || '在线观看' }}
              </button>
            </div>
            <div v-if="d.hasDetailInfo" class="watch-detail-row">
              <span v-if="d.streamingLinks.length" class="watch-detail-row__hint">或</span>
              <button type="button" class="watch-detail-btn" @click="d.openDetailPage()">
                {{ d.primaryDetailLabel }}
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div v-if="d.trailer && d.trailer.type !== 'none'" class="relative h-full">
            <MediaPlayer
              :source="d.trailer"
              :autoplay="true"
              muted
              :cover="false"
              controls
              :play-check-ms="3000"
              :fallback-label="d.primaryDetailLabel"
              @open-detail="d.openDetailPage()"
            />
          </div>
          <div v-else class="flex h-full flex-col items-center justify-center gap-4 px-6 text-center text-sm text-white/70">
            <p>{{ d.trailer?.message || '暂无预告片' }}</p>
            <PlaybackFallbackButton
              v-if="d.hasDetailInfo"
              :label="d.primaryDetailLabel"
              @click="d.openDetailPage()"
            />
          </div>
        </template>
      </div>

      <div class="flex flex-wrap items-center gap-2 pt-2 text-sm">
        <button
          class="rounded-full border px-4 py-1.5"
          style="border-color: var(--fywz-border)"
          @click="d.activeTab === 'movie' ? d.loadPlayback() : d.loadTrailer(true)"
        >
          重新加载
        </button>
        <p v-if="d.activeTab === 'movie' ? d.playback?.type !== 'none' && d.playback?.message : d.trailer?.message" class="text-xs text-muted">
          {{ d.activeTab === 'movie' ? d.playback?.message : d.trailer?.message }}
        </p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import MediaPlayer from '../MediaPlayer.vue'
import PlaybackFallbackButton from '../PlaybackFallbackButton.vue'

const d = inject('movieDetail')
</script>

<style scoped>
.watch-platform-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
  max-width: 28rem;
}

.watch-platform-btn {
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 9999px;
  padding: 0.45rem 0.95rem;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.88);
  background: rgba(255, 255, 255, 0.08);
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.watch-platform-btn:hover {
  background: rgba(1, 180, 228, 0.22);
  border-color: rgba(1, 180, 228, 0.55);
  transform: translateY(-1px);
}

.watch-platform-btn--primary {
  background: rgba(1, 180, 228, 0.28);
  border-color: rgba(1, 180, 228, 0.72);
  color: #fff;
}

.watch-detail-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.watch-detail-row__hint {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.45);
}

.watch-detail-btn {
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 9999px;
  padding: 0.4rem 0.9rem;
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.78);
  background: transparent;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.watch-detail-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.38);
  color: #fff;
}

.movie-player__screen {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
}

.movie-player__video-shell {
  position: relative;
  height: 100%;
  min-height: 0;
}

.movie-player__error {
  position: absolute;
  inset: 0;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  text-align: center;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #fff;
  background: rgba(0, 0, 0, 0.72);
}

.detail-play-trailer--movie {
  color: var(--fywz-accent);
}
</style>
