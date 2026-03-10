<script setup lang="ts">
import type { GameStatusDisplay } from '@/types'
import { Refresh, VideoPlay } from '@element-plus/icons-vue'

defineProps<{
  status: GameStatusDisplay | null
  loading?: boolean
  autoRefresh?: boolean
  refreshInterval?: number
}>()

const emit = defineEmits<{
  'update:autoRefresh': [value: boolean]
  'update:refreshInterval': [value: number]
  'refresh': []
}>()

const handleRefresh = () => {
  emit('refresh')
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
    'running': '游戏运行中',
    'not_running': '游戏未运行',
    'busy': '处理中',
    'error': '错误',
  }
  return map[status] || status
}

const getEdenText = (isEden: boolean): string => {
  return isEden ? 'Eden 版本' : '标准版本'
}

const getDifficultyClass = (difficulty: string): string => {
  const map: Record<string, string> = {
    'EASY': 'diff-easy',
    'NORMAL': 'diff-normal',
    'HARD': 'diff-hard',
    'EXTREME': 'diff-extreme',
    'EXTRA EXTREME': 'diff-exex',
    'RESERVED': 'diff-reserved',
  }
  // Handle unknown difficulty values like "Unknown(19)"
  if (difficulty.startsWith('Unknown')) {
    return 'diff-unknown'
  }
  return map[difficulty] || 'diff-normal'
}

const getDifficultyShortName = (difficulty: string): string => {
  const map: Record<string, string> = {
    'EASY': 'EASY',
    'NORMAL': 'NORMAL',
    'HARD': 'HARD',
    'EXTREME': 'EXTREME',
    'EXTRA_EXTREME': 'EXEXTREME',
    'RESERVED': 'RESERVED',
  }
  // Handle unknown difficulty values like "Unknown(19)"
  if (difficulty.startsWith('Unknown')) {
    // Extract the number from "Unknown(19)" and show as "UNK(19)"
    const match = difficulty.match(/Unknown\((\d+)\)/)
    if (match) {
      return `UNK(${match[1]})`
    }
    return 'UNKNOWN'
  }
  return map[difficulty] || difficulty
}

const handleAutoRefreshChange = (value: boolean) => {
  emit('update:autoRefresh', value)
}

const handleIntervalChange = (value: number) => {
  emit('update:refreshInterval', value)
}
</script>

<template>
  <div class="game-status">
    <el-card shadow="never" :body-style="{ position: 'relative' }">
      <!-- Subtle loading indicator at top -->
      <div v-if="loading" class="loading-indicator">
        <div class="loading-bar"></div>
      </div>

      <div class="status-content">
        <div class="status-header">
          <span class="status-label">游戏状态</span>
          <div class="status-actions">
            <el-tag
              v-if="status"
              :type="getStatusType(status.status)"
              size="large"
            >
              {{ getStatusText(status.status) }}
            </el-tag>
            <el-tag v-else type="info" size="large">未知</el-tag>
            <el-button
              circle
              size="small"
              :class="{ 'is-refreshing': loading }"
              @click="handleRefresh"
              title="立即刷新"
            >
              <el-icon :class="{ 'is-spinning': loading }"><refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- Refresh Controls -->
        <el-divider />
        <div class="refresh-controls">
          <div class="refresh-row">
            <el-switch
              :model-value="autoRefresh"
              @update:model-value="handleAutoRefreshChange"
              active-text="自动刷新"
              inline-prompt
            />
            <span class="refresh-hint">{{ autoRefresh ? '已开启' : '已关闭' }}</span>
          </div>
          <div v-if="autoRefresh" class="refresh-row interval-row">
            <span class="interval-label">刷新间隔:</span>
            <el-slider
              :model-value="refreshInterval"
              @update:model-value="handleIntervalChange"
              :min="1"
              :max="10"
              :step="1"
              show-stops
              :marks="{ 1: '1s', 5: '5s', 10: '10s' }"
              style="flex: 1;"
            />
            <span class="interval-value">{{ refreshInterval }}s</span>
          </div>
        </div>

        <template v-if="status?.status === 'running'">
          <el-divider />

          <div class="status-details">
            <div class="detail-item">
              <span class="detail-label">版本:</span>
              <el-tag
                :type="status.isEdenVersion ? 'warning' : 'success'"
                size="small"
              >
                {{ getEdenText(status.isEdenVersion) }}
              </el-tag>
            </div>

            <div class="detail-item">
              <span class="detail-label">偏移量:</span>
              <code class="offset-value">0x{{ (status.edenOffset ?? 0).toString(16).toUpperCase() }}</code>
            </div>

            <template v-if="status.currentSong && 1 !== 1">
              <el-divider />
              <div class="current-song-section">
                <div class="song-card">
                  <div class="song-icon">
                    <el-icon :size="24"><VideoPlay /></el-icon>
                  </div>
                  <div class="song-info">
                    <div class="song-label">当前歌曲</div>
                    <div class="song-name" :title="status.currentSong.name">
                      {{ status.currentSong.name }}
                    </div>
                  </div>
                </div>
                <div class="difficulty-card">
                  <div class="difficulty-label">难度</div>
                  <div class="difficulty-badge" :class="getDifficultyClass(status.currentSong.difficultyType)">
                    {{ getDifficultyShortName(status.currentSong.difficultyType) }}
                  </div>
                </div>
              </div>
            </template>
          </div>
        </template>
      </div>
    </el-card>

    <el-alert
      v-if="status?.status === 'not_running'"
      title="提示"
      type="warning"
      :closable="false"
      class="status-alert"
    >
      请先启动 Project DIVA MegaMix+ 游戏
    </el-alert>
  </div>
</template>

<style scoped>
.game-status {
  margin-bottom: 16px;
}

.status-content {
  min-height: 100px;
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  min-width: 60px;
}

.detail-value {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.offset-value {
  font-family: monospace;
  background: var(--el-fill-color);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-alert {
  margin-top: 12px;
}

.refresh-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.refresh-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.interval-row {
  padding-left: 44px;
}

.refresh-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.interval-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  min-width: 60px;
}

.interval-value {
  font-size: 13px;
  color: var(--el-text-color-primary);
  font-weight: 500;
  min-width: 30px;
  text-align: right;
}

.status-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-actions .el-button {
  margin-left: 4px;
}

/* Loading indicator - subtle animation instead of v-loading mask */
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
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(250%);
  }
}

/* Current Song Section Styles */
.current-song-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.song-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--el-color-primary-light-7);
}

.song-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: var(--el-color-primary);
  border-radius: 50%;
  color: white;
  flex-shrink: 0;
}

.song-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.song-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.song-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.difficulty-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--el-fill-color-light);
  border-radius: 10px;
  padding: 12px 16px;
}

.difficulty-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.difficulty-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  min-width: 60px;
}

/* Difficulty Colors */
.diff-easy {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
}

.diff-normal {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: white;
}

.diff-hard {
  background: linear-gradient(135deg, #e6a23c 0%, #eebe77 100%);
  color: white;
}

.diff-extreme {
  background: linear-gradient(135deg, #f56c6c 0%, #f89898 100%);
  color: white;
}

.diff-exex {
  background: linear-gradient(135deg, #9b59b6 0%, #bb8fce 100%);
  color: white;
  box-shadow: 0 0 10px rgba(155, 89, 182, 0.4);
}

.diff-reserved {
  background: linear-gradient(135deg, #909399 0%, #b1b3b8 100%);
  color: white;
}

.diff-unknown {
  background: linear-gradient(135deg, #606266 0%, #909399 100%);
  color: white;
  border: 1px dashed #c0c4cc;
}

/* Refresh button spin animation */
.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Refresh button hover effect */
.is-refreshing {
  opacity: 0.8;
  cursor: not-allowed;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .status-content {
    min-height: auto;
  }

  .status-header {
    flex-wrap: wrap;
    gap: 10px;
  }

  .status-label {
    font-size: 15px;
  }

  .refresh-controls {
    gap: 12px;
  }

  .refresh-row {
    flex-wrap: wrap;
    gap: 10px;
  }

  .interval-row {
    padding-left: 0;
    padding-top: 8px;
    border-top: 1px dashed var(--el-border-color-lighter);
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .interval-label {
    font-size: 14px;
  }

  .interval-value {
    text-align: left;
    font-size: 14px;
  }

  .detail-item {
    flex-wrap: wrap;
    gap: 6px;
  }

  .detail-label {
    font-size: 14px;
    min-width: 50px;
  }

  .status-actions .el-button {
    min-height: 36px;
    min-width: 36px;
  }
}

/* Small mobile optimizations */
@media (max-width: 480px) {
  .game-status {
    margin-bottom: 12px;
  }

  .status-content {
    padding: 4px;
  }

  .status-header {
    gap: 8px;
    flex-wrap: wrap;
  }

  .status-label {
    font-size: 14px;
  }

  .status-actions {
    flex-wrap: wrap;
    gap: 6px;
  }

  .status-actions .el-tag {
    font-size: 12px;
    padding: 0 8px;
    height: 28px;
    line-height: 26px;
  }

  .refresh-row {
    gap: 8px;
    flex-wrap: wrap;
  }

  .interval-row {
    padding-top: 6px;
    gap: 8px;
  }

  .refresh-hint {
    font-size: 11px;
  }

  .interval-label {
    font-size: 13px;
    min-width: auto;
  }

  .interval-value {
    font-size: 13px;
  }

  .detail-item {
    gap: 4px;
    flex-wrap: wrap;
  }

  .detail-label {
    font-size: 13px;
    min-width: auto;
  }

  .offset-value {
    font-size: 11px;
  }

  .refresh-controls :deep(.el-slider__marks-text) {
    font-size: 10px;
  }
}
</style>
