import { ref, computed } from 'vue'

/**
 * 图表联动交互 Composable
 * 
 * 管理数据分析页面的图表点击交互逻辑，包括：
 * - 筛选条件状态管理（类型、国家、年份、语言）
 * - 钻取详情弹窗控制（导演、演员、电影详情）
 * - 图表点击事件统一处理
 */

export function useChartLinkage() {
  /** 筛选条件状态 */
  const filters = ref({
    genre: null,      // 选中的类型
    country: null,    // 选中的国家
    year: null,       // 选中的年份
    language: null    // 选中的语言
  })

  /** 钻取详情状态 */
  const drilldown = ref({
    visible: false,   // 是否显示
    type: null,       // 钻取类型: 'director' | 'actor' | 'movie'
    data: null        // 钻取数据
  })

  /** 更新筛选条件 */
  function setFilter(key, value) {
    filters.value = {
      ...filters.value,
      [key]: value
    }
  }

  /** 清除所有筛选条件 */
  function clearFilters() {
    filters.value = {
      genre: null,
      country: null,
      year: null,
      language: null
    }
  }

  /** 打开钻取详情弹窗 */
  function openDrilldown(type, data) {
    drilldown.value = {
      visible: true,
      type,
      data
    }
  }

  /** 关闭钻取详情弹窗 */
  function closeDrilldown() {
    drilldown.value = {
      visible: false,
      type: null,
      data: null
    }
  }

  /**
   * 处理图表点击事件
   * 
   * @param {string} chartType - 图表类型（genres/countries/languages/directors/actors/years）
   * @param {Object} params - ECharts 点击参数
   */
  function handleChartClick(chartType, params) {
    const { name, seriesType } = params
    
    switch (seriesType) {
      case 'pie':
        // 饼图点击 - 设置筛选条件
        if (chartType === 'genres' || chartType === 'countries' || chartType === 'languages') {
          const filterKey = chartType === 'genres' ? 'genre' : 
                           chartType === 'countries' ? 'country' : 'language'
          setFilter(filterKey, name)
        }
        break
      case 'bar':
        // 柱状图点击 - 根据图表类型处理
        if (chartType === 'directors') {
          openDrilldown('director', { name, ...params })
        } else if (chartType === 'actors') {
          openDrilldown('actor', { name, ...params })
        } else if (chartType === 'years') {
          setFilter('year', parseInt(name))
        }
        break
    }
  }

  /** 检查是否有激活的筛选条件 */
  const hasActiveFilters = computed(() => {
    return Object.values(filters.value).some(v => v !== null)
  })

  return {
    filters,
    drilldown,
    setFilter,
    clearFilters,
    openDrilldown,
    closeDrilldown,
    handleChartClick,
    hasActiveFilters
  }
}
