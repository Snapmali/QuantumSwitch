import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gameApi } from '@/api'
import type { GameStatus, GameStatusDisplay, SwitchSongRequest } from '@/types'
import { ElMessage } from 'element-plus'

export const useGameStore = defineStore('game', () => {
  // State
  const status = ref<GameStatus>({
    running: false,
    processId: undefined,
    currentSongId: undefined,
    gameState: undefined,
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
  const currentState = computed(() => status.value.gameState)
  const currentPvId = computed(() => status.value.currentSongId)

  // Convert to display format for GameStatus component
  const statusDisplay = computed((): GameStatusDisplay | null => {
    const s = status.value
    if (!s) return null

    // Determine status string based on game state
    let statusStr: 'running' | 'not_running' | 'busy' | 'error' = 'not_running'
    if (s.running) {
        statusStr = 'running'
    }

    const display: GameStatusDisplay = {
      status: statusStr,
      gameState: s.gameState,
      currentSongInfo: s.currentSongInfo,
      currentChartStyle: s.currentChartStyle,
      isIngame: s.isIngame,
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
    currentState,
    currentPvId,
    statusDisplay,
    refreshStatus,
    switchSong,
    startAutoRefresh,
    stopAutoRefresh,
    setAutoRefresh,
    setRefreshInterval,
  }
})
