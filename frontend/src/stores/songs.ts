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
  const favoritesOnly = ref(false)

  // Favorites state - 当前列表页的歌曲收藏状态
  const favorites = ref<Set<number>>(new Set())

  // 选中歌曲的收藏状态 - 独立缓存，不随列表刷新而丢失
  const selectedSongFavorite = ref<boolean>(false)

  // Client-side filter options (for local filtering if needed)
  const filterOptions = ref<FilterOptions>({
    search: '',
    difficulties: [],
    hiddenOnly: false,
    sortBy: 'pvId',
    sortOrder: 'asc',
    favoritesOnly: false,
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

  const isFavorite = computed(() => (songId: number) => {
    // 如果是当前选中歌曲，优先使用独立的缓存
    if (songId === selectedId.value) {
      return selectedSongFavorite.value
    }
    // 否则从列表缓存中查询
    return favorites.value.has(songId)
  })

  // Actions
  async function loadSongs(page: number = 1, query: string = '', resetFavorites: boolean = false) {
    loading.value = true
    error.value = null
    try {
      // 列表刷新时清空 favorites
      if (resetFavorites) {
        favorites.value.clear()
      }

      const response = await songApi.getSongs({
        page,
        pageSize: pageSize.value,
        search: query || undefined,
        favorites: favoritesOnly.value,
      })

      const data: SongListResponse = response.data.data
      songs.value = data.songs || []
      total.value = data.total || 0
      currentPage.value = data.page || page
      totalPages.value = data.totalPages || 1

      // Update favorites set from song data (merge, don't replace)
      data.songs?.forEach(song => {
        if (song.isFavorite) {
          favorites.value.add(song.id)
        } else {
          favorites.value.delete(song.id)
        }
        // 如果选中歌曲在新列表中，同步更新其收藏状态
        if (song.id === selectedId.value) {
          selectedSongFavorite.value = song.isFavorite || false
        }
      })
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

      // 清空并重新加载 favorites
      favorites.value.clear()
      data.songs?.forEach(song => {
        if (song.isFavorite) {
          favorites.value.add(song.id)
        }
      })

      ElMessage.success(`歌曲列表已刷新，共 ${data.total} 首歌曲`)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to reload songs'
      ElMessage.error('刷新歌曲列表失败')
    } finally {
      reloading.value = false
    }
  }

  async function changePage(page: number) {
    await loadSongs(page, searchQuery.value, true)
  }

  async function changePageSize(size: number) {
    pageSize.value = size
    currentPage.value = 1
    await loadSongs(1, searchQuery.value, true)
  }

  async function searchSongs(query: string) {
    searchQuery.value = query
    currentPage.value = 1
    await loadSongs(1, query, true) // 搜索时清空 favorites
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

  function setFavoritesOnly(value: boolean) {
    favoritesOnly.value = value
    filterOptions.value.favoritesOnly = value
    currentPage.value = 1
    loadSongs(1, searchQuery.value, true) // 切换收藏筛选时清空 favorites
  }

  async function loadFavorites() {
    try {
      const response = await songApi.getFavorites()
      const favoriteIds = response.data.data || []
      favorites.value = new Set(favoriteIds)
    } catch (err) {
      console.error('Failed to load favorites:', err)
    }
  }

  async function toggleFavorite(songId: number) {
    try {
      const response = await songApi.toggleFavorite(songId)
      const isFav = response.data.data.isFavorite

      if (isFav) {
        favorites.value.add(songId)
      } else {
        favorites.value.delete(songId)
      }

      // Update song in current list if present
      const song = songs.value.find(s => s.id === songId)
      if (song) {
        song.isFavorite = isFav
      }

      // 如果是当前选中歌曲，同步更新独立缓存
      if (songId === selectedId.value) {
        selectedSongFavorite.value = isFav
      }

      return isFav
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to toggle favorite'
      ElMessage.error(errorMsg)
      return null
    }
  }

  async function selectSong(song: Song) {
    selectedId.value = song.id
    // 选择新歌曲时重置难度选择
    selectedDifficulty.value = null
    // 直接使用列表中的歌曲数据，只需要单独获取收藏状态
    selectedSongFavorite.value = song.isFavorite || false
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
    favorites,
    favoritesOnly,
    // Getters
    allSongs,
    hasSongs,
    songById,
    songByPvId,
    isFavorite,
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
    setFavoritesOnly,
    loadFavorites,
    toggleFavorite,
    selectSong,
    selectDifficulty,
    switchToCurrentSong,
  }
})
