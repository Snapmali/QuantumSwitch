<script setup lang="ts">
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'
import type { LocaleType } from '@/locales'

const localeStore = useLocaleStore()

const currentLocale = computed(() => localeStore.currentLocale)

const localeOptions: { value: LocaleType; label: string }[] = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en-US', label: 'English' },
]

const handleLocaleChange = (value: LocaleType) => {
  localeStore.switchLocale(value)
}
</script>

<template>
  <el-select
    :model-value="currentLocale"
    size="small"
    class="language-switch"
    @update:model-value="handleLocaleChange($event as LocaleType)"
  >
    <el-option
      v-for="opt in localeOptions"
      :key="opt.value"
      :value="opt.value"
      :label="opt.label"
    />
  </el-select>
</template>

<style scoped>
.language-switch {
  width: 100px;
}

.language-switch :deep(.el-input__wrapper) {
  padding: 0 8px;
}
</style>
