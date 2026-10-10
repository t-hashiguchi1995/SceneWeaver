import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { type AppLocale, persistLocale } from '../../i18n'
import { api } from '../../lib/api'

export const Route = createFileRoute('/settings/')({
  component: SettingsPage,
})

type SettingsForm = {
  workspace_label: string
  comfy_url: string
  image_backend: string
  llm_provider: string
  llm_base_url: string
  llm_model: string
  llm_api_key: string
  eagle_enabled: boolean
  eagle_base_url: string
  csp_export_dir: string
}

const EMPTY_FORM: SettingsForm = {
  workspace_label: '',
  comfy_url: '',
  image_backend: 'fake',
  llm_provider: 'stub',
  llm_base_url: '',
  llm_model: '',
  llm_api_key: '',
  eagle_enabled: false,
  eagle_base_url: '',
  csp_export_dir: '',
}

function SettingsPage() {
  const { t, i18n } = useTranslation(['settings', 'common'])
  const qc = useQueryClient()
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [form, setForm] = useState<SettingsForm>(EMPTY_FORM)
  const locale: AppLocale = i18n.language.startsWith('en') ? 'en' : 'ja'

  useEffect(() => {
    const data = settings.data
    if (!data) return
    setForm((prev) => ({
      ...prev,
      workspace_label: data.workspace_label,
      comfy_url: data.comfy_url,
      image_backend: data.image_backend,
      llm_provider: data.llm_provider,
      llm_base_url: data.llm_base_url,
      llm_model: data.llm_model,
      eagle_enabled: data.eagle_enabled,
      eagle_base_url: data.eagle_base_url,
      csp_export_dir: data.csp_export_dir,
    }))
  }, [settings.data])

  function setField<K extends keyof SettingsForm>(key: K, value: SettingsForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const save = useMutation({
    mutationFn: () =>
      api.updateSettings({
        ...form,
        llm_api_key: form.llm_api_key || undefined,
      }),
    onSuccess: async () => {
      setForm((prev) => ({ ...prev, llm_api_key: '' }))
      await qc.invalidateQueries({ queryKey: ['settings'] })
      await qc.invalidateQueries({ queryKey: ['setup-status'] })
    },
  })

  async function changeLocale(next: AppLocale) {
    persistLocale(next)
    await i18n.changeLanguage(next)
  }

  return (
    <section className="page" data-testid="settings-page">
      <h1>{t('settings:title')}</h1>
      <p className="lede">
        {t('settings:lede', { backend: settings.data?.secrets_backend ?? '—' })}
      </p>

      <fieldset className="stack-form" data-testid="settings-language">
        <legend>{t('settings:language')}</legend>
        <label className="checkbox">
          <input
            type="radio"
            name="locale"
            checked={locale === 'ja'}
            onChange={() => void changeLocale('ja')}
            data-testid="locale-ja"
          />
          {t('settings:languageJa')}
        </label>
        <label className="checkbox">
          <input
            type="radio"
            name="locale"
            checked={locale === 'en'}
            onChange={() => void changeLocale('en')}
            data-testid="locale-en"
          />
          {t('settings:languageEn')}
        </label>
      </fieldset>

      <form
        className="stack-form"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        <label>
          {t('settings:workspaceLabel')}
          <input
            value={form.workspace_label}
            onChange={(e) => setField('workspace_label', e.target.value)}
          />
        </label>
        <label>
          {t('settings:comfyUrl')}
          <input
            data-testid="settings-comfy-url"
            value={form.comfy_url}
            onChange={(e) => setField('comfy_url', e.target.value)}
          />
        </label>
        <label>
          {t('settings:imageBackend')}
          <select
            value={form.image_backend}
            onChange={(e) => setField('image_backend', e.target.value)}
          >
            <option value="fake">fake</option>
            <option value="comfy">comfy</option>
            <option value="comfy_dry">comfy_dry</option>
          </select>
        </label>
        <label>
          {t('settings:llmProvider')}
          <select
            value={form.llm_provider}
            onChange={(e) => setField('llm_provider', e.target.value)}
          >
            <option value="stub">stub</option>
            <option value="openai_compatible">openai_compatible</option>
          </select>
        </label>
        <label>
          {t('settings:llmBaseUrl')}
          <input
            value={form.llm_base_url}
            onChange={(e) => setField('llm_base_url', e.target.value)}
          />
        </label>
        <label>
          {t('settings:llmModel')}
          <input value={form.llm_model} onChange={(e) => setField('llm_model', e.target.value)} />
        </label>
        <label>
          {t('settings:llmApiKey')}{' '}
          {settings.data?.llm_api_key_set ? t('settings:llmApiKeySet') : ''}
          <input
            type="password"
            data-testid="settings-llm-key"
            value={form.llm_api_key}
            onChange={(e) => setField('llm_api_key', e.target.value)}
            placeholder={t('settings:llmApiKeyPlaceholder')}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={form.eagle_enabled}
            onChange={(e) => setField('eagle_enabled', e.target.checked)}
          />
          {t('settings:eagleEnabled')}
        </label>
        <label>
          {t('settings:eagleBaseUrl')}
          <input
            value={form.eagle_base_url}
            onChange={(e) => setField('eagle_base_url', e.target.value)}
          />
        </label>
        <label>
          {t('settings:cspExportDir')}
          <input
            value={form.csp_export_dir}
            onChange={(e) => setField('csp_export_dir', e.target.value)}
          />
        </label>
        <button
          type="submit"
          className="btn primary"
          data-testid="settings-save"
          disabled={save.isPending}
        >
          {t('common:actions.save')}
        </button>
      </form>
    </section>
  )
}
