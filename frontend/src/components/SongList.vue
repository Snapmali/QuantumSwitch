<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Song } from '@/types'
import { Search, Refresh, Star, StarFilled } from '@element-plus/icons-vue'
import { debounce } from 'lodash-es'
import { getDifficultyStyle, getDifficultyShortLabel } from '@/types'

const props = defineProps<{
  songs: Song[]
  selectedId?: number | null
  loading?: boolean
  total?: number
  page?: number
  pageSize?: number
  favorites?: Set<number>
  favoritesOnly?: boolean
}>()

const emit = defineEmits<{
  select: [song: Song]
  pageChange: [page: number]
  refresh: []
  search: [query: string]
  toggleFavorite: [songId: number]
  'update:favoritesOnly': [value: boolean]
}>()

const searchQuery = ref('')
const selectedDifficulties = ref<string[]>([])
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

// Watch search query and emit debounced search
watch(searchQuery, (newValue) => {
  debouncedSearch(newValue)
})

const difficultyOptions = [
  { label: 'EASY', value: 'EASY', type: 'primary' },
  { label: 'NORMAL', value: 'NORMAL', type: 'success' },
  { label: 'HARD', value: 'HARD', type: 'warning' },
  { label: 'EXTREME', value: 'EXTREME', type: 'danger' },
  { label: 'EX EXTREME', value: 'EXTRA EXTREME', type: 'danger' },
]

const filteredSongs = computed(() => {
  let result = props.songs

  // Note: Search is now handled server-side via the search event
  // Only difficulty filtering is done client-side

  // Filter by difficulty
  if (selectedDifficulties.value.length > 0) {
    result = result.filter(song =>
      song.difficultyDetails?.some(d => selectedDifficulties.value.includes(d.name))
    )
  }

  return result
})

const handleSelect = (song: Song) => {
  emit('select', song)
}

const handleRefresh = () => {
  emit('refresh')
}

const handleToggleFavorite = (e: Event, songId: number) => {
  e.stopPropagation()
  emit('toggleFavorite', songId)
}

const isFavorite = (songId: number) => {
  return props.favorites?.has(songId) || false
}

// Format level for display (handle decimals like 6.5)
const formatLevel = (level: number): string => {
  if (level === 0) return ''
  // Show as integer if it's a whole number, otherwise show decimal
  return Number.isInteger(level) ? level.toString() : level.toFixed(1)
}
</script>

<template>
  <div class="song-list-container">
    <!-- Search and Filter -->
    <div class="search-section">
      <el-input
        v-model="searchQuery"
        placeholder="搜索歌曲..."
        clearable
        :prefix-icon="Search"
        class="search-input"
      />
      <el-select
        v-model="selectedDifficulties"
        multiple
        collapse-tags
        placeholder="筛选难度"
        class="difficulty-filter"
      >
        <el-option
          v-for="opt in difficultyOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-button
        :icon="Refresh"
        circle
        title="刷新歌曲列表"
        @click="handleRefresh"
      />
    </div>

    <!-- Favorites Filter -->
    <div class="favorites-filter">
      <el-radio-group v-model="favoritesOnlyLocal" size="small">
        <el-radio-button :value="false">
          全部歌曲
        </el-radio-button>
        <el-radio-button :value="true">
          <el-icon><StarFilled /></el-icon>
          已收藏
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- Song List -->
    <div v-loading="loading" class="songs-container">
      <div v-if="filteredSongs.length === 0" class="empty-state">
        <el-empty description="未找到歌曲" />
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
              <span v-if="song.hidden" class="static-tag hidden-tag">隐藏</span>
            </div>
            <div v-if="song.nameEn && song.nameEn !== song.name" class="song-name-en">{{ song.nameEn }}</div>
          </div>
          <div class="song-meta">
            <div class="song-id">id {{ song.id }}</div>
            <span v-if="song.isVanilla" class="static-tag vanilla-tag">原版</span>
            <span v-else-if="song.modEnabled === false" class="static-tag disabled-tag">已禁用</span>
          </div>
        </div>
        <div class="song-difficulties">
          <el-tooltip
            v-for="detail in song.difficultyDetails"
            :key="detail.type + '-' + detail.index"
            :content="`${detail.name}${detail.level > 0 ? ' - ' + formatLevel(detail.level) + '★' : ''}`"
            placement="top"
          >
            <span
              class="diff-tag-static"
              :style="getDifficultyStyle(detail.name)"
            >
              <span class="diff-short">{{ getDifficultyShortLabel(detail.name) }}</span>
              <span v-if="detail.level > 0" class="diff-level">
                {{ formatLevel(detail.level) }}
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
      共 {{ total || 0 }} 首歌曲
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
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 150px;
}

.difficulty-filter {
  width: 150px;
  min-width: 120px;
}

.favorites-filter {
  padding: 8px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: center;
}

.favorites-filter .el-radio-button__inner {
  display: flex;
  align-items: center;
  gap: 4px;
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

  .difficulty-filter {
    width: calc(100% - 52px);
    order: 2;
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

  .difficulty-filter {
    width: calc(100% - 44px);
    min-width: auto;
  }

  .difficulty-filter :deep(.el-input__inner) {
    font-size: 14px;
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
