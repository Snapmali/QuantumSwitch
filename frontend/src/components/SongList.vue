<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Song, SongAliasMatchItem, ModInfoSearchItem } from '@/types'
import { Search, Refresh, Star, StarFilled } from '@element-plus/icons-vue'
import { debounce } from 'lodash-es'
import { getDifficultyStyle } from '@/types'
import SearchAliasDropdown from './SearchAliasDropdown.vue'
import SearchModDropdown from './SearchModDropdown.vue'

const { t } = useI18n()

const props = defineProps<{
  songs: Song[]
  selectedId?: number | null
  loading?: boolean
  total?: number
  page?: number
  pageSize?: number
  favorites?: Set<number>
  favoritesOnly?: boolean
  matchedAliases?: SongAliasMatchItem[]
  // New props for mod search
  searchMode?: 'song' | 'mod'
  matchedMods?: ModInfoSearchItem[]
}>()

const emit = defineEmits<{
  select: [song: Song]
  pageChange: [page: number]
  refresh: []
  search: [query: string]
  toggleFavorite: [songId: number]
  'update:favoritesOnly': [value: boolean]
  'update:searchMode': [value: 'song' | 'mod']
  selectAlias: [item: SongAliasMatchItem]
  selectMod: [item: ModInfoSearchItem]
  searchMods: [query: string]
  clearSearch: []
}>()

const searchQuery = ref('')
const currentPage = computed({
  get: () => props.page || 1,
  set: (val) => {
    emit('pageChange', val)
    scrollToTop()
  }
})

const favoritesOnlyLocal = computed({
  get: () => props.favoritesOnly || false,
  set: (val) => emit('update:favoritesOnly', val)
})

const searchModeLocal = computed({
  get: () => props.searchMode || 'song',
  set: (val) => {
    // Skip if refreshing (parent will handle the reload)
    if (isRefreshing.value) {
      return
    }
    // Set flag to prevent watcher from triggering search
    isSwitchingMode.value = true
    emit('update:searchMode', val)
    // Clear search query when switching modes
    // Note: don't emit search event here, parent component's setSearchMode will handle loading
    searchQuery.value = ''
  }
})

// ChartStyle filter state - default to ARCADE
const selectedChartStyle = ref<string>('ARCADE')

const chartStyleOptions = [
  { value: 'ARCADE', label: 'A' },
  { value: 'CONSOLE', label: 'C' },
  { value: 'MIXED', label: 'M' },
]

// 滚动到列表顶部
const scrollToTop = () => {
  const container = document.querySelector('.songs-container')
  if (container) {
    container.scrollTop = 0
  }
}

// Debounced search function
const debouncedSearch = debounce((query: string) => {
  emit('search', query)
}, 300)

// Debounced mod search function
const debouncedModSearch = debounce((query: string) => {
  emit('searchMods', query)
}, 300)

// Watch search query and emit debounced search
watch(searchQuery, (newValue) => {
  // Skip search if selecting from dropdown (mod selection)
  if (isSelectingFromDropdown.value) {
    isSelectingFromDropdown.value = false
    return
  }
  // Skip search if switching search mode (parent will handle the search)
  if (isSwitchingMode.value) {
    isSwitchingMode.value = false
    return
  }
  // Skip search if refreshing (parent will handle the search via reload)
  if (isRefreshing.value) {
    // 不清除标志，让 handleRefresh 来清除
    return
  }
  if (searchModeLocal.value === 'mod') {
    debouncedModSearch(newValue)
  } else {
    debouncedSearch(newValue)
  }
  // Reset dropdown visibility when search content changes
  if (isDropdownHiddenByEsc.value) {
    isDropdownHiddenByEsc.value = false
  }
})

const filteredSongs = computed(() => {
  return props.songs
})

const handleSelect = (song: Song) => {
  emit('select', song)
}

const handleRefresh = () => {
  // Set flag to prevent search mode setter and search query watcher from triggering search
  isRefreshing.value = true
  // 取消待执行的 debounced 搜索，防止之前的输入触发搜索
  debouncedSearch.cancel()
  debouncedModSearch.cancel()
  // 清空搜索框
  searchQuery.value = ''
  // 触发刷新事件（父组件的 reloadSongs 会处理所有状态重置和歌曲加载）
  emit('refresh')
  // 延迟清除标志（确保在父组件处理期间标志仍然有效）
  setTimeout(() => {
    isRefreshing.value = false
  }, 100)
}

const handleToggleFavorite = (e: Event, songId: number) => {
  e.stopPropagation()
  emit('toggleFavorite', songId)
}

const isFavorite = (songId: number) => {
  return props.favorites?.has(songId) || false
}

// Alias/Mod dropdown state and handlers
const isSearchFocused = ref(false)
const aliasDropdownRef = ref<InstanceType<typeof SearchAliasDropdown> | null>(null)
const modDropdownRef = ref<InstanceType<typeof SearchModDropdown> | null>(null)
const dropdownSelectedIndex = ref(-1)
const isDropdownHiddenByEsc = ref(false)
// Flag to prevent search when selecting from dropdown
const isSelectingFromDropdown = ref(false)
// Flag to prevent search when switching search mode
const isSwitchingMode = ref(false)
// Flag to prevent search when refreshing
const isRefreshing = ref(false)

const showDropdown = computed(() => {
  if (isDropdownHiddenByEsc.value || !isSearchFocused.value || searchQuery.value.length === 0) {
    return false
  }
  if (searchModeLocal.value === 'mod') {
    return (props.matchedMods?.length ?? 0) > 0
  }
  return (props.matchedAliases?.length ?? 0) > 0
})

const handleSearchKeydown = (event: KeyboardEvent) => {
  if (!showDropdown.value) return

  const matches = searchModeLocal.value === 'mod' ? props.matchedMods : props.matchedAliases
  const maxIndex = (matches?.length ?? 0) - 1
  if (maxIndex < 0) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      dropdownSelectedIndex.value = Math.min(dropdownSelectedIndex.value + 1, maxIndex)
      break
    case 'ArrowUp':
      event.preventDefault()
      dropdownSelectedIndex.value = Math.max(dropdownSelectedIndex.value - 1, -1)
      break
    case 'Enter':
      if (dropdownSelectedIndex.value >= 0 && matches?.[dropdownSelectedIndex.value]) {
        event.preventDefault()
        if (searchModeLocal.value === 'mod') {
          handleModSelect(matches[dropdownSelectedIndex.value] as ModInfoSearchItem)
        } else {
          handleAliasSelect(matches[dropdownSelectedIndex.value] as SongAliasMatchItem)
        }
      }
      break
    case 'Escape':
      isDropdownHiddenByEsc.value = true
      break
  }
}

const handleSearchBlur = (event: FocusEvent) => {
  // Check if focus is moving to the dropdown
  const relatedTarget = event.relatedTarget as HTMLElement
  const aliasDropdownEl = aliasDropdownRef.value?.$el as HTMLElement | undefined
  const modDropdownEl = modDropdownRef.value?.$el as HTMLElement | undefined
  if (aliasDropdownEl?.contains(relatedTarget) || modDropdownEl?.contains(relatedTarget)) {
    return
  }
  isSearchFocused.value = false
}

const handleAliasSelect = (item: SongAliasMatchItem) => {
  // Fill search box with song name and trigger search
  searchQuery.value = item.songName
  emit('search', item.songName)
  emit('selectAlias', item)
}

const handleModSelect = (item: ModInfoSearchItem) => {
  // Set flag to prevent re-triggering search when setting searchQuery
  isSelectingFromDropdown.value = true
  // Fill search box with mod name and trigger mod selection
  searchQuery.value = item.name
  emit('selectMod', item)
}

// Format level for display (handle decimals like 6.5)
const formatLevel = (level: number): string => {
  // Show as integer if it's a whole number, otherwise show decimal
  return Number.isInteger(level) ? level.toString() : level.toFixed(1)
}

// 获取指定 ChartStyle 的全部难度列表（用于单 style 模式）
const getChartStyleDifficulties = (
  song: Song,
  style: string
): { type: number, name: string, shortName: string, maxLevel: number }[] => {
  const styleDetail = song.difficultyDetails.find(s => s.style === style)
  if (!styleDetail) return []

  return styleDetail.difficulties
    .filter(diff => diff.hasEnabledCharts)
    .map(diff => {
      // 找出该难度下最高等级的 chart
      const maxLevel = diff.chartInfos
        .filter(c => c.enabled)
        .reduce((max, chart) => Math.max(max, chart.level), 0)

      return {
        type: diff.type,
        name: diff.name,
        shortName: diff.shortName,
        maxLevel
      }
    })
    .filter(d => d.maxLevel >= 0)
    .sort((a, b) => a.type - b.type)  // 按难度类型排序（EASY -> EXTRA_EXTREME）
}
</script>

<template>
  <div class="song-list-container">
    <!-- Search and Filter -->
    <div class="search-section">
      <!-- Search Mode Radio Buttons -->
      <div class="search-mode-row">
        <el-radio-group v-model="searchModeLocal" size="small">
          <el-radio-button value="song">{{ t('songList.searchBySong') }}</el-radio-button>
          <el-radio-button value="mod">{{ t('songList.searchByMod') }}</el-radio-button>
        </el-radio-group>
      </div>
      <!-- Search Input Row -->
      <div class="search-input-row">
        <div class="search-input-wrapper">
          <el-input
            v-model.trim="searchQuery"
            :placeholder="searchModeLocal === 'mod' ? t('songList.searchModPlaceholder') : t('songList.searchPlaceholder')"
            clearable
            :prefix-icon="Search"
            class="search-input"
            @focus="isSearchFocused = true; dropdownSelectedIndex = -1; isDropdownHiddenByEsc = false"
            @blur="handleSearchBlur"
            @keydown="handleSearchKeydown"
          />
          <SearchAliasDropdown
            ref="aliasDropdownRef"
            :matches="matchedAliases || []"
            :visible="showDropdown && searchModeLocal === 'song'"
            :selected-index="dropdownSelectedIndex"
            @select="handleAliasSelect"
          />
          <SearchModDropdown
            ref="modDropdownRef"
            :matches="matchedMods || []"
            :visible="showDropdown && searchModeLocal === 'mod'"
            :selected-index="dropdownSelectedIndex"
            @select="handleModSelect"
          />
        </div>
        <el-button
          :icon="Refresh"
          circle
          :title="t('songList.refreshTooltip')"
          @click="handleRefresh"
        />
      </div>
    </div>

    <!-- Filters Row -->
    <div class="filters-row">
      <el-radio-group v-model="favoritesOnlyLocal" size="small">
        <el-radio-button :value="false">
          <div class="filter-btn-content">{{ t('songList.allSongs') }}</div>
        </el-radio-button>
        <el-radio-button :value="true">
          <div class="filter-btn-content">
            <el-icon><StarFilled /></el-icon>
            <span>{{ t('songList.favorites') }}</span>
          </div>
        </el-radio-button>
      </el-radio-group>

      <!-- ChartStyle Filter -->
      <el-radio-group v-model="selectedChartStyle" size="small">
        <el-radio-button v-for="opt in chartStyleOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- Song List -->
    <div v-loading="loading" class="songs-container">
      <div v-if="filteredSongs.length === 0" class="empty-state">
        <el-empty :description="t('songList.noSongsFound')" />
      </div>
      <div
        v-for="song in filteredSongs"
        :key="song.id"
        :class="['song-item', { active: selectedId === song.id, hidden: song.hidden }]"
        @click="handleSelect(song)"
      >
        <div class="song-main-row">
          <div class="song-info">
            <div class="song-name-row">
              <span class="song-name">{{ song.name }}</span>
              <span v-if="song.hidden" class="static-tag hidden-tag">{{ t('songList.hidden') }}</span>
            </div>
            <div v-if="song.nameEn && song.nameEn !== song.name" class="song-name-en">{{ song.nameEn }}</div>
          </div>
          <div class="song-meta">
            <div class="song-id">id {{ song.id }}</div>
            <span v-if="song.isVanilla" class="static-tag vanilla-tag">{{ t('songList.vanilla') }}</span>
            <span v-else-if="song.modEnabled === false" class="static-tag disabled-tag">{{ t('songList.disabled') }}</span>
          </div>
        </div>
        <div class="song-difficulties">
          <!-- Show all difficulties for selected ChartStyle -->
          <el-tooltip
            v-for="diff in getChartStyleDifficulties(song, selectedChartStyle)"
            :key="diff.type"
            :content="`${diff.name}${diff.maxLevel >= 0 ? ' - ' + formatLevel(diff.maxLevel) + '★' : ''}`"
            placement="top"
          >
            <span
              class="diff-tag-static"
              :style="getDifficultyStyle(diff.name)"
            >
              <span class="diff-short">{{ diff.shortName }}</span>
              <span v-if="diff.maxLevel >= 0" class="diff-level">
                {{ formatLevel(diff.maxLevel) }}
              </span>
            </span>
          </el-tooltip>

          <!-- Favorite Star -->
          <span
            class="favorite-star"
            :class="{ 'is-favorite': isFavorite(song.id) }"
            @click="(e) => handleToggleFavorite(e, song.id)"
          >
            <el-icon :size="16">
              <StarFilled v-if="isFavorite(song.id)" />
              <Star v-else />
            </el-icon>
          </span>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination-section">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize || 20"
        :total="total || 0"
        layout="prev, pager, next, jumper"
        :pager-count="5"
        size="small"
        background
      />
    </div>

    <div class="song-count">
      {{ t('songList.totalSongs', { count: total || 0 }) }}
    </div>
  </div>
</template>

<style scoped>
.song-list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.search-section {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-mode-row {
  margin-bottom: 0;
}

.search-input-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
  min-width: 150px;
}

.search-input {
  flex: 1;
  min-width: 150px;
}

.filters-row {
  padding: 8px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters-row .el-radio-button__inner {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-btn-content {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 100%;
}

.songs-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.song-item {
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 8px;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.song-item:hover {
  background-color: var(--el-fill-color-light);
}

.song-item.active {
  background-color: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.song-item.hidden {
  opacity: 0.7;
}

/* 主行：歌曲信息和ID */
.song-main-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.song-id {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.song-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.song-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.hidden-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 6px;
}

.disabled-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 6px;
  margin-left: auto;
}

/* 静态标签样式 - 无动效 */
.static-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 18px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 500;
  border-radius: 4px;
  white-space: nowrap;
  line-height: 1;
}

.static-tag.hidden-tag {
  background-color: #f56c6c;
  color: #fff;
}

.static-tag.disabled-tag {
  background-color: #e6a23c;
  color: #fff;
  margin-left: auto;
}

.static-tag.vanilla-tag {
  background-color: #409eff;
  color: #fff;
}

.song-name-en {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.song-difficulties {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 4px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.diff-tag {
  min-width: 36px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.diff-tag-static {
  min-width: 36px;
  text-align: center;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 0 6px;
  height: 22px;
  font-size: 12px;
  border-radius: 4px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}

.diff-short {
  font-weight: 600;
}

.diff-level {
  font-size: 10px;
  opacity: 0.9;
  margin-left: 2px;
}

.favorite-star {
  margin-left: auto;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
  color: var(--el-text-color-secondary);
}

.favorite-star:hover {
  background-color: var(--el-fill-color);
  color: var(--el-color-warning);
}

.favorite-star.is-favorite {
  color: #ffc107;
}

.favorite-star.is-favorite:hover {
  color: #ff9800;
}

.empty-state {
  padding: 40px 0;
}

.song-count {
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color-light);
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.pagination-section {
  padding: 8px 8px;
  border-top: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: center;
  overflow: visible;
}

.pagination-section :deep(.el-pagination) {
  --el-pagination-button-width: 28px;
  --el-pagination-button-height: 28px;
}

.pagination-section :deep(.el-pagination__jump) {
  margin-left: 8px;
  font-size: 12px;
}

.pagination-section :deep(.el-pagination__jump .el-input) {
  width: 40px;
}

/* Hide "Go to" text in jumper */
.pagination-section :deep(.el-pagination__goto) {
  display: none;
}

.pagination-section :deep(.el-pagination__classifier) {
  display: none;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .search-section {
    padding: 12px;
    gap: 10px;
  }

  .search-input {
    min-width: 100%;
    order: 1;
  }

  .search-section .el-button {
    order: 3;
  }

  .songs-container {
    padding: 6px;
  }

  .song-item {
    padding: 14px 12px;
    margin-bottom: 6px;
    gap: 10px;
  }

  .song-name {
    font-size: 15px;
  }

  .song-name-en {
    font-size: 12px;
  }

  .diff-tag-static {
    min-width: 40px;
    height: 26px;
    font-size: 13px;
    padding: 0 8px;
  }

  .song-count {
    padding: 10px 12px;
  }

  .pagination-section {
    padding: 10px 6px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .pagination-section :deep(.el-pagination) {
    --el-pagination-button-width: 36px;
    --el-pagination-button-height: 36px;
    white-space: nowrap;
    min-width: min-content;
  }

  .pagination-section :deep(.el-pagination__jump) {
    font-size: 13px;
    margin-left: 8px;
  }

  .pagination-section :deep(.el-pagination__editor.el-input) {
    width: 40px;
  }
}

/* Small mobile optimizations */
@media (max-width: 480px) {
  .search-section {
    padding: 10px;
    gap: 8px;
  }

  .search-input {
    min-width: 100%;
    width: 100%;
  }

  .search-input :deep(.el-input__inner) {
    font-size: 16px;
  }

  .search-section .el-button {
    width: 36px;
    height: 36px;
  }

  .song-item {
    padding: 12px 10px;
    gap: 8px;
  }

  .song-main-row {
    gap: 8px;
  }

  .song-name {
    font-size: 14px;
    word-break: break-word;
    line-height: 1.4;
  }

  .song-name-en {
    font-size: 11px;
    word-break: break-word;
  }

  .song-meta {
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }

  .song-id {
    font-size: 11px;
  }

  .song-difficulties {
    gap: 4px;
  }

  .diff-tag-static {
    min-width: 36px;
    height: 24px;
    font-size: 12px;
    padding: 0 6px;
  }

  .pagination-section {
    padding: 8px 4px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .pagination-section :deep(.el-pagination) {
    white-space: nowrap;
    min-width: min-content;
  }

  .pagination-section :deep(.el-pagination .btn-prev),
  .pagination-section :deep(.el-pagination .btn-next) {
    min-width: 28px;
    height: 28px;
  }

  .pagination-section :deep(.el-pagination .el-pager li) {
    min-width: 28px;
    height: 28px;
    line-height: 28px;
    font-size: 12px;
  }

  .pagination-section :deep(.el-pagination__jump) {
    margin-left: 2px;
    font-size: 12px;
  }

  .pagination-section :deep(.el-pagination__editor.el-input) {
    width: 30px;
    margin: 0 2px;
  }

  .pagination-section :deep(.el-pagination__editor.el-input .el-input__inner) {
    padding: 0 1px;
    height: 24px;
    line-height: 24px;
    font-size: 11px;
  }

  .pagination-section :deep(.el-pagination__total) {
    font-size: 11px;
  }

  .song-count {
    padding: 10px;
    font-size: 11px;
  }
}

/* Extra small mobile - hide jumper to save space */
@media (max-width: 375px) {
  .pagination-section :deep(.el-pagination__jump) {
    display: none;
  }
}
</style>
