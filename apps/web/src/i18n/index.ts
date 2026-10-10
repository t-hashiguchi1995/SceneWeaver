import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import commonEn from './locales/en/common.json'
import characterEn from './locales/en/character.json'
import cspEn from './locales/en/csp.json'
import generationEn from './locales/en/generation.json'
import homeEn from './locales/en/home.json'
import integrationsEn from './locales/en/integrations.json'
import jobsEn from './locales/en/jobs.json'
import projectEn from './locales/en/project.json'
import promptEn from './locales/en/prompt.json'
import releaseEn from './locales/en/release.json'
import settingsEn from './locales/en/settings.json'
import storyEn from './locales/en/story.json'
import wardrobeEn from './locales/en/wardrobe.json'

import commonJa from './locales/ja/common.json'
import characterJa from './locales/ja/character.json'
import cspJa from './locales/ja/csp.json'
import generationJa from './locales/ja/generation.json'
import homeJa from './locales/ja/home.json'
import integrationsJa from './locales/ja/integrations.json'
import jobsJa from './locales/ja/jobs.json'
import projectJa from './locales/ja/project.json'
import promptJa from './locales/ja/prompt.json'
import releaseJa from './locales/ja/release.json'
import settingsJa from './locales/ja/settings.json'
import storyJa from './locales/ja/story.json'
import wardrobeJa from './locales/ja/wardrobe.json'

export const LOCALE_STORAGE_KEY = 'sceneweaver.locale'
export const SUPPORTED_LOCALES = ['ja', 'en'] as const
export type AppLocale = (typeof SUPPORTED_LOCALES)[number]

export const namespaces = [
  'common',
  'home',
  'project',
  'character',
  'story',
  'wardrobe',
  'generation',
  'prompt',
  'csp',
  'release',
  'settings',
  'integrations',
  'jobs',
] as const

const resources = {
  ja: {
    common: commonJa,
    home: homeJa,
    project: projectJa,
    character: characterJa,
    story: storyJa,
    wardrobe: wardrobeJa,
    generation: generationJa,
    prompt: promptJa,
    csp: cspJa,
    release: releaseJa,
    settings: settingsJa,
    integrations: integrationsJa,
    jobs: jobsJa,
  },
  en: {
    common: commonEn,
    home: homeEn,
    project: projectEn,
    character: characterEn,
    story: storyEn,
    wardrobe: wardrobeEn,
    generation: generationEn,
    prompt: promptEn,
    csp: cspEn,
    release: releaseEn,
    settings: settingsEn,
    integrations: integrationsEn,
    jobs: jobsEn,
  },
} as const

export function readStoredLocale(): AppLocale {
  try {
    const raw = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (raw === 'en' || raw === 'ja') return raw
  } catch {
    /* ignore */
  }
  return 'ja'
}

export function persistLocale(locale: AppLocale): void {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    /* ignore */
  }
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }
}

void i18n.use(initReactI18next).init({
  resources,
  lng: typeof window !== 'undefined' ? readStoredLocale() : 'ja',
  fallbackLng: 'en',
  defaultNS: 'common',
  ns: [...namespaces],
  interpolation: { escapeValue: false },
  returnNull: false,
})

if (typeof document !== 'undefined') {
  document.documentElement.lang = i18n.language.startsWith('en') ? 'en' : 'ja'
}

i18n.on('languageChanged', (lng) => {
  persistLocale(lng.startsWith('en') ? 'en' : 'ja')
})

export default i18n
