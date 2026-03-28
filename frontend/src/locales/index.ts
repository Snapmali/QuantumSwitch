import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import enUS from './en-US'

export const messages = {
  'zh-CN': zhCN,
  'en-US': enUS,
}

export type LocaleType = 'zh-CN' | 'en-US'

// Get initial locale from localStorage or detect browser language
const getInitialLocale = (): LocaleType => {
  // 1. Check if user has manually selected a language
  const saved = localStorage.getItem('app-locale') as LocaleType
  if (saved && ['zh-CN', 'en-US'].includes(saved)) {
    return saved
  }

  // 2. First visit, detect browser language
  const browserLang = navigator.language.toLowerCase()
  if (browserLang.startsWith('zh')) {
    return 'zh-CN'
  }

  // 3. Default to English for other languages
  return 'en-US'
}

const i18n = createI18n({
  legacy: false, // Use Composition API mode
  locale: getInitialLocale(),
  fallbackLocale: 'zh-CN',
  messages,
  silentTranslationWarn: true,
  silentFallbackWarn: true,
})

export default i18n
