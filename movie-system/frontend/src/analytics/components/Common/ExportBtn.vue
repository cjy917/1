<template>
  <!-- 导出按钮组件 -->
  <div class="export-btn-wrapper">
    <button @click="toggleMenu" class="action-btn action-btn-outline">
      <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
        <path d="M12 3v12" stroke-linecap="round" />
        <path d="M8 11l4 4 4-4" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M4 19h16" stroke-linecap="round" />
      </svg>
      导出数据
    </button>
    <div v-if="showMenu" class="export-menu">
      <button @click="handleExport('csv')" class="export-option">
        <span class="option-label">CSV 表格</span>
        <span class="option-desc">Excel 可直接打开</span>
      </button>
      <button @click="handleExport('json')" class="export-option">
        <span class="option-label">JSON 数据</span>
        <span class="option-desc">完整结构化导出</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 数据导出按钮组件
 * 
 * 支持 CSV 和 JSON 两种格式导出
 * 点击外部自动关闭下拉菜单
 */

const props = defineProps({
  /** 待导出的数据对象 */
  data: {
    type: Object,
    default: () => ({})
  }
})

const showMenu = ref(false)

/** 切换导出菜单显示状态 */
function toggleMenu() {
  showMenu.value = !showMenu.value
}

/** 处理导出操作 */
function handleExport(format) {
  showMenu.value = false

  let content, filename, mimeType

  if (format === 'json') {
    content = JSON.stringify(props.data, null, 2)
    filename = `movie-analytics-${Date.now()}.json`
    mimeType = 'application/json'
  } else {
    content = convertToCSV(props.data)
    filename = `movie-analytics-${Date.now()}.csv`
    mimeType = 'text/csv'
  }

  downloadFile(content, filename, mimeType)
}

/** 将数据转换为 CSV 格式 */
function convertToCSV(data) {
  // 如果包含 movies 数组，使用专门的转换方法
  if (data.movies && Array.isArray(data.movies) && data.movies.length > 0) {
    return moviesToCSV(data.movies)
  }

  // 通用转换：遍历对象键值对
  const rows = []
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value)) {
      rows.push([key, JSON.stringify(value)])
    } else {
      rows.push([key, value])
    }
  }

  return rows.map(row => row.join(',')).join('\n')
}

/** 将电影数据转换为 CSV 格式 */
function moviesToCSV(movies) {
  const headers = ['电影ID', '标题', '评分', '评分人数', '类型', '年份', '导演', '时长', '国家', '语言', '简介', '获奖信息']
  const rows = movies.map(movie => [
    movie.movie_id || '',
    escapeCSV(movie.title || ''),
    movie.rating || '',
    movie.rating_count || '',
    escapeCSV(movie.genres || ''),
    movie.year || '',
    escapeCSV(movie.director || ''),
    movie.duration || '',
    escapeCSV(movie.country || ''),
    escapeCSV(movie.language || ''),
    escapeCSV(movie.summary || ''),
    escapeCSV(movie.awards || '')
  ])

  return [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
}

/** CSV 特殊字符转义 */
function escapeCSV(str) {
  if (str == null) return ''
  const escaped = String(str).replace(/"/g, '""')
  return escaped.includes(',') || escaped.includes('\n') || escaped.includes('"')
    ? `"${escaped}"`
    : escaped
}

/** 下载文件 */
function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/** 点击外部关闭菜单 */
function handleClickOutside(event) {
  if (!event.target.closest('.export-btn-wrapper')) {
    showMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.export-btn-wrapper {
  position: relative;
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

.action-btn-outline {
  background: var(--card);
  border: 1.5px solid color-mix(in srgb, var(--primary) 35%, var(--border));
  color: var(--primary);
}

.action-btn-outline:hover {
  background: color-mix(in srgb, var(--primary) 8%, var(--card));
  border-color: var(--primary);
  box-shadow: 0 2px 10px color-mix(in srgb, var(--primary) 18%, transparent);
}

.export-menu {
  position: absolute;
  bottom: calc(100% + 10px);
  right: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  z-index: 100;
  min-width: 200px;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.export-option {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  color: var(--card-foreground);
  text-align: left;
  cursor: pointer;
  transition: background-color 180ms ease;
}

.export-option + .export-option {
  border-top: 1px solid var(--border);
}

.export-option:hover {
  background: var(--accent);
}

.option-label {
  font-size: 14px;
  font-weight: 600;
}

.option-desc {
  font-size: 12px;
  color: var(--muted-foreground);
}
</style>
