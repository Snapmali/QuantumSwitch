<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { watch, ref } from 'vue'
import type { SongAliasMatchItem } from '@/types'
import { ArrowRight } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps<{
  matches: SongAliasMatchItem[]
  visible: boolean
  selectedIndex: number
}>()

const emit = defineEmits<{
  select: [item: SongAliasMatchItem]
}>()

const listRef = ref<HTMLElement | null>(null)

watch(() => props.selectedIndex, (index) => {
  if (index < 0 || !listRef.value) return
  const items = listRef.value.querySelectorAll('.alias-dropdown-item')
  const selectedEl = items[index] as HTMLElement | undefined
  selectedEl?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
})

const handleSelect = (item: SongAliasMatchItem) => {
  emit('select', item)
}
</script>

<template>
  <div v-if="visible && matches.length > 0" class="alias-dropdown">
    <div class="alias-dropdown-header">
      {{ t('alias.matchesFound', { count: matches.length }) }}
    </div>
    <div ref="listRef" class="alias-dropdown-list">
      <div
        v-for="(item, index) in matches"
        :key="index"
        class="alias-dropdown-item"
        :class="{ selected: index === selectedIndex }"
        tabindex="0"
        @click="handleSelect(item)"
      >
        <span class="alias-text">{{ item.alias }}</span>
        <el-icon class="alias-arrow"><ArrowRight /></el-icon>
        <span class="song-name">{{ item.songName }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alias-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  margin-top: 4px;
  max-height: 180px;
  display: flex;
  flex-direction: column;
}

.alias-dropdown-header {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  flex-shrink: 0;
}

.alias-dropdown-list {
  overflow-y: auto;
  flex: 1;
}

.alias-dropdown-item {
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.2s;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.alias-dropdown-item:last-child {
  border-bottom: none;
}

.alias-dropdown-item:hover,
.alias-dropdown-item.selected {
  background-color: var(--el-fill-color-light);
}

.alias-text {
  font-weight: 500;
  color: var(--el-color-primary);
  flex-shrink: 0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alias-arrow {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.song-name {
  color: var(--el-text-color-regular);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}

/* Scrollbar styling */
.alias-dropdown-list::-webkit-scrollbar {
  width: 6px;
}

.alias-dropdown-list::-webkit-scrollbar-track {
  background: var(--el-fill-color-light);
}

.alias-dropdown-list::-webkit-scrollbar-thumb {
  background: var(--el-border-color);
  border-radius: 3px;
}

.alias-dropdown-list::-webkit-scrollbar-thumb:hover {
  background: var(--el-text-color-secondary);
}
</style>
