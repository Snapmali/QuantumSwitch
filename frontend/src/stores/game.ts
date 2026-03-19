import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gameApi } from '@/api'
import type { GameStatus, GameStatusDisplay, SwitchSongRequest } from '@/types'
import { ElMessage } from 'element-plus'
import { useSongStore } from './songs'

export const useGameStore = defineStore('game', () => {
  // State
  const status = ref<GameStatus>({
    running: false,
    processId: undefined,
    currentSongId: undefined,
    currentSortId: undefined,
    currentDifficulty: undefined,
    currentDifficultyName: undefined,
    gameState: undefined,
    edenVersion: false,
    edenOffset: 0,
    currentSongInfo: undefined,
    currentChartStyle: undefined,
    isIngame: undefined,
  })
  const switching = ref(false)
  const loading = ref(false)
  const autoRefresh = ref(true)
  const refreshIntervalMs = ref(5000)
  const refreshIntervalId = ref<number | null>(null)

  // Getters
  const isRunning = computed(() => status.value.running)
  const isReady = computed(() => status.value.running && status.value.gameState === 6)
  const isBusy = computed(() => status.value.running && status.value.gameState === 5)
  const currentState = computed(() => status.value.gameState)
  const currentPvId = computed(() => status.value.currentSongId)
  const currentDifficulty = computed(() => status.value.currentDifficulty)
  const edenDetected = computed(() => status.value.edenVersion)
  const edenOffset = computed(() => status.value.edenOffset)

  // Convert to display format for GameStatus component
  const statusDisplay = computed((): GameStatusDisplay | null => {
    const s = status.value
    if (!s) return null

    // Determine status string
    let statusStr: 'running' | 'not_running' | 'busy' | 'error' = 'not_running'
    if (s.running) {
      if (s.gameState === 5) {
        statusStr = 'busy'
      } else if (s.gameState === 6) {
        statusStr = 'running'
      } else {
        statusStr = 'running'
      }
    }

    const display: GameStatusDisplay = {
      status: statusStr,
      isEdenVersion: s.edenVersion,
      edenOffset: s.edenOffset,
      currentSongInfo: s.currentSongInfo,
      currentChartStyle: s.currentChartStyle,
      isIngame: s.isIngame,
    }

    // Add current song info if available
    if (s.currentSongId && s.currentDifficultyName) {
      // Try to get actual song name from songs store
      const songsStore = useSongStore()
      const songInfo = songsStore.songByPvId(s.currentSongId)
      display.currentSong = {
        name: songInfo?.name || `PV ${s.currentSongId}`,
        difficultyType: s.currentDifficultyName,
      }
    }

    return display
  })

  // Actions
  async function refreshStatus() {
    loading.value = true
    try {
      const response = await gameApi.getStatus()
      // Backend now returns camelCase directly, no mapping needed
      status.value = response.data.data
    } catch (err) {
      // Silent fail - game might not be running
      status.value.running = false
    } finally {
      loading.value = false
    }
  }

  async function switchSong(data: SwitchSongRequest) {
    switching.value = true
    try {
      const response = await gameApi.switchSong(data)
      const result = response.data.data

      if (result.success) {
        ElMessage.success(result.message)
      } else {
        ElMessage.error(result.message)
      }

      return result
    } catch (err) {
      ElMessage.error('Failed to switch song')
      return null
    } finally {
      switching.value = false
    }
  }

  function startAutoRefresh() {
    if (refreshIntervalId.value) return
    refreshIntervalId.value = window.setInterval(() => {
      refreshStatus()
    }, refreshIntervalMs.value)
  }

  function stopAutoRefresh() {
    if (refreshIntervalId.value) {
      clearInterval(refreshIntervalId.value)
      refreshIntervalId.value = null
    }
  }

  function setAutoRefresh(enabled: boolean) {
    autoRefresh.value = enabled
    if (enabled) {
      startAutoRefresh()
    } else {
      stopAutoRefresh()
    }
  }

  function setRefreshInterval(seconds: number) {
    const newMs = seconds * 1000
    if (newMs !== refreshIntervalMs.value) {
      refreshIntervalMs.value = newMs
      // Restart auto-refresh if it's running
      if (autoRefresh.value && refreshIntervalId.value) {
        stopAutoRefresh()
        startAutoRefresh()
      }
    }
  }

  return {
    status,
    switching,
    loading,
    autoRefresh,
    refreshIntervalMs,
    isRunning,
    isReady,
    isBusy,
    currentState,
    currentPvId,
    currentDifficulty,
    edenDetected,
    edenOffset,
    statusDisplay,
    refreshStatus,
    switchSong,
    startAutoRefresh,
    stopAutoRefresh,
    setAutoRefresh,
    setRefreshInterval,
  }
})
