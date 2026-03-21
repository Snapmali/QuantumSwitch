<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSongStore } from '@/stores/songs'
import { useGameStore } from '@/stores/game'
import { useLocaleStore } from '@/stores/locale'
import { ElMessage } from 'element-plus'
import type { Song } from '@/types'
import { songApi } from '@/api'
import SongList from '@/components/SongList.vue'
import SongDetail from '@/components/SongDetail.vue'
import GameStatus from '@/components/GameStatus.vue'
import WarningDialog from '@/components/WarningDialog.vue'
import LanguageSwitch from '@/components/LanguageSwitch.vue'
import AliasManager from '@/components/AliasManager.vue'
import { CollectionTag } from '@element-plus/icons-vue'

const { t } = useI18n()
const songStore = useSongStore()
const gameStore = useGameStore()
useLocaleStore() // Initialize locale store
const warningDialog = ref<InstanceType<typeof WarningDialog> | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)

// 使用 ref 存储选中歌曲的完整数据，翻页时不会丢失
const selectedSongData = ref<Song | null>(null)

// Alias manager dialog visibility
const aliasManagerVisible = ref(false)

const selectedSong = computed(() => {
  if (!songStore.selectedId) return null
  // 如果有缓存的歌曲数据且id匹配，直接返回缓存数据
  if (selectedSongData.value && selectedSongData.value.id === songStore.selectedId) {
    return selectedSongData.value
  }
  // 否则从当前列表中查找
  return songStore.songs.find(s => s.id === songStore.selectedId) || null
})

// Matched aliases from search
const matchedAliases = computed(() => songStore.matchedAliases)

// Mod search related computed
const matchedMods = computed(() => songStore.matchedMods)
const searchMode = computed({
  get: () => songStore.searchMode,
  set: (value: 'song' | 'mod') => songStore.setSearchMode(value)
})

const selectedStyle = computed(() => songStore.selectedStyle)
const selectedDifficultyType = computed(() => songStore.selectedDifficultyType)

// Refresh interval in seconds for the slider
const refreshIntervalSeconds = computed({
  get: () => Math.round(gameStore.refreshIntervalMs / 1000),
  set: (value: number) => {
    gameStore.setRefreshInterval(value)
  }
})

// Watch for autoRefresh changes
watch(() => gameStore.autoRefresh, (enabled) => {
  gameStore.setAutoRefresh(enabled)
})

onMounted(async () => {
  // Show warning dialog
  warningDialog.value?.open()

  // Load initial data
  await Promise.all([
    songStore.loadSongs(currentPage.value),
    gameStore.refreshStatus(),
  ])

  // Start auto-refresh based on current setting
  gameStore.setAutoRefresh(gameStore.autoRefresh)
})

onUnmounted(() => {
  // Stop auto-refresh when component is destroyed
  gameStore.setAutoRefresh(false)
})

const handleSongSelect = async (song: Song) => {
  await songStore.selectSong(song)
  // 缓存选中的歌曲完整数据，翻页时不会丢失
  selectedSongData.value = song
}

const handleDifficultySelect = (style: string, difficultyType: number) => {
  songStore.selectDifficulty(style, difficultyType)
}

const handleSwitchSong = async () => {
  if (!selectedSong.value || selectedDifficultyType.value === null) {
    ElMessage.warning(t('messages.selectSongFirst'))
    return
  }

  const success = await songStore.switchToCurrentSong()
  if (success) {
    // Refresh game status after switch
    await gameStore.refreshStatus()
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  songStore.loadSongs(page)
}

const handleRefreshSongs = async () => {
  await songStore.reloadSongs()
  currentPage.value = 1
  ElMessage.success(t('messages.songsRefreshed'))
}

const handleSearch = async (query: string) => {
  currentPage.value = 1
  await songStore.searchSongs(query)
}

const handleToggleFavorite = async (songId: number) => {
  await songStore.toggleFavorite(songId)
}

const handleToggleFavoriteDetail = async () => {
  if (selectedSong.value) {
    await songStore.toggleFavorite(selectedSong.value.id)
  }
}

const handleFavoritesOnlyChange = (value: boolean) => {
  songStore.setFavoritesOnly(value)
}

const handleSearchModeChange = (value: 'song' | 'mod') => {
  songStore.setSearchMode(value)
}

const handleSearchMods = async (query: string) => {
  await songStore.searchMods(query)
}

const handleSelectMod = async (mod: { id: number; name: string }) => {
  await songStore.selectMod(mod.id, mod.name)
}

const handleCurrentSongClick = async (songId: number) => {
  // Check if already in current list
  const existingSong = songStore.songs.find(s => s.id === songId)
  if (existingSong) {
    // If in current list, select directly
    await handleSongSelect(existingSong)
  } else {
    // If not in current list, get full song info via API
    try {
      const response = await songApi.getById(songId)
      if (response.data.data) {
        const song = response.data.data
        await handleSongSelect(song)
      }
    } catch (err) {
      ElMessage.error(t('messages.cannotGetSongInfo'))
    }
  }
}
</script>

<template>
  <div class="home-view">
    <WarningDialog ref="warningDialog" />

    <header class="app-header">
      <div class="header-content">
        <h1>
          <img src="/icon.ico" alt="icon" class="header-icon" />
          {{ t('home.title') }}
        </h1>
        <div class="header-actions">
          <span class="version">v1.0.0</span>
          <el-button
            type="default"
            size="small"
            :icon="CollectionTag"
            @click="aliasManagerVisible = true"
          >
            {{ t('alias.manageButton') }}
          </el-button>
          <LanguageSwitch />
        </div>
      </div>
    </header>

    <main class="main-content">
      <div class="content-grid">
        <!-- Left Column: Song List -->
        <div class="left-column">
          <GameStatus
            :status="gameStore.statusDisplay"
            :loading="gameStore.loading"
            v-model:auto-refresh="gameStore.autoRefresh"
            v-model:refresh-interval="refreshIntervalSeconds"
            @refresh="gameStore.refreshStatus"
            @song-click="handleCurrentSongClick"
          />
          <el-card shadow="never" class="song-list-card">
            <SongList
              :songs="songStore.songs"
              :selected-id="songStore.selectedId"
              :loading="songStore.loading"
              :total="songStore.total"
              :page="currentPage"
              :page-size="pageSize"
              :favorites="songStore.favorites"
              :favorites-only="songStore.favoritesOnly"
              :matched-aliases="matchedAliases"
              :search-mode="searchMode"
              :matched-mods="matchedMods"
              @select="handleSongSelect"
              @page-change="handlePageChange"
              @refresh="handleRefreshSongs"
              @search="handleSearch"
              @toggle-favorite="handleToggleFavorite"
              @update:favorites-only="handleFavoritesOnlyChange"
              @update:search-mode="handleSearchModeChange"
              @search-mods="handleSearchMods"
              @select-mod="handleSelectMod"
            />
          </el-card>
        </div>

        <!-- Right Column: Song Detail -->
        <div class="right-column">
          <el-card shadow="never" class="detail-card">
            <SongDetail
              :song="selectedSong"
              :selected-style="selectedStyle"
              :selected-difficulty-type="selectedDifficultyType"
              :game-running="gameStore.isRunning"
              :is-mod-enabled="selectedSong?.modEnabled"
              :is-favorite="selectedSong ? songStore.isFavorite(selectedSong.id) : false"
              @select-difficulty="handleDifficultySelect"
              @switch-song="handleSwitchSong"
              @toggle-favorite="handleToggleFavoriteDetail"
            />
          </el-card>
        </div>
      </div>
    </main>

    <!-- Alias Manager Dialog -->
    <AliasManager v-model:visible="aliasManagerVisible" />
  </div>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color-page);
  overflow-x: hidden;
}

.app-header {
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  padding: 0 24px;
}

.header-content {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.app-header h1 {
  margin: 0;
  font-size: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-primary);
}

.header-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.version {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 12px;
  border-radius: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow: hidden;
}

.content-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 108px);
}

.left-column,
.right-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.song-list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.song-list-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.detail-card {
  height: 100%;
  overflow: hidden;
  max-width: 100%;
}

.detail-card :deep(.el-card__body) {
  height: 100%;
  padding: 0;
  overflow: hidden;
  max-width: 100%;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
    height: auto;
    min-height: calc(100vh - 108px);
    min-height: calc(100dvh - 108px);
  }

  .left-column {
    max-height: none;
    height: auto;
    min-height: 300px;
  }

  .song-list-card {
    min-height: 400px;
  }

  .right-column {
    height: auto;
    min-height: 500px;
  }

  .detail-card {
    min-height: 500px;
  }
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .app-header {
    padding: 0 12px;
  }

  .header-content {
    height: 52px;
  }

  .app-header h1 {
    font-size: 16px;
  }

  .header-icon {
    width: 22px;
    height: 22px;
  }

  .version {
    padding: 2px 8px;
    font-size: 10px;
  }

  .main-content {
    padding: 12px;
  }

  .content-grid {
    gap: 12px;
    min-height: calc(100dvh - 80px);
  }

  .left-column,
  .right-column {
    gap: 10px;
  }

  .song-list-card {
    min-height: 300px;
  }

  .detail-card {
    min-height: 350px;
  }
}

/* Small mobile optimizations */
@media (max-width: 480px) {
  .main-content {
    padding: 8px;
  }

  .content-grid {
    gap: 8px;
    min-height: calc(100dvh - 76px);
  }

  .left-column,
  .right-column {
    max-width: 100%;
    overflow-x: hidden;
  }

  .song-list-card,
  .detail-card {
    max-width: 100%;
  }
}
</style>
