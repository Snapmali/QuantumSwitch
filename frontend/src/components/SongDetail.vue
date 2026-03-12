<script setup lang="ts">
import type { Song } from '@/types'
import { ref, computed } from 'vue'
import {Check, Folder, InfoFilled, StarFilled, Star, SwitchButton, UserFilled, VideoPlay, Collection} from "@element-plus/icons-vue"
import { formatLevel, getDifficultyLabel, getDifficultyShortLabel, DifficultyColorValues } from '@/types'

const props = defineProps<{
  song: Song | null
  selectedDifficulty?: string | null
  gameRunning?: boolean
  isModEnabled?: boolean
  isFavorite?: boolean
}>()

const emit = defineEmits<{
  selectDifficulty: [difficulty: string]
  switchSong: []
  toggleFavorite: []
}>()

// 跟踪悬停的难度
const hoveredDifficulty = ref<string | null>(null)


// 计算按钮禁用状态和提示文本
const switchButtonDisabled = computed(() => {
  if (!props.selectedDifficulty) return true
  if (!props.gameRunning) return true
  // 检查选中的难度是否被禁用
  const selectedDetail = props.song?.difficultyDetails.find(d => d.name === props.selectedDifficulty)
  if (selectedDetail?.enabled === false) return true
  // 原版歌曲不检测mod启用状态
  if (props.song?.isVanilla) return false
  if (props.isModEnabled === false) return true
  return false
})

const switchButtonHint = computed(() => {
  if (!props.selectedDifficulty) return '请先选择难度'
  if (!props.gameRunning) return '游戏未运行'
  // 检查选中的难度是否被禁用
  const selectedDetail = props.song?.difficultyDetails.find(d => d.name === props.selectedDifficulty)
  if (selectedDetail?.enabled === false) return '该难度已被禁用'
  // 原版歌曲不显示mod禁用提示
  if (props.song?.isVanilla) return ''
  if (props.isModEnabled === false) return 'Mod 已禁用'
  return ''
})

const handleSelectDifficulty = (difficultyType: string) => {
  emit('selectDifficulty', difficultyType)
}

const handleSwitch = () => {
  emit('switchSong')
}

const handleToggleFavorite = () => {
  emit('toggleFavorite')
}

// Format attributes for display
const formatAttributes = computed(() => {
  if (!props.song?.attributes) return []
  return Object.entries(props.song.attributes)
    .filter(([key]) => !key.includes('song_name') && !key.includes('difficulty'))
    .sort(([a], [b]) => a.localeCompare(b))
})

// Check if song has metadata
const hasMetadata = computed(() => {
  if (!props.song) return false
  return !!(props.song.bpm)
})

// 获取难度颜色（从 DifficultyColorValues）
const getDifficultyColor = (diffName: string): string => {
  return DifficultyColorValues[diffName] || '#909399'
}

// 获取难度卡片样式（根据选中状态、悬停状态和禁用状态返回不同样式）
const getDifficultyCardStyle = (diffName: string, isSelected: boolean, isHovered: boolean, isDisabled: boolean): Record<string, string> => {
  const color = DifficultyColorValues[diffName] || '#909399'

  if (isDisabled) {
    // 禁用状态：灰色边框、降低透明度
    return {
      borderLeftColor: '#8c959f',
      borderColor: '#d0d7de',
      backgroundColor: '#f6f8fa',
      opacity: '0.6',
      cursor: 'not-allowed',
    }
  }

  if (isSelected) {
    // 选中状态：使用难度颜色的半透明背景，以及该颜色作为边框
    return {
      borderLeftColor: color,
      borderColor: color,
      backgroundColor: color + '1A', // 10% 透明度
    }
  }
  if (isHovered) {
    // 悬停状态：使用难度颜色的浅色背景和边框
    return {
      borderLeftColor: color,
      borderColor: color,
      backgroundColor: color + '0D', // 5% 透明度，比选中状态更淡
    }
  }
  // 未选中未悬停状态：只设置左边框颜色
  return {
    borderLeftColor: color,
  }
}

// Check if song has credits from songinfo
const hasCredits = computed(() => {
  if (!props.song) return false
  return !!(props.song.music || props.song.arranger || props.song.lyrics || props.song.guitarPlayer ||
    props.song.illustrator || props.song.manipulator || props.song.pvEditor)
})
</script>

<template>
  <div class="song-detail">
    <div v-if="!song" class="empty-detail">
      <el-empty description="请选择一首歌曲" />
    </div>
    <template v-else>
      <!-- Song Header -->
      <div class="song-header">
        <div class="song-icon">
          <el-icon :size="40" color="var(--el-color-primary)">
            <video-play />
          </el-icon>
        </div>
        <div class="song-titles">
          <h2 class="song-name">
            {{ song.name }}
            <el-tag v-if="song.isVanilla" type="primary" size="small" effect="light" class="vanilla-badge" :disable-transitions="true">原版</el-tag>
          </h2>
          <p v-if="song.nameReading" class="song-reading">{{ song.nameReading }}</p>
          <p v-if="song.nameEn && song.nameEn !== song.name" class="song-name-en">{{ song.nameEn }}</p>
          <div class="song-badges">
            <el-tag v-if="song.hidden" type="danger" size="small" effect="dark">隐藏</el-tag>
            <el-tag type="info" size="small">id {{ song.id }}</el-tag>
          </div>
        </div>
        <div class="song-favorite">
          <el-button
            circle
            :type="isFavorite ? 'warning' : 'default'"
            size="small"
            @click="handleToggleFavorite"
            :title="isFavorite ? '取消收藏' : '添加收藏'"
          >
            <el-icon :size="18">
              <StarFilled v-if="isFavorite" />
              <Star v-else />
            </el-icon>
          </el-button>
        </div>
      </div>

      <el-divider />

      <!-- Action Button -->
      <div class="action-section">
        <el-button
          type="primary"
          size="large"
          :disabled="switchButtonDisabled"
          @click="handleSwitch"
        >
          <el-icon>
            <switch-button />
          </el-icon>
          切换到该歌曲
        </el-button>
        <p v-if="switchButtonHint" class="hint">
          {{ switchButtonHint }}
        </p>
      </div>

      <el-divider />

      <!-- Difficulty Details -->
      <div class="difficulty-section">
        <h3 class="section-title">
          <el-icon>
            <star-filled />
          </el-icon>
          难度详情
        </h3>
        <div class="difficulty-list">
          <div v-for="detail in song.difficultyDetails" :key="detail.type + '-' + detail.index"
            :class="['difficulty-card', {
              selected: selectedDifficulty === detail.name,
              disabled: detail.enabled === false
            }]"
            :style="getDifficultyCardStyle(detail.name, selectedDifficulty === detail.name, hoveredDifficulty === detail.name, detail.enabled === false)"
            @click="detail.enabled !== false ? handleSelectDifficulty(detail.name) : null"
            @mouseenter="hoveredDifficulty = detail.name"
            @mouseleave="hoveredDifficulty = null"
          >
            <div class="difficulty-content">
              <div class="difficulty-main">
                <div class="difficulty-badge" :style="{ backgroundColor: detail.enabled === false ? '#8c959f' : getDifficultyColor(detail.name) }">{{ getDifficultyShortLabel(detail.name) }}</div>
                <div class="difficulty-info">
                  <div class="difficulty-name">{{ getDifficultyLabel(detail.name) }}</div>
                  <div v-if="detail.level > 0" class="difficulty-level">
                    <span class="level-value">{{ formatLevel(detail.level) }}</span>
                  </div>
                </div>
              </div>
              <div v-if="selectedDifficulty === detail.name" class="selected-icon" :style="{ color: getDifficultyColor(detail.name) }">
                <el-icon><check /></el-icon>
              </div>
              <!-- 禁用标记 -->
              <div v-if="detail.enabled === false" class="disabled-indicator">
                <el-tag type="info" size="small" :disable-transitions="true">已禁用</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <el-divider />

      <!-- Song Metadata -->
      <div v-if="hasMetadata" class="metadata-section">
        <h3 class="section-title">
          <el-icon>
            <info-filled />
          </el-icon>
          歌曲信息
        </h3>
        <div class="metadata-grid">
          <div v-if="song.bpm" class="metadata-item">
            <span class="metadata-label">BPM</span>
            <span class="metadata-value">{{ song.bpm }}</span>
          </div>
        </div>
      </div>

      <el-divider v-if="hasMetadata" />

      <!-- Song Credits from songinfo -->
      <div v-if="hasCredits" class="credits-section">
        <h3 class="section-title">
          <el-icon>
            <user-filled />
          </el-icon>
          创作者信息
        </h3>
        <div class="metadata-grid">
          <div v-if="song.manipulator" class="metadata-item">
            <span class="metadata-label">调教师</span>
            <span class="metadata-value">{{ song.manipulator }}</span>
          </div>
          <div v-if="song.music" class="metadata-item">
            <span class="metadata-label">作曲</span>
            <span class="metadata-value">{{ song.music }}</span>
          </div>
          <div v-if="song.arranger" class="metadata-item">
            <span class="metadata-label">编曲</span>
            <span class="metadata-value">{{ song.arranger }}</span>
          </div>
          <div v-if="song.guitarPlayer" class="metadata-item">
            <span class="metadata-label">吉他</span>
            <span class="metadata-value">{{ song.guitarPlayer }}</span>
          </div>
          <div v-if="song.lyrics" class="metadata-item">
            <span class="metadata-label">作词</span>
            <span class="metadata-value">{{ song.lyrics }}</span>
          </div>
          <div v-if="song.illustrator" class="metadata-item">
            <span class="metadata-label">画师</span>
            <span class="metadata-value">{{ song.illustrator }}</span>
          </div>
          <div v-if="song.pvEditor" class="metadata-item">
            <span class="metadata-label">PV编辑</span>
            <span class="metadata-value">{{ song.pvEditor }}</span>
          </div>
        </div>
      </div>

      <el-divider v-if="hasCredits" />

      <!-- Mod Info -->
      <div v-if="(song.modInfos && song.modInfos.length > 0) || song.modInfo || song.modPath || song.isVanilla" class="mod-section">
        <h3 class="section-title">
          <el-icon>
            <folder />
          </el-icon>
          来源 Mod
          <el-tag v-if="song.isVanilla" type="primary" size="small" effect="light" class="vanilla-badge" :disable-transitions="true">原版</el-tag>
        </h3>

        <!-- Multiple Mods List -->
        <div v-if="song.modInfos && song.modInfos.length > 0" class="mod-list">
          <div
            v-for="(mod, index) in song.modInfos"
            :key="mod.path || index"
            class="mod-item"
            :class="{ 'mod-disabled': !mod.enabled }"
          >
            <div class="mod-header">
              <span class="mod-index">#{{ index + 1 }}</span>
              <span class="mod-name">{{ mod.name }}</span>
              <el-tag :type="mod.enabled ? 'success' : 'info'" size="small" :disable-transitions="true">
                {{ mod.enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </div>
            <div v-if="mod.author || mod.version" class="mod-meta">
              <span v-if="mod.author" class="mod-author">
                作者: {{ mod.author }}
              </span>
              <span v-if="mod.version" class="mod-version">
                版本: {{ mod.version }}
              </span>
            </div>
            <div v-if="mod.path && mod.id !== 0" class="mod-path" :title="mod.path">
              <el-icon><folder /></el-icon> {{ mod.path }}
            </div>
          </div>
        </div>

        <!-- Vanilla Only (No Mod) -->
        <div v-else-if="song.isVanilla" class="mod-info-empty">
          <el-icon><collection /></el-icon>
          <span>原版歌曲（无Mod关联）</span>
        </div>
      </div>

      <el-divider v-if="(song.modInfos && song.modInfos.length > 0) || song.modInfo || song.modPath" />

      <!-- Raw Attributes (Collapsible) -->
      <el-collapse v-if="formatAttributes.length > 0" class="attributes-collapse">
        <el-collapse-item title="原始属性 (PVDB)" name="attributes">
          <div class="attributes-list">
            <div v-for="[key, value] in formatAttributes" :key="key" class="attribute-item">
              <span class="attribute-key">{{ key }}</span>
              <span class="attribute-value">{{ value }}</span>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<style scoped>
.song-detail {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  max-width: 100%;
  box-sizing: border-box;
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* Song Header */
.song-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  height: 90px;
  min-height: 90px;
}

.song-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.song-titles {
  flex: 1;
  min-width: 0;
}

.song-favorite {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.song-favorite .el-button {
  transition: all 0.2s;
}

.song-favorite .el-button:hover {
  transform: scale(1.1);
}

.song-name {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.3;
  min-height: 24px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  overflow: hidden;
}

.song-name .el-tag {
  flex-shrink: 0;
}

.song-reading {
  margin: 0 0 2px 0;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.song-name-en {
  margin: 0 0 6px 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.song-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}

/* Section Title */
.section-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Wide screen optimizations (1024px and above) */
@media (min-width: 1025px) {
  .difficulty-card {
    min-width: 120px;
    max-width: 160px;
  }

  .difficulty-content {
    padding: 0 10px;
    gap: 8px;
  }

  .difficulty-badge {
    width: 28px;
    height: 28px;
    font-size: 11px;
  }

  .difficulty-name {
    font-size: 12px;
  }

  .song-header {
    height: 90px;
    min-height: 90px;
  }

  .song-icon {
    width: 56px;
    height: 56px;
  }

  .song-name {
    font-size: 16px;
  }

  .metadata-grid {
    gap: 8px;
  }

  .metadata-item {
    padding: 6px 10px;
  }

  .mod-item {
    padding: 10px;
  }

  .song-detail {
    padding: 16px;
  }
}

.section-title .el-icon {
  font-size: 16px;
  color: var(--el-color-primary);
}

/* Difficulty Section - Flat Modern Style */
.difficulty-section {
  margin-bottom: 4px;
}

.difficulty-list {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

.difficulty-card {
  cursor: pointer;
  transition: all 0.15s ease;
  border-radius: 6px;
  border: 1px solid #e1e4e8;
  border-left: 3px solid #909399;
  padding: 0;
  flex: 1;
  min-width: 140px;
  max-width: 180px;
  height: 56px;
  overflow: hidden;
  background: #fff;
  position: relative;
  box-sizing: border-box;
}

.difficulty-card.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.difficulty-card:hover {
  /* 悬停样式由动态样式绑定设置 */
}

.difficulty-card.selected {
  /* 选中样式由动态样式绑定设置 */
}

.difficulty-card {
  height: 64px;
}

.difficulty-content {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  height: 100%;
  gap: 10px;
}

.difficulty-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.difficulty-badge {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  color: white;
  flex-shrink: 0;
}

.difficulty-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.difficulty-name {
  font-size: 13px;
  font-weight: 500;
  color: #24292f;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.difficulty-level {
  font-size: 12px;
  color: #656d76;
}

.level-value {
  font-weight: 600;
  color: #24292f;
}

.selected-icon {
  color: #409eff;
  font-size: 16px;
  flex-shrink: 0;
}

.disabled-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
}

/* Rest of the styles */
.script-path {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #d0d7de;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #656d76;
}

.script-name {
  font-family: monospace;
  color: #24292f;
}

/* Metadata Section */
.metadata-section {
  margin-bottom: 4px;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: #f6f8fa;
  border-radius: 6px;
}

.metadata-label {
  font-size: 11px;
  color: #656d76;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metadata-value {
  font-size: 13px;
  color: #24292f;
  font-weight: 500;
}

/* Mod Section */
.mod-section {
  margin-bottom: 4px;
}

.mod-info-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mod-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.mod-name {
  font-size: 14px;
  font-weight: 600;
  color: #24292f;
}

.mod-version {
  font-size: 12px;
  color: #656d76;
  background: #f6f8fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.mod-author {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mod-label {
  font-size: 12px;
  color: #656d76;
}

.mod-value {
  font-size: 12px;
  color: #24292f;
  font-weight: 500;
}

.mod-path {
  font-family: monospace;
  font-size: 12px;
  max-width: 100%;
  overflow: hidden;
  word-break: break-all;
  white-space: normal;
  line-height: 1.4;
}

/* Vanilla Badge in Title */
.vanilla-badge {
  margin-left: 8px;
  font-size: 11px;
  vertical-align: middle;
}

/* Multiple Mods List */
.mod-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mod-item {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid #409eff;
}

.mod-item.mod-disabled {
  border-left-color: #8c959f;
  opacity: 0.8;
}

.mod-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.mod-index {
  font-size: 11px;
  color: #8c959f;
  font-weight: 500;
}

.mod-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #656d76;
  margin-bottom: 4px;
}

.mod-list .mod-path {
  font-size: 11px;
  color: #8c959f;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  word-break: break-all;
  white-space: normal;
  line-height: 1.4;
}

.mod-list .mod-path .el-icon {
  font-size: 11px;
  flex-shrink: 0;
}

.mod-info-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  color: #8c959f;
  font-size: 13px;
  background: #f6f8fa;
  border-radius: 8px;
}

.mod-info-empty .el-icon {
  font-size: 16px;
}

/* Attributes */
.attributes-collapse {
  margin-bottom: 4px;
}

.attributes-collapse :deep(.el-collapse-item__header) {
  font-size: 14px;
  font-weight: 500;
}

.attributes-collapse :deep(.el-collapse-item__content) {
  padding: 12px;
  overflow: visible;
}

.attributes-collapse :deep(.el-collapse-item__wrap) {
  overflow: visible;
}

.attributes-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow-y: auto;
}

.attribute-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: #f6f8fa;
  border-radius: 6px;
  font-size: 12px;
  max-width: 100%;
  overflow: hidden;
  min-height: 36px;
  align-items: center;
}

.attribute-key {
  color: #656d76;
  font-family: monospace;
  flex-shrink: 0;
  max-width: 50%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attribute-value {
  color: #24292f;
  word-break: break-all;
  text-align: right;
}

/* Action Section */
.action-section {
  text-align: center;
  padding: 8px 0;
}

.action-section .el-button {
  width: 100%;
  padding: 14px;
  font-size: 15px;
}

.hint {
  margin-top: 10px;
  font-size: 12px;
  color: #656d76;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .song-detail {
    padding: 16px;
  }

  .song-header {
    height: 90px;
    min-height: 90px;
    gap: 12px;
  }

  .song-icon {
    width: 56px;
    height: 56px;
  }

  .song-name {
    font-size: 17px;
    height: auto;
    line-height: 1.4;
    white-space: normal;
  }

  .song-name .el-tag {
    margin-left: 4px;
  }

  .song-reading {
    font-size: 13px;
  }

  .song-name-en {
    font-size: 12px;
    margin-bottom: 8px;
  }

  .song-badges {
    margin-top: 8px;
  }

  .action-section .el-button {
    padding: 16px;
    font-size: 16px;
    min-height: 48px;
  }

  .difficulty-card {
    min-width: calc(50% - 4px);
    max-width: none;
    height: 68px;
    flex: 0 0 calc(50% - 4px);
  }

  .difficulty-content {
    padding: 0 10px;
    gap: 8px;
  }

  .difficulty-badge {
    width: 36px;
    height: 36px;
    font-size: 13px;
  }

  .difficulty-name {
    font-size: 14px;
  }

  .difficulty-level {
    font-size: 13px;
  }

  .metadata-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .metadata-item {
    padding: 10px 14px;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .metadata-label {
    font-size: 12px;
  }

  .metadata-value {
    font-size: 14px;
  }

  .section-title {
    font-size: 15px;
    margin-bottom: 14px;
  }

  .mod-item {
    padding: 14px;
  }

  .mod-name {
    font-size: 15px;
  }

  .attributes-list {
    max-height: none;
    overflow-y: visible;
  }

  .attribute-item {
    flex-direction: column;
    gap: 6px;
    align-items: flex-start;
    padding: 10px 12px;
    overflow: visible;
    min-height: auto;
  }

  .attribute-key {
    max-width: 100%;
    white-space: normal;
    word-break: break-all;
  }

  .attribute-value {
    text-align: left;
    width: 100%;
    word-break: break-all;
  }
}

/* Small mobile optimizations */
@media (max-width: 480px) {
  .attributes-list {
    max-height: none;
    overflow-y: visible;
  }

  .song-detail {
    padding: 12px;
    max-width: 100%;
    box-sizing: border-box;
  }

  .song-header {
    height: 90px;
    min-height: 90px;
    gap: 10px;
  }

  .song-icon {
    width: 48px;
    height: 48px;
  }

  .song-icon .el-icon {
    font-size: 28px;
  }

  .song-titles {
    max-width: calc(100% - 58px);
  }

  .song-name {
    font-size: 15px;
    white-space: normal;
    height: auto;
    min-height: 24px;
    word-break: break-word;
  }

  .song-name .el-tag {
    margin-left: 4px;
    margin-top: 2px;
  }

  .song-reading {
    font-size: 12px;
  }

  .song-name-en {
    font-size: 11px;
  }

  .song-badges {
    margin-top: 6px;
  }

  .difficulty-card {
    min-width: 100%;
    max-width: 100%;
    height: 60px;
    flex: 0 0 100%;
  }

  .difficulty-list {
    gap: 6px;
  }

  .difficulty-badge {
    width: 32px;
    height: 32px;
    font-size: 12px;
  }

  .difficulty-content {
    padding: 0 10px;
    gap: 8px;
  }

  .difficulty-name {
    font-size: 13px;
    white-space: normal;
    word-break: break-word;
  }

  .action-section .el-button {
    padding: 14px;
    font-size: 15px;
    min-height: 44px;
  }

  .metadata-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .metadata-item {
    padding: 8px 12px;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .metadata-label {
    font-size: 11px;
  }

  .metadata-value {
    font-size: 13px;
    word-break: break-word;
    text-align: right;
    flex: 1;
  }

  .mod-item {
    padding: 12px;
  }

  .mod-header {
    flex-wrap: wrap;
    gap: 6px;
  }

  .mod-name {
    font-size: 14px;
    word-break: break-word;
    flex: 1;
  }

  .mod-meta {
    gap: 8px;
    font-size: 11px;
  }

  .mod-list .mod-path {
    font-size: 10px;
    word-break: break-all;
    white-space: normal;
  }

  .attribute-item {
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    align-items: flex-start;
    overflow: visible;
  }

  .attribute-key {
    max-width: 100%;
    word-break: break-all;
    white-space: normal;
    font-size: 11px;
    color: #8c959f;
  }

  .attribute-value {
    text-align: left;
    word-break: break-all;
    max-width: 100%;
    font-size: 13px;
    color: #24292f;
    width: 100%;
  }

  .section-title {
    font-size: 14px;
    margin-bottom: 12px;
  }
}
</style>
