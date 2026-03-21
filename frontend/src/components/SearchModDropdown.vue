<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { watch, ref } from 'vue'
import type { ModInfoSearchItem } from '@/types'

const { t } = useI18n()

const props = defineProps<{
  matches: ModInfoSearchItem[]
  visible: boolean
  selectedIndex: number
}>()

const emit = defineEmits<{
  select: [item: ModInfoSearchItem]
}>()

const listRef = ref<HTMLElement | null>(null)

watch(() => props.selectedIndex, (index) => {
  if (index < 0 || !listRef.value) return
  const items = listRef.value.querySelectorAll('.mod-dropdown-item')
  const selectedEl = items[index] as HTMLElement | undefined
  selectedEl?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
})

const handleSelect = (item: ModInfoSearchItem) => {
  emit('select', item)
}
</script>

<template>
  <div v-if="visible && matches.length > 0" class="mod-dropdown">
    <div class="mod-dropdown-header">
      {{ t('mod.matchesFound', { count: matches.length }) }}
    </div>
    <div ref="listRef" class="mod-dropdown-list">
      <div
        v-for="(item, index) in matches"
        :key="item.id"
        class="mod-dropdown-item"
        :class="{ selected: index === selectedIndex, disabled: !item.enabled }"
        tabindex="0"
        @click="handleSelect(item)"
      >
        <div class="mod-info">
          <span class="mod-name">{{ item.name }}</span>
          <span v-if="item.author" class="mod-author">by {{ item.author }}</span>
        </div>
        <div class="mod-meta">
          <span class="mod-song-count">{{ item.songCount }} {{ t('mod.songs') }}</span>
          <span v-if="!item.enabled" class="mod-disabled-badge">{{ t('mod.disabled') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mod-dropdown {
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
  max-height: 240px;
  display: flex;
  flex-direction: column;
}

.mod-dropdown-header {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  flex-shrink: 0;
}

.mod-dropdown-list {
  overflow-y: auto;
  flex: 1;
}

.mod-dropdown-item {
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: background-color 0.2s;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.mod-dropdown-item:last-child {
  border-bottom: none;
}

.mod-dropdown-item:hover,
.mod-dropdown-item.selected {
  background-color: var(--el-fill-color-light);
}

.mod-dropdown-item.disabled {
  opacity: 0.6;
}

.mod-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.mod-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mod-author {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mod-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}

.mod-song-count {
  font-size: 11px;
  color: var(--el-color-primary);
  font-weight: 500;
}

.mod-disabled-badge {
  font-size: 10px;
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  padding: 1px 4px;
  border-radius: 2px;
}

/* Scrollbar styling */
.mod-dropdown-list::-webkit-scrollbar {
  width: 6px;
}

.mod-dropdown-list::-webkit-scrollbar-track {
  background: var(--el-fill-color-light);
}

.mod-dropdown-list::-webkit-scrollbar-thumb {
  background: var(--el-border-color);
  border-radius: 3px;
}

.mod-dropdown-list::-webkit-scrollbar-thumb:hover {
  background: var(--el-text-color-secondary);
}
</style>
