import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import enUS from './en-US'

export const messages = {
  'zh-CN': zhCN,
  'en-US': enUS,
}

export type LocaleType = 'zh-CN' | 'en-US'

// Get initial locale from localStorage or default to zh-CN
const getInitialLocale = (): LocaleType => {
  const saved = localStorage.getItem('app-locale') as LocaleType
  if (saved && ['zh-CN', 'en-US'].includes(saved)) {
    return saved
  }
  return 'zh-CN'
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
