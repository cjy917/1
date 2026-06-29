import { ref } from 'vue'

const searchOpen = ref(false)

export function useSearchPanel() {
  function toggleSearch() {
    searchOpen.value = !searchOpen.value
  }

  function openSearch() {
    searchOpen.value = true
  }

  function closeSearch() {
    searchOpen.value = false
  }

  return { searchOpen, toggleSearch, openSearch, closeSearch }
}
