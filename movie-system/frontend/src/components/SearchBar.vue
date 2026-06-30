<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { movieApi } from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  variant: { type: String, default: 'hero' },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const router = useRouter()
const keyword = ref(props.modelValue)
const suggestions = ref([])
const open = ref(false)
let timer = null

watch(
  () => props.modelValue,
  (val) => {
    keyword.value = val
  },
)

watch(keyword, (val) => {
  emit('update:modelValue', val)
  clearTimeout(timer)
  if (!val.trim()) {
    suggestions.value = []
    open.value = false
    return
  }
  timer = setTimeout(async () => {
    const { data } = await movieApi.search(val.trim())
    suggestions.value = data.items
    open.value = data.items.length > 0
  }, 250)
})

function goSearch() {
  if (!keyword.value.trim()) return
  open.value = false
  emit('submit', keyword.value.trim())
  router.push({ name: 'movies', query: { q: keyword.value.trim() } })
}

function pick(item) {
  open.value = false
  router.push({ name: 'movie-detail', params: { id: item.movie_id } })
}
</script>

<template>
  <div class="relative w-full">
    <div
      class="flex items-center overflow-hidden shadow-lg"
      :class="
        variant === 'hero'
          ? 'rounded-full bg-white'
          : 'rounded-full bg-white/10 ring-1 ring-white/10'
      "
    >
      <input
        v-model="keyword"
        class="w-full bg-transparent px-5 py-3.5 text-base outline-none"
        :class="variant === 'hero' ? 'text-[#032541] placeholder:text-gray-400' : 'text-white placeholder:text-[#9aa5b1]'"
        placeholder="搜索电影、电视节目、人物……"
        @keyup.enter="goSearch"
        @focus="open = suggestions.length > 0"
      />
      <button
        class="m-1 shrink-0 rounded-full px-6 py-2.5 text-sm font-bold transition hover:brightness-110"
        :class="variant === 'hero' ? 'bg-[#01B4E4] text-white' : 'text-[#01B4E4]'"
        @click="goSearch"
      >
        搜索
      </button>
    </div>
    <div
      v-if="open"
      class="absolute z-50 mt-2 w-full overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl"
    >
      <button
        v-for="item in suggestions"
        :key="item.movie_id"
        class="flex w-full items-center justify-between px-5 py-3 text-left text-[#032541] hover:bg-gray-50"
        @click="pick(item)"
      >
        <span class="font-medium">{{ item.title }}</span>
        <span class="text-sm text-gray-500">{{ item.release_year }} · {{ item.rating?.toFixed?.(1) || item.rating }}</span>
      </button>
    </div>
  </div>
</template>
