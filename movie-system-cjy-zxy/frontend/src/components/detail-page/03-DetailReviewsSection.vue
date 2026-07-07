<!--
  【详情页·区块3】短评与精选评论
  代码搜索: 短评 发表评论 站友短评 精选短评 翻译 展开收起
  API/后端: 见 code-map.js
-->
<template>
  <div class="mx-auto max-w-5xl space-y-8 px-4 py-7 lg:px-8">
    <section class="detail-reviews">
      <h2 class="detail-section-title">短评</h2>

      <div v-if="d.userStore.isLoggedIn" class="comment-compose">
        <div class="comment-compose__meta">
          <span class="review-item__author">{{ d.userStore.user?.username }}</span>
          <span class="review-item__tag">写短评</span>
          <el-rate
            v-model="d.commentStarScore"
            allow-half
            clearable
            :max="5"
            :colors="['#f5a623', '#f5a623', '#f5a623']"
            void-color="#c0c4cc"
            class="review-item__stars"
          />
          <span v-if="d.commentScore > 0" class="review-item__score">{{ formatReviewRating(d.commentScore) }}</span>
        </div>
        <textarea
          v-model="d.commentText"
          class="comment-compose__input"
          rows="4"
          maxlength="2000"
          placeholder="写下你的观感…"
        />
        <div class="comment-compose__actions">
          <button
            type="button"
            class="comment-compose__submit"
            :disabled="d.submittingComment"
            @click="d.submitComment"
          >
            {{ d.myComment ? '更新评论' : '发表评论' }}
          </button>
          <button
            v-if="d.myComment"
            type="button"
            class="comment-compose__delete"
            :disabled="d.submittingComment"
            @click="d.deleteComment"
          >
            删除我的评论
          </button>
        </div>
      </div>
      <p v-else class="comment-login-hint">
        <button type="button" class="review-item__toggle" @click="d.goLogin">登录</button>
        后参与短评讨论
      </p>

      <div v-if="d.userComments.length" class="review-list review-list--user">
        <h3 class="detail-subsection-title">站友短评</h3>
        <article
          v-for="item in d.userComments"
          :key="`u-${item.id}`"
          :id="`comment-user-${item.id}`"
          class="review-item"
          :class="{ 'review-item--mine': item.is_mine }"
        >
          <div class="review-item__meta">
            <span class="review-item__author">{{ item.username }}</span>
            <span v-if="item.is_mine" class="review-item__tag review-item__tag--mine">我的</span>
            <span v-else class="review-item__tag">看过</span>
            <el-rate
              v-if="item.score != null"
              class="review-item__stars"
              :model-value="reviewStarScore(item.score)"
              disabled
              allow-half
              :max="5"
              :colors="['#f5a623', '#f5a623', '#f5a623']"
              disabled-void-color="#c0c4cc"
            />
            <span v-if="item.score != null" class="review-item__score">{{ formatReviewRating(item.score) }}</span>
            <span v-if="item.created_at" class="review-item__time">{{ formatCommentTime(item.created_at) }}</span>
          </div>
          <p
            :ref="(el) => d.measureReviewBody(el, `u-${item.id}`)"
            class="review-item__body"
            :class="{ 'review-item__body--collapsed': d.isReviewCollapsible(`u-${item.id}`) && !d.isReviewExpanded(`u-${item.id}`) }"
          >
            {{ item.content }}
          </p>
          <button
            v-if="d.isReviewCollapsible(`u-${item.id}`)"
            type="button"
            class="review-item__toggle"
            @click="d.toggleReviewExpand(`u-${item.id}`)"
          >
            {{ d.isReviewExpanded(`u-${item.id}`) ? '收起' : '展开' }}
          </button>
        </article>
      </div>
      <p v-else-if="d.userStore.isLoggedIn" class="comment-empty">还没有站友短评，来写第一条吧。</p>
    </section>

    <section v-if="d.movie.crawled_review_list?.length" class="detail-reviews">
      <h2 class="detail-section-title">精选短评</h2>
      <div class="review-list">
        <article
          v-for="(item, idx) in d.movie.crawled_review_list"
          :key="idx"
          :id="`comment-crawled-${d.movie.movie_id}-${idx}`"
          class="review-item"
        >
          <div class="review-item__meta">
            <span class="review-item__author">{{ item.author }}</span>
            <span class="review-item__tag">看过</span>
            <el-rate
              v-if="item.rating != null"
              class="review-item__stars"
              :model-value="reviewStarScore(item.rating)"
              disabled
              allow-half
              :max="5"
              :colors="['#f5a623', '#f5a623', '#f5a623']"
              disabled-void-color="#c0c4cc"
            />
            <span v-if="item.rating != null" class="review-item__score">{{ formatReviewRating(item.rating) }}</span>
          </div>
          <p
            :ref="(el) => d.measureReviewBody(el, `c-${idx}`)"
            class="review-item__body"
            :class="{ 'review-item__body--collapsed': d.isReviewCollapsible(`c-${idx}`) && !d.isReviewExpanded(`c-${idx}`) }"
          >
            {{ d.displayReviewText(`c-${idx}`, item.content) }}
          </p>
          <div class="review-item__actions">
            <button
              v-if="d.isReviewCollapsible(`c-${idx}`)"
              type="button"
              class="review-item__toggle"
              @click="d.toggleReviewExpand(`c-${idx}`)"
            >
              {{ d.isReviewExpanded(`c-${idx}`) ? '收起' : '展开' }}
            </button>
            <button
              v-if="d.canTranslateReview(item.content)"
              type="button"
              class="review-item__toggle"
              :disabled="d.isReviewTranslationLoading(`c-${idx}`)"
              @click="d.toggleReviewTranslation(`c-${idx}`, item.content)"
            >
              {{ d.reviewTranslationLabel(`c-${idx}`) }}
            </button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import {
  formatCommentTime,
  formatReviewRating,
  reviewStarScore,
} from '../../utils/reviews'

const d = inject('movieDetail')
</script>

<style scoped>
.detail-subsection-title {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.review-item__tag--mine {
  color: var(--fywz-accent);
  font-weight: 600;
}

.detail-section-title {
  margin: 0 0 0.65rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--fywz-text);
}

.detail-reviews .comment-compose__meta {
  margin-bottom: 0.5rem;
}

.detail-reviews .comment-compose__input {
  min-height: 4.5rem;
  font-size: 0.875rem;
  line-height: 1.55;
  padding: 0.6rem 0.75rem;
}

.detail-reviews .review-item {
  padding: 0.65rem 0;
}

.detail-reviews .review-item__meta {
  margin-bottom: 0.35rem;
  gap: 0.25rem 0.5rem;
}

.detail-reviews .review-item__author {
  font-size: 0.875rem;
}

.detail-reviews .review-item__tag,
.detail-reviews .review-item__score {
  font-size: 0.8rem;
}

.detail-reviews .review-item__stars :deep(.el-rate__icon) {
  font-size: 0.85rem;
}

.detail-reviews .review-item__body {
  font-size: 0.875rem;
  line-height: 1.55;
}

.detail-reviews .review-item__body--collapsed {
  -webkit-line-clamp: 3;
}

.detail-reviews .review-item__toggle {
  margin-top: 0.2rem;
  font-size: 0.8rem;
}

.review-list {
  padding-top: 0.25rem;
}

.review-list--user {
  margin-top: 1.25rem;
}

.comment-compose {
  margin-bottom: 0.5rem;
}

.comment-compose__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.65rem;
  margin-bottom: 0.65rem;
}

.comment-compose__input {
  width: 100%;
  resize: vertical;
  min-height: 6rem;
  border-radius: 8px;
  border: 1px solid var(--fywz-border);
  background: var(--fywz-surface-2);
  padding: 0.75rem 0.85rem;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--fywz-text);
}

.comment-compose__input:focus {
  outline: none;
  border-color: #01b4e4;
}

.comment-compose__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.75rem;
}

.comment-compose__submit {
  border-radius: 999px;
  border: none;
  background: #01b4e4;
  padding: 0.45rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #042541;
  cursor: pointer;
}

.comment-compose__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.comment-compose__delete {
  border-radius: 999px;
  border: 1px solid var(--fywz-border);
  background: transparent;
  padding: 0.45rem 1.1rem;
  font-size: 0.9rem;
  color: var(--fywz-muted);
  cursor: pointer;
}

.comment-login-hint,
.comment-empty {
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
  color: var(--fywz-muted);
}

.review-item__time {
  margin-left: auto;
  font-size: 0.8rem;
  color: var(--fywz-muted);
}

.review-item {
  padding: 1.15rem 0;
  border-bottom: 1px solid var(--fywz-border);
  border-radius: 0.75rem;
  transition: background-color 0.25s ease, box-shadow 0.25s ease;
}

.review-item--highlight {
  background: rgba(1, 180, 228, 0.1);
  box-shadow: inset 0 0 0 1px rgba(1, 180, 228, 0.35);
}

.review-item:last-child {
  border-bottom: none;
}

.review-item__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.65rem;
  margin-bottom: 0.55rem;
}

.review-item__author {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--fywz-link);
}

.review-item__toggle {
  border: none;
  background: none;
  padding: 0;
  font-size: 0.9rem;
  color: var(--fywz-link);
  cursor: pointer;
}

.review-item__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.review-item__toggle:disabled {
  opacity: 0.6;
  cursor: wait;
}

.review-item__tag {
  font-size: 0.85rem;
  color: var(--fywz-muted);
}

.review-item__stars {
  height: auto;
}

.review-item__stars :deep(.el-rate__icon) {
  font-size: 0.95rem;
  margin-right: 1px;
}

.review-item__score {
  font-size: 0.85rem;
  color: var(--fywz-muted);
}

.review-item__body {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--fywz-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.review-item__body--collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: normal;
}

.review-item__toggle:hover {
  text-decoration: underline;
}
</style>
