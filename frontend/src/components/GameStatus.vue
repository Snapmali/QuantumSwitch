<script setup lang="ts">
import type { GameStatusDisplay } from '@/types'
import { useI18n } from 'vue-i18n'
import { getDifficultyShortLabel, getDifficultyStyle, getDifficultyDisabledStyle, getChartStyleDisplayName } from '@/types'
import { Refresh, VideoPlay, Link } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps<{
  status: GameStatusDisplay | null
  loading?: boolean
  autoRefresh?: boolean
  refreshInterval?: number
}>()

const emit = defineEmits<{
  'update:autoRefresh': [value: boolean]
  'update:refreshInterval': [value: number]
  'refresh': []
  'reattach': []
  'song-click': [songId: number]  // 新增：点击当前歌曲
}>()

const handleRefresh = () => {
  emit('refresh')
}

const handleReattach = () => {
  emit('reattach')
}

const getStatusType = (status: string): string => {
  const map: Record<string, string> = {
    'running': 'success',
    'not_running': 'danger',
    'busy': 'warning',
    'error': 'danger',
  }
  return map[status] || 'info'
}

const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    'running': t('gameStatus.running'),
    'not_running': t('gameStatus.notRunning'),
    'busy': t('gameStatus.busy'),
    'error': t('gameStatus.error'),
  }
  return map[status] || status
}

const getGameStateText = (state?: string): string => {
  const map: Record<string, string> = {
    'UNKNOWN': t('gameState.unknown'),
    'NOT_READY': t('gameState.notReady'),
    'LOADING': t('gameState.loading'),
    'INTRO': t('gameState.intro'),
    'TITLE': t('gameState.title'),
    'RHYTHM_GAME': t('gameState.rhythmGame'),
    'CUSTOM_PLAYLIST': t('gameState.customPlaylist'),
    'INGAME': t('gameState.ingame'),
    'CUSTOMIZATION': t('gameState.customization'),
    'GALLERY': t('gameState.gallery'),
    'MAIN_MENU': t('gameState.mainMenu'),
    'OPTIONS': t('gameState.options'),
  }
  return map[state || ''] || state || t('common.unknown')
}

// 获取难度徽章样式（根据启用状态返回不同样式）
const getDifficultyBadgeStyle = (diff: { name: string; enabled: boolean }): Record<string, string> => {
  if (!diff.enabled) {
    // 禁用状态：使用对应难度的浅色版本
    return getDifficultyDisabledStyle(diff.name)
  }

  // 启用状态：使用统一的颜色配置
  return getDifficultyStyle(diff.name)
}

const handleAutoRefreshChange = (value: boolean) => {
  emit('update:autoRefresh', value)
}

const handleIntervalChange = (value: number) => {
  emit('update:refreshInterval', value)
}

const handleSongClick = () => {
  if (props.status?.currentSongInfo?.id) {
    emit('song-click', props.status.currentSongInfo.id)
  }
}

// 获取状态标签的显示配置（类型和文本）
const resolveStatusDisplay = (status: GameStatusDisplay | null) => {
  if (!status) {
    return { type: 'info', text: t('common.unknown') }
  }

  if (status.status !== 'running') {
    return { type: getStatusType(status.status), text: getStatusText(status.status) }
  }

  // 游戏运行中状态
  const gameState = status.gameState
  const isIngame = gameState === 'INGAME'
  const isWarningState = ['UNKNOWN', 'NOT_READY', null, undefined, ''].includes(gameState)

  return {
    type: isIngame ? 'success' : isWarningState ? 'warning' : 'primary',
    text: getGameStateText(gameState)
  }
}
</script>

<template>
  <div class="game-status">
    <el-card shadow="never" :body-style="{ position: 'relative', padding: '12px 16px' }">
      <!-- Loading indicator -->
      <div v-if="loading" class="loading-indicator">
        <div class="loading-bar"></div>
      </div>

      <!-- Header: Status + Controls -->
      <div class="status-header">
        <span class="status-title">{{ t('gameStatus.title') }}</span>
        <div class="status-right">
          <el-tag :type="resolveStatusDisplay(status).type" size="small" effect="light" class="status-tag">
            {{ resolveStatusDisplay(status).text }}
          </el-tag>
          <div class="header-actions">
            <el-button
              circle
              size="small"
              :class="{ 'is-refreshing': loading }"
              @click="handleRefresh"
              :title="t('gameStatus.refreshNow')"
            >
              <el-icon :class="{ 'is-spinning': loading }"><Refresh /></el-icon>
            </el-button>
            <el-button
              circle
              size="small"
              :disabled="loading"
              @click="handleReattach"
              :title="t('gameStatus.reattach')"
            >
              <el-icon><Link /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <!-- Compact Refresh Controls -->
      <div class="refresh-control" :class="{ 'no-song': !(status?.status === 'running' && status?.currentSongInfo) }">
        <div class="refresh-left">
          <span class="refresh-label">{{ t('gameStatus.autoRefresh') }}</span>
          <el-switch
            :model-value="autoRefresh"
            @update:model-value="handleAutoRefreshChange"
            size="small"
          />
        </div>
        <div v-if="autoRefresh" class="interval-control">
          <el-slider
            :model-value="refreshInterval"
            @update:model-value="handleIntervalChange"
            :min="1"
            :max="10"
            :step="1"
            :show-tooltip="false"
            size="small"
            class="interval-slider"
          />
          <span class="interval-value">{{ refreshInterval }}s</span>
        </div>
      </div>

      <!-- Current Song (only when running) -->
      <template v-if="status?.status === 'running' && status?.currentSongInfo">
        <div class="song-card clickable" @click="handleSongClick">
          <div class="song-left">
            <div class="song-icon" :class="{ 'is-playing': status?.isIngame }">
              <el-icon :size="20"><VideoPlay /></el-icon>
            </div>
            <div class="song-info">
              <div class="song-name-row">
                <span class="song-name" :title="status.currentSongInfo.name">
                  {{ status.currentSongInfo.name }}
                </span>
                <span class="song-id">#{{ status.currentSongInfo.id }}</span>
              </div>
              <div class="song-meta">
                <div class="meta-left">
                  <span class="meta-label">{{ t('gameStatus.currentSelection') }}</span>
                  <el-tag
                    v-if="status.currentChartStyle"
                    size="small"
                    effect="plain"
                    class="style-tag"
                  >
                    {{ getChartStyleDisplayName(status.currentChartStyle) }}
                  </el-tag>
                </div>
                <div class="difficulties-row">
                  <span
                    v-for="diff in status.currentSongInfo.difficulties"
                    :key="diff.name"
                    class="diff-badge"
                    :class="{ 'diff-disabled': !diff.enabled }"
                    :style="getDifficultyBadgeStyle(diff)"
                  >
                    {{ getDifficultyShortLabel(diff.name) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-card>

    <el-alert
      v-if="status?.status === 'not_running'"
      :title="t('common.info')"
      type="warning"
      :closable="false"
      class="status-alert"
    >
      {{ t('gameStatus.gameNotRunningTip') }}
    </el-alert>
  </div>
</template>

<style scoped>
.game-status {
  margin-bottom: 0;
}

/* Header Section */
.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.status-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  flex-shrink: 0;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
}

/* Refresh Control */
.refresh-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-top: 1px solid var(--el-border-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.refresh-control.no-song {
  padding-bottom: 0;
  border-bottom: none;
}

.refresh-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.refresh-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.interval-control {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.interval-slider {
  width: 120px;
  flex-shrink: 0;
}

.interval-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-light);
  border-radius: 4px;
  padding: 3px 8px;
  min-width: 38px;
  text-align: center;
  flex-shrink: 0;
}

/* Song Card */
.song-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 12px;
  padding: 12px;
  height: 72px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 10px;
  border: 1px solid var(--el-color-primary-light-8);
  transition: all 0.2s ease;
}

.song-card.clickable {
  cursor: pointer;
}

.song-card.clickable:hover {
  background: linear-gradient(135deg, var(--el-color-primary-light-8) 0%, var(--el-color-primary-light-9) 100%);
  border-color: var(--el-color-primary-light-7);
}

.song-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  width: 100%;
}

.song-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--el-color-primary);
  border-radius: 8px;
  color: white;
  flex-shrink: 0;
}

.song-icon.is-playing {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.song-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.song-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.song-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  height: 22px;
  line-height: 22px;
}

.song-id {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  font-weight: 500;
  flex-shrink: 0;
}

.song-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.meta-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.style-tag {
  font-size: 11px;
  height: 20px;
  line-height: 18px;
  padding: 0 6px;
  transition: none;
}

/* Difficulties */
.difficulties-row {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  margin-left: auto;
}

.diff-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 20px;
  border-radius: 4px;
  font-size:  11px;
  font-weight: 600;
  color: white;
}

.diff-badge.diff-disabled {
  opacity: 0.4;
}

/* Loading indicator */
.loading-indicator {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  overflow: hidden;
  z-index: 10;
}

.loading-bar {
  height: 100%;
  width: 40%;
  background: linear-gradient(90deg, transparent, var(--el-color-primary), transparent);
  animation: loading-slide 1s infinite ease-in-out;
}

@keyframes loading-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(250%); }
}

/* Status Alert */
.status-alert {
  margin-top: 8px;
}

/* Spin animation */
.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.is-refreshing {
  opacity: 0.8;
  cursor: not-allowed;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .status-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .song-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .difficulties-row {
    margin-left: auto;
  }
}

@media (max-width: 480px) {
  :deep(.el-card__body) {
    padding: 10px 12px !important;
  }

  .status-header {
    gap: 6px;
  }

  .status-title {
    font-size: 13px;
  }

  .status-right {
    gap: 8px;
  }

  .refresh-control {
    gap: 12px;
  }

  .refresh-left {
    gap: 8px;
  }

  .interval-control {
    gap: 8px;
  }

  .interval-slider {
    width: 120px;
  }

  .interval-value {
    font-size: 11px;
    padding: 2px 6px;
    min-width: 34px;
  }

  .song-card {
    padding: 10px;
    margin-top: 10px;
  }

  .song-icon {
    width: 36px;
    height: 36px;
  }

  .song-name {
    font-size: 14px;
  }

  .diff-badge {
    width: 24px;
    height: 20px;
    font-size:  11px;
  }
}
</style>
