import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Language } from 'element-plus/es/locale'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import i18n, { type LocaleType } from '@/locales'

const elementLocales: Record<LocaleType, Language> = {
  'zh-CN': zhCn,
  'en-US': en,
}

export const useLocaleStore = defineStore('locale', () => {
  // State
  const currentLocale = ref<LocaleType>(i18n.global.locale.value as LocaleType)

  // Getters
  const locale = computed(() => currentLocale.value)
  const elementPlusLocale = computed(() => elementLocales[currentLocale.value])

  // Actions
  const switchLocale = (locale: LocaleType) => {
    if (currentLocale.value === locale) return

    currentLocale.value = locale
    i18n.global.locale.value = locale
    localStorage.setItem('app-locale', locale)
  }

  const initializeLocale = () => {
    const saved = localStorage.getItem('app-locale') as LocaleType
    if (saved && ['zh-CN', 'en-US'].includes(saved)) {
      currentLocale.value = saved
      i18n.global.locale.value = saved
    }
  }

  return {
    currentLocale,
    locale,
    elementPlusLocale,
    switchLocale,
    initializeLocale,
  }
})
