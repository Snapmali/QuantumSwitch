<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Plus, Search, ArrowRight } from '@element-plus/icons-vue'
import { aliasApi } from '@/api'
import type { SongAlias } from '@/types'

const { t } = useI18n()

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// State
const aliases = ref<SongAlias[]>([])
const loading = ref(false)
const saving = ref(false)
const searchQuery = ref('')

// Form state
const editingId = ref<string | null>(null)
const aliasInput = ref('')
const songNameInput = ref('')

// Computed
const filteredAliases = computed(() => {
  if (!searchQuery.value) return aliases.value
  const query = searchQuery.value.toLowerCase()
  return aliases.value.filter(a =>
    a.alias.toLowerCase().includes(query) ||
    a.songName.toLowerCase().includes(query)
  )
})

const isEditing = computed(() => editingId.value !== null)

// Load aliases
const loadAliases = async () => {
  loading.value = true
  try {
    const response = await aliasApi.getAll()
    aliases.value = response.data.data || []
  } catch (err) {
    console.error('Failed to load aliases:', err)
    ElMessage.error(t('alias.loadFailed'))
  } finally {
    loading.value = false
  }
}

// Reset form
const resetForm = () => {
  editingId.value = null
  aliasInput.value = ''
  songNameInput.value = ''
}

// Handle save (create or update)
const handleSave = async () => {
  if (!aliasInput.value.trim()) {
    ElMessage.warning(t('alias.aliasRequired'))
    return
  }
  if (!songNameInput.value.trim()) {
    ElMessage.warning(t('alias.songNameRequired'))
    return
  }

  saving.value = true
  try {
    if (isEditing.value) {
      // Update existing
      const response = await aliasApi.update(editingId.value!, {
        alias: aliasInput.value.trim(),
        songName: songNameInput.value.trim()
      })
      const index = aliases.value.findIndex(a => a.id === editingId.value)
      if (index !== -1) {
        aliases.value[index] = response.data.data!
      }
      ElMessage.success(t('alias.updateSuccess'))
    } else {
      // Create new
      const response = await aliasApi.create({
        alias: aliasInput.value.trim(),
        songName: songNameInput.value.trim()
      })
      aliases.value.push(response.data.data!)
      ElMessage.success(t('alias.createSuccess'))
    }
    resetForm()
  } catch (err: any) {
    const msg = err.response?.data?.error || (isEditing.value ? t('alias.updateFailed') : t('alias.createFailed'))
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

// Handle edit
const handleEdit = (alias: SongAlias) => {
  editingId.value = alias.id
  aliasInput.value = alias.alias
  songNameInput.value = alias.songName
}

// Handle cancel edit
const handleCancelEdit = () => {
  resetForm()
}

// Handle delete
const handleDelete = async (alias: SongAlias) => {
  try {
    await ElMessageBox.confirm(
      t('alias.deleteConfirm', { alias: alias.alias }),
      t('common.warning'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await aliasApi.delete(alias.id)
    aliases.value = aliases.value.filter(a => a.id !== alias.id)

    // If deleting the one being edited, reset form
    if (editingId.value === alias.id) {
      resetForm()
    }

    ElMessage.success(t('alias.deleteSuccess'))
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(t('alias.deleteFailed'))
    }
  }
}

// Close dialog
const handleClose = () => {
  emit('update:visible', false)
  resetForm()
  searchQuery.value = ''
}

// Initialize
onMounted(() => {
  if (props.visible) {
    loadAliases()
  }
})

// Watch visible to load data
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    loadAliases()
  }
})
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="t('alias.manageTitle')"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
    class="alias-manager-dialog"
  >
    <div class="alias-manager">
      <!-- Form Section -->
      <div class="alias-form-section">
        <el-input
          v-model.trim="aliasInput"
          :placeholder="t('alias.aliasPlaceholder')"
          clearable
          class="form-input"
        />
        <el-input
          v-model.trim="songNameInput"
          :placeholder="t('alias.songNamePlaceholder')"
          clearable
          class="form-input"
        />
        <el-button
          type="primary"
          :loading="saving"
          :icon="isEditing ? Edit : Plus"
          @click="handleSave"
          class="save-btn"
        >
          {{ isEditing ? t('common.save') : t('common.add') }}
        </el-button>
        <el-button
          v-if="isEditing"
          @click="handleCancelEdit"
          class="cancel-btn"
        >
          {{ t('common.cancel') }}
        </el-button>
      </div>

      <!-- Search Section -->
      <div class="alias-search-section">
        <el-input
          v-model.trim="searchQuery"
          :placeholder="t('alias.searchPlaceholder')"
          clearable
          :prefix-icon="Search"
          class="search-input"
        />
        <span class="alias-count">
          {{ t('alias.totalCount', { count: filteredAliases.length }) }}
        </span>
      </div>

      <!-- List Section -->
      <div v-loading="loading" class="alias-list-section">
        <div v-if="filteredAliases.length === 0" class="alias-empty">
          <el-empty :description="t('alias.noAliases')" />
        </div>
        <div v-else class="alias-list">
          <div
            v-for="alias in filteredAliases"
            :key="alias.id"
            :class="['alias-item', { 'is-editing': editingId === alias.id }]"
          >
            <div class="alias-info">
              <span class="alias-name">{{ alias.alias }}</span>
              <el-icon class="alias-arrow"><ArrowRight /></el-icon>
              <span class="alias-song">{{ alias.songName }}</span>
            </div>
            <div class="alias-actions">
              <el-button
                type="primary"
                size="small"
                circle
                @click="handleEdit(alias)"
              >
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button
                type="danger"
                size="small"
                circle
                @click="handleDelete(alias)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.alias-manager-dialog :deep(.el-dialog__body) {
  padding: 16px 20px;
}

.alias-manager {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.alias-form-section {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.form-input {
  flex: 1;
  min-width: 120px;
}

.save-btn {
  flex-shrink: 0;
}

.cancel-btn {
  flex-shrink: 0;
  margin-left: 0 !important;
}

.alias-search-section {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  flex: 1;
}

.alias-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.alias-list-section {
  max-height: 300px;
  overflow-y: auto;
}

.alias-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alias-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
  transition: all 0.2s;
}

.alias-item:hover {
  background-color: var(--el-fill-color-light);
}

.alias-item.is-editing {
  background-color: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.alias-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.alias-name {
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

.alias-song {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alias-actions {
  display: flex;
  flex-shrink: 0;
}

.alias-empty {
  padding: 20px 0;
}

/* Scrollbar styling */
.alias-list-section::-webkit-scrollbar {
  width: 6px;
}

.alias-list-section::-webkit-scrollbar-track {
  background: var(--el-fill-color-light);
}

.alias-list-section::-webkit-scrollbar-thumb {
  background: var(--el-border-color);
  border-radius: 3px;
}

.alias-list-section::-webkit-scrollbar-thumb:hover {
  background: var(--el-text-color-secondary);
}
</style>
