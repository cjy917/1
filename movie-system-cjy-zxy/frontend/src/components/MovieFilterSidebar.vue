<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  filters: { type: Object, default: () => ({ years: [], genres: [], languages: [] }) },
  query: { type: Object, required: true },
})

const emit = defineEmits(['apply', 'reset'])

const sortOpen = ref(false)
const filtersOpen = ref(true)

const draft = reactive({
  q: '',
  selectedGenres: [],
  selectedLanguages: [],
  year_from: '',
  year_to: '',
  sort: 'rating_desc',
  min_rating: '',
  max_rating: '',
  min_votes: 0,
})

const sortOptions = [
  { value: 'popular', label: '热门降序' },
  { value: 'popular_asc', label: '热门升序' },
  { value: 'rating_desc', label: '评分降序' },
  { value: 'rating_asc', label: '评分升序' },
  { value: 'year_desc', label: '发行日期降序' },
  { value: 'year_asc', label: '发行日期升序' },
]

function syncDraftFromQuery() {
  draft.q = props.query.q || ''
  draft.selectedGenres = [...(props.query.selectedGenres || [])]
  draft.selectedLanguages = [...(props.query.selectedLanguages || [])]
  draft.year_from = props.query.year_from || ''
  draft.year_to = props.query.year_to || ''
  draft.sort = props.query.sort || 'rating_desc'
  draft.min_rating = props.query.min_rating ?? ''
  draft.max_rating = props.query.max_rating ?? ''
  draft.min_votes = Number(props.query.min_votes || 0)
}

watch(
  () => props.query,
  () => syncDraftFromQuery(),
  { deep: true, immediate: true },
)

const ratingRange = computed({
  get() {
    const min = draft.min_rating === '' ? 0 : Number(draft.min_rating)
    const max = draft.max_rating === '' ? 10 : Number(draft.max_rating)
    return [Number.isNaN(min) ? 0 : min, Number.isNaN(max) ? 10 : max]
  },
  set([min, max]) {
    draft.min_rating = min <= 0 ? '' : String(min)
    draft.max_rating = max >= 10 ? '' : String(max)
  },
})

const minVotes = computed({
  get: () => Number(draft.min_votes || 0),
  set: (value) => {
    draft.min_votes = value
  },
})

function onSortChange(event) {
  draft.sort = event.target.value
}

function onYearChange(field, event) {
  const value = event.target.value
  draft[field] = value
  const from = field === 'year_from' ? value : draft.year_from
  const to = field === 'year_to' ? value : draft.year_to
  if (from && to && Number(from) > Number(to)) {
    if (field === 'year_from') draft.year_to = value
    else draft.year_from = value
  }
}

function toggleGenre(genre) {
  const index = draft.selectedGenres.indexOf(genre)
  if (index >= 0) draft.selectedGenres.splice(index, 1)
  else draft.selectedGenres.push(genre)
}

function toggleLanguage(language) {
  const index = draft.selectedLanguages.indexOf(language)
  if (index >= 0) draft.selectedLanguages.splice(index, 1)
  else draft.selectedLanguages.push(language)
}

function isGenreActive(genre) {
  return draft.selectedGenres.includes(genre)
}

function isLanguageActive(language) {
  return draft.selectedLanguages.includes(language)
}

function submitSearch() {
  emit('apply', {
    q: draft.q.trim(),
    selectedGenres: [...draft.selectedGenres],
    selectedLanguages: [...draft.selectedLanguages],
    year_from: draft.year_from,
    year_to: draft.year_to,
    sort: draft.sort,
    min_rating: draft.min_rating,
    max_rating: draft.max_rating,
    min_votes: draft.min_votes,
  }, true)
}

function resetFilters() {
  Object.assign(draft, {
    q: '',
    selectedGenres: [],
    selectedLanguages: [],
    year_from: '',
    year_to: '',
    sort: 'rating_desc',
    min_rating: '',
    max_rating: '',
    min_votes: 0,
  })
  emit('reset')
}
</script>

<template>
  <aside class="movie-filter-sidebar">
    <div class="filter-card">
      <button type="button" class="filter-card__header" @click="sortOpen = !sortOpen">
        <span>排序</span>
        <svg
          class="filter-card__chevron"
          :class="{ 'filter-card__chevron--open': sortOpen }"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
      <div v-show="sortOpen" class="filter-card__body">
        <label class="filter-label">结果排序</label>
        <select :value="draft.sort" class="filter-input filter-input--select" @change="onSortChange">
          <option v-for="item in sortOptions" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>
      </div>
    </div>

    <div class="filter-card">
      <button type="button" class="filter-card__header" @click="filtersOpen = !filtersOpen">
        <span>筛选</span>
        <svg
          class="filter-card__chevron"
          :class="{ 'filter-card__chevron--open': filtersOpen }"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clip-rule="evenodd"
          />
        </svg>
      </button>

      <div v-show="filtersOpen" class="filter-card__body filter-card__body--stacked">
        <section class="filter-block">
          <h4 class="filter-block__title">发行日期</h4>
          <p class="filter-block__hint">按上映年份筛选</p>
          <div class="filter-year-row">
            <label class="filter-year-field">
              <span>从</span>
              <select
                :value="draft.year_from"
                class="filter-input"
                @change="onYearChange('year_from', $event)"
              >
                <option value="">不限</option>
                <option v-for="y in filters.years" :key="`from-${y}`" :value="String(y)">{{ y }}</option>
              </select>
            </label>
            <label class="filter-year-field">
              <span>到</span>
              <select
                :value="draft.year_to"
                class="filter-input"
                @change="onYearChange('year_to', $event)"
              >
                <option value="">不限</option>
                <option v-for="y in filters.years" :key="`to-${y}`" :value="String(y)">{{ y }}</option>
              </select>
            </label>
          </div>
        </section>

        <section class="filter-block">
          <h4 class="filter-block__title">类型</h4>
          <p class="filter-block__hint">可多选，匹配任一类型即可</p>
          <div class="genre-chips">
            <button
              v-for="genre in filters.genres"
              :key="genre"
              type="button"
              class="genre-chip"
              :class="{ 'genre-chip--active': isGenreActive(genre) }"
              @click="toggleGenre(genre)"
            >
              {{ genre }}
            </button>
          </div>
        </section>

        <section class="filter-block">
          <h4 class="filter-block__title">语言</h4>
          <p class="filter-block__hint">可多选，匹配任一语言即可</p>
          <div class="genre-chips">
            <button
              v-for="language in filters.languages"
              :key="language"
              type="button"
              class="genre-chip"
              :class="{ 'genre-chip--active': isLanguageActive(language) }"
              @click="toggleLanguage(language)"
            >
              {{ language }}
            </button>
          </div>
        </section>

        <section class="filter-block">
          <h4 class="filter-block__title">用户评分</h4>
          <el-slider
            v-model="ratingRange"
            class="filter-slider"
            range
            :min="0"
            :max="10"
            :step="0.5"
            :show-tooltip="false"
          />
          <div class="filter-slider-scale">
            <span>0</span>
            <span>5</span>
            <span>10</span>
          </div>
        </section>

        <section class="filter-block">
          <h4 class="filter-block__title">最少人数投票</h4>
          <el-slider
            v-model="minVotes"
            class="filter-slider"
            :min="0"
            :max="500"
            :step="50"
            :show-tooltip="false"
          />
          <div class="filter-slider-scale filter-slider-scale--wide">
            <span>0</span>
            <span>100</span>
            <span>200</span>
            <span>300</span>
            <span>400</span>
            <span>500</span>
          </div>
        </section>

        <section class="filter-block filter-block--last">
          <h4 class="filter-block__title">关键词</h4>
          <input
            v-model="draft.q"
            class="filter-input filter-input--keyword"
            placeholder="按关键词筛选…"
            @keyup.enter="submitSearch"
          />
        </section>

        <div class="filter-actions">
          <button type="button" class="filter-actions__search" @click="submitSearch">
            搜索
          </button>
          <button type="button" class="filter-actions__reset" @click="resetFilters">
            重置
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.movie-filter-sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.filter-card {
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  border-radius: 8px;
  background: var(--fywz-filter-bg, #fff);
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.05);
}

.filter-card__header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  border: none;
  background: transparent;
  padding: 0.85rem 1rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--fywz-text);
  cursor: pointer;
}

.filter-card__chevron {
  width: 1.1rem;
  height: 1.1rem;
  color: var(--fywz-muted);
  transition: transform 0.2s;
}

.filter-card__chevron--open {
  transform: rotate(180deg);
}

.filter-card__body {
  padding: 0 1rem 1rem;
}

.filter-card__body--stacked {
  padding-top: 0;
}

.filter-label {
  display: block;
  margin-bottom: 0.45rem;
  font-size: 0.85rem;
  color: var(--fywz-muted);
}

.filter-block {
  padding: 0.95rem 0;
  border-bottom: 1px solid var(--fywz-filter-border, #e3e3e3);
}

.filter-block--last {
  border-bottom: none;
  padding-bottom: 0.25rem;
}

.filter-block__title {
  margin: 0 0 0.65rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--fywz-text);
}

.filter-block__hint {
  margin: -0.35rem 0 0.55rem;
  font-size: 0.75rem;
  color: var(--fywz-muted);
}

.filter-year-row {
  display: grid;
  gap: 0.65rem;
}

.filter-year-field {
  display: grid;
  grid-template-columns: 1.5rem 1fr;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: var(--fywz-muted);
}

.filter-input {
  width: 100%;
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  border-radius: 8px;
  background: var(--fywz-filter-bg, #fff);
  padding: 0.45rem 0.65rem;
  font-size: 0.875rem;
  color: var(--fywz-text);
  outline: none;
}

.filter-input:focus {
  border-color: #01b4e4;
}

.filter-input--keyword {
  padding: 0.55rem 0.75rem;
}

.filter-input--select {
  min-height: 38px;
  cursor: pointer;
  padding-right: 2rem;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%2352606d'%3E%3Cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z' clip-rule='evenodd'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.55rem center;
  background-size: 1rem;
  appearance: none;
}

.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.genre-chip {
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  border-radius: 999px;
  background: var(--fywz-filter-bg, #fff);
  padding: 0.28rem 0.72rem;
  font-size: 0.82rem;
  line-height: 1.35;
  color: var(--fywz-text);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.genre-chip:hover {
  border-color: #01b4e4;
}

.genre-chip--active {
  border-color: #01b4e4;
  background: #01b4e4;
  color: #042541;
  font-weight: 600;
}

.filter-slider {
  margin: 0 0.35rem;
}

.filter-slider :deep(.el-slider__runway) {
  height: 4px;
  background: #d5dbe3;
}

.filter-slider :deep(.el-slider__bar) {
  background: #01b4e4;
}

.filter-slider :deep(.el-slider__button) {
  width: 16px;
  height: 16px;
  border: none;
  background: #01b4e4;
}

.filter-slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.35rem;
  font-size: 0.75rem;
  color: var(--fywz-muted);
}

.filter-slider-scale--wide {
  font-size: 0.7rem;
}

.filter-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  padding-top: 0.85rem;
}

.filter-actions__search,
.filter-actions__reset {
  border-radius: 999px;
  padding: 0.62rem 0.85rem;
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
  transition: filter 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.filter-actions__search {
  border: none;
  background: #01b4e4;
  color: #032541;
}

.filter-actions__search:hover {
  filter: brightness(1.05);
}

.filter-actions__reset {
  border: 1px solid var(--fywz-filter-border, #e3e3e3);
  background: var(--fywz-filter-bg, #fff);
  color: var(--fywz-text);
}

.filter-actions__reset:hover {
  border-color: #01b4e4;
  color: #01b4e4;
}
</style>
