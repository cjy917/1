<template>
  <!-- 筛选栏组件 -->
  <div class="filter-bar">
    <div class="filter-group">
      <!-- 类型筛选 -->
      <div class="filter-section">
        <span class="filter-label">类型</span>
        <div class="filter-tags">
          <button
            v-for="genre in genres"
            :key="genre"
            @click="toggleGenre(genre)"
            :class="['filter-tag', { active: selectedGenres.includes(genre) }]"
          >
            {{ genre }}
          </button>
          <button
            v-if="selectedGenres.length > 0"
            @click="clearGenres"
            class="filter-tag clear-tag"
          >
            清除
          </button>
        </div>
      </div>

      <!-- 年份筛选 -->
      <div class="filter-section">
        <span class="filter-label">年份</span>
        <div class="filter-tags">
          <button
            v-for="year in years"
            :key="year"
            @click="toggleYear(year)"
            :class="['filter-tag', { active: selectedYears.includes(year) }]"
          >
            {{ year }}
          </button>
          <button
            v-if="selectedYears.length > 0"
            @click="clearYears"
            class="filter-tag clear-tag"
          >
            清除
          </button>
        </div>
      </div>

      <!-- 国家筛选 -->
      <div class="filter-section">
        <span class="filter-label">国家</span>
        <div class="filter-tags">
          <button
            v-for="country in countries"
            :key="country"
            @click="toggleCountry(country)"
            :class="['filter-tag', { active: selectedCountries.includes(country) }]"
          >
            {{ country }}
          </button>
          <button
            v-if="selectedCountries.length > 0"
            @click="clearCountries"
            class="filter-tag clear-tag"
          >
            清除
          </button>
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="filter-footer">
      <p v-if="hasActiveFilters" class="filter-hint">
        已选 {{ activeCount }} 项筛选条件
      </p>
      <div class="filter-actions">
        <button
          v-if="hasActiveFilters"
          @click="handleClear"
          class="action-btn action-btn-ghost"
        >
          清除全部
        </button>
        <button @click="handleSearch" class="action-btn action-btn-primary">
          <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20L16.5 16.5" stroke-linecap="round" />
          </svg>
          搜索
        </button>
        <ExportBtn :data="exportData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import ExportBtn from './ExportBtn.vue'

/**
 * 筛选栏组件
 * 
 * 提供类型、年份、国家三个维度的筛选功能
 * 支持多选、清除和搜索操作
 */

const props = defineProps({
  /** 类型列表 */
  genres: {
    type: Array,
    default: () => []
  },
  /** 年份列表 */
  years: {
    type: Array,
    default: () => []
  },
  /** 国家列表 */
  countries: {
    type: Array,
    default: () => []
  },
  /** 当前筛选条件 */
  filters: {
    type: Object,
    default: () => ({})
  },
  /** 导出数据 */
  exportData: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:filters', 'search'])

const selectedGenres = ref(props.filters.genre ? props.filters.genre.split(',') : [])
const selectedYears = ref(parseYearTokens(props.filters.year))

/** 解析年份字符串为数组 */
function parseYearTokens(yearStr) {
  if (!yearStr) return []
  return yearStr.split(',').map((token) => {
    const trimmed = token.trim()
    if (trimmed === '更早') return '更早'
    const parsed = parseInt(trimmed, 10)
    return Number.isNaN(parsed) ? trimmed : parsed
  })
}

const selectedCountries = ref(props.filters.country ? props.filters.country.split(',') : [])

/** 是否有激活的筛选条件 */
const hasActiveFilters = computed(() => {
  return selectedGenres.value.length > 0 || selectedYears.value.length > 0 || selectedCountries.value.length > 0
})

/** 激活的筛选条件数量 */
const activeCount = computed(() => {
  return selectedGenres.value.length + selectedYears.value.length + selectedCountries.value.length
})

/** 获取当前筛选条件对象 */
function currentFilters() {
  return {
    genre: selectedGenres.value.length > 0 ? selectedGenres.value.join(',') : null,
    year: selectedYears.value.length > 0 ? selectedYears.value.join(',') : null,
    country: selectedCountries.value.length > 0 ? selectedCountries.value.join(',') : null
  }
}

/** 同步筛选条件到父组件 */
function syncFilters() {
  emit('update:filters', currentFilters())
}

/** 处理搜索按钮点击 */
function handleSearch() {
  syncFilters()
  emit('search')
}

/** 切换类型选中状态 */
function toggleGenre(genre) {
  const index = selectedGenres.value.indexOf(genre)
  if (index > -1) {
    selectedGenres.value.splice(index, 1)
  } else {
    selectedGenres.value.push(genre)
  }
}

/** 切换年份选中状态 */
function toggleYear(year) {
  const index = selectedYears.value.indexOf(year)
  if (index > -1) {
    selectedYears.value.splice(index, 1)
  } else {
    selectedYears.value.push(year)
  }
}

/** 切换国家选中状态 */
function toggleCountry(country) {
  const index = selectedCountries.value.indexOf(country)
  if (index > -1) {
    selectedCountries.value.splice(index, 1)
  } else {
    selectedCountries.value.push(country)
  }
}

/** 清除类型筛选 */
function clearGenres() {
  selectedGenres.value = []
}

/** 清除年份筛选 */
function clearYears() {
  selectedYears.value = []
}

/** 清除国家筛选 */
function clearCountries() {
  selectedCountries.value = []
}

/** 清除所有筛选条件 */
function handleClear() {
  selectedGenres.value = []
  selectedYears.value = []
  selectedCountries.value = []
  syncFilters()
  emit('search')
}

/** 监听外部筛选条件变化 */
watch(() => props.filters, (newFilters) => {
  selectedGenres.value = newFilters.genre ? newFilters.genre.split(',') : []
  selectedYears.value = parseYearTokens(newFilters.year)
  selectedCountries.value = newFilters.country ? newFilters.country.split(',') : []
}, { deep: true })
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 24px 28px 20px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 20px;
  margin-bottom: 32px;
  box-shadow: var(--shadow-sm);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.filter-section {
  display: grid;
  grid-template-columns: 52px 1fr;
  align-items: start;
  gap: 12px 16px;
}

.filter-label {
  padding-top: 7px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted-foreground);
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-tag {
  padding: 6px 14px;
  background: var(--secondary);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--card-foreground);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, color 180ms ease, transform 120ms ease;
  white-space: nowrap;
}

.filter-tag:hover {
  background: var(--accent);
  border-color: color-mix(in srgb, var(--primary) 25%, var(--border));
}

.filter-tag:active {
  transform: scale(0.97);
}

.filter-tag.active {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-foreground);
  box-shadow: 0 2px 8px color-mix(in srgb, var(--primary) 35%, transparent);
}

.filter-tag.clear-tag {
  background: transparent;
  border-color: color-mix(in srgb, var(--destructive) 45%, var(--border));
  color: var(--destructive);
  box-shadow: none;
}

.filter-tag.clear-tag:hover {
  background: var(--destructive);
  border-color: var(--destructive);
  color: var(--destructive-foreground);
}

.filter-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
}

.filter-hint {
  margin: 0;
  font-size: 13px;
  color: var(--muted-foreground);
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 42px;
  padding: 0 22px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease, transform 120ms ease;
  white-space: nowrap;
}

.action-btn:active {
  transform: scale(0.98);
}

.action-icon {
  width: 17px;
  height: 17px;
  flex-shrink: 0;
}

.action-btn-primary {
  background: var(--primary);
  border: none;
  color: var(--primary-foreground);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--primary) 32%, transparent);
}

.action-btn-primary:hover {
  box-shadow: 0 6px 18px color-mix(in srgb, var(--primary) 40%, transparent);
  filter: brightness(1.05);
}

.action-btn-ghost {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted-foreground);
}

.action-btn-ghost:hover {
  background: var(--secondary);
  color: var(--card-foreground);
  border-color: color-mix(in srgb, var(--foreground) 12%, var(--border));
}

@media (max-width: 640px) {
  .filter-bar {
    padding: 20px 18px 16px;
  }

  .filter-section {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .filter-label {
    padding-top: 0;
  }

  .filter-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-actions {
    margin-left: 0;
    justify-content: stretch;
  }

  .action-btn {
    flex: 1;
  }
}
</style>
