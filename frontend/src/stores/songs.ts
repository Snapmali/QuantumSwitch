import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { songApi, gameApi } from '@/api'
import type { Song, SongListResponse, FilterOptions, DifficultyType } from '@/types'
import { ElMessage } from 'element-plus'

export const useSongStore = defineStore('songs', () => {
  // State
  const songs = ref<Song[]>([])
  const loading = ref(false)
  const reloading = ref(false)
  const error = ref<string | null>(null)
  const selectedId = ref<number | null>(null)
  const selectedDifficulty = ref<string | null>(null)

  // Pagination state
  const currentPage = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const totalPages = ref(1)

  // Filter state (for server-side filtering)
  const searchQuery = ref('')

  // Client-side filter options (for local filtering if needed)
  const filterOptions = ref<FilterOptions>({
    search: '',
    difficulties: [],
    hiddenOnly: false,
    sortBy: 'pvId',
    sortOrder: 'asc',
  })

  // Getters
  const allSongs = computed(() => songs.value)
  const hasSongs = computed(() => songs.value.length > 0)

  const songById = computed(() => (id: number) => {
    return songs.value.find(song => song.id === id)
  })

  const songByPvId = computed(() => (pvId: number) => {
    return songs.value.find(song => song.id === pvId)
  })

  // Actions
  async function loadSongs(page: number = 1, query: string = '') {
    loading.value = true
    error.value = null
    try {
      const response = await songApi.getAll({
        page,
        pageSize: pageSize.value,
        search: query || undefined,
      })

      const data: SongListResponse = response.data.data
      songs.value = data.songs || []
      total.value = data.total || 0
      currentPage.value = data.page || page
      totalPages.value = data.totalPages || 1
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load songs'
      songs.value = []
    } finally {
      loading.value = false
    }
  }

  async function reloadSongs() {
    reloading.value = true
    error.value = null
    try {
      const response = await songApi.reload()
      const data: SongListResponse = response.data.data

      songs.value = data.songs || []
      total.value = data.total || 0
      currentPage.value = 1
      totalPages.value = data.totalPages || 1
      ElMessage.success(`歌曲列表已刷新，共 ${data.total} 首歌曲`)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to reload songs'
      ElMessage.error('刷新歌曲列表失败')
    } finally {
      reloading.value = false
    }
  }

  async function changePage(page: number) {
    await loadSongs(page, searchQuery.value)
  }

  async function changePageSize(size: number) {
    pageSize.value = size
    currentPage.value = 1
    await loadSongs(1, searchQuery.value)
  }

  async function searchSongs(query: string) {
    searchQuery.value = query
    currentPage.value = 1
    await loadSongs(1, query)
  }

  function setDifficultyFilter(difficulties: DifficultyType[]) {
    filterOptions.value.difficulties = difficulties
  }

  function setHiddenOnly(hiddenOnly: boolean) {
    filterOptions.value.hiddenOnly = hiddenOnly
  }

  function setSortBy(sortBy: FilterOptions['sortBy']) {
    filterOptions.value.sortBy = sortBy
  }

  function setSortOrder(sortOrder: FilterOptions['sortOrder']) {
    filterOptions.value.sortOrder = sortOrder
  }

  function selectSong(id: number) {
    selectedId.value = id
    // 选择新歌曲时重置难度选择
    selectedDifficulty.value = null
  }

  function selectDifficulty(difficulty: string) {
    selectedDifficulty.value = difficulty
  }

  async function switchToCurrentSong() {
    if (!selectedId.value || !selectedDifficulty.value) {
      ElMessage.warning('请先选择歌曲和难度')
      return false
    }

    // 将难度名称转换为难度类型数值
    const difficultyMap: Record<string, number> = {
      'EASY': 0,
      'NORMAL': 1,
      'HARD': 2,
      'EXTREME': 3,
      'EXTRA EXTREME': 4,
    }

    const difficultyValue = difficultyMap[selectedDifficulty.value]
    if (difficultyValue === undefined) {
      ElMessage.error('未知的难度类型')
      return false
    }

    try {
      const response = await gameApi.switchSong({
        songId: selectedId.value,
        difficulty: difficultyValue,
      })

      const result = response.data.data

      if (result.success) {
        ElMessage.success(result.message)
        return true
      } else {
        ElMessage.error(result.message)
        return false
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '切换歌曲失败'
      ElMessage.error(errorMsg)
      return false
    }
  }

  return {
    // State
    songs,
    loading,
    reloading,
    error,
    selectedId,
    selectedDifficulty,
    currentPage,
    pageSize,
    total,
    totalPages,
    searchQuery,
    filterOptions,
    // Getters
    allSongs,
    hasSongs,
    songById,
    songByPvId,
    // Actions
    loadSongs,
    reloadSongs,
    changePage,
    changePageSize,
    searchSongs,
    setDifficultyFilter,
    setHiddenOnly,
    setSortBy,
    setSortOrder,
    selectSong,
    selectDifficulty,
    switchToCurrentSong,
  }
})
