import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../../lib/api'

export const Route = createFileRoute('/setup/')({
  component: SetupWizardPage,
})

function SetupWizardPage() {
  const { t } = useTranslation('settings')
  const nav = useNavigate()
  const qc = useQueryClient()
  const status = useQuery({ queryKey: ['setup-status'], queryFn: api.setupStatus })
  const [comfyUrl, setComfyUrl] = useState('')
  const [llmProvider, setLlmProvider] = useState('stub')
  const [apiKey, setApiKey] = useState('')
  const [cspDir, setCspDir] = useState('')

  const save = useMutation({
    mutationFn: async () => {
      await api.updateSettings({
        comfy_url: comfyUrl || status.data?.comfy.url,
        llm_provider: llmProvider,
        llm_api_key: apiKey || undefined,
        csp_export_dir: cspDir,
        image_backend: comfyUrl || status.data?.comfy.url ? 'comfy' : 'fake',
      })
      return api.setupStatus()
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['setup-status'] })
      await qc.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  const finish = useMutation({
    mutationFn: async () => {
      await save.mutateAsync()
      return api.completeSetup()
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['setup-status'] })
      await nav({ to: '/' })
    },
  })

  const data = status.data
  const models = data?.models ?? []
  const modelsOk = models.filter((m) => m.ok).length
  const modelsTotal = models.length

  return (
    <section className="page" data-testid="setup-page">
      <p className="eyebrow">{t('setup.eyebrow')}</p>
      <h1>{t('setup.title')}</h1>
      <p className="lede">{t('setup.lede')}</p>

      <ol className="setup-steps">
        <li>
          <h2>{t('setup.workspace')}</h2>
          <p className="meta">{data?.workspace_label || '…'}</p>
          <p className="meta">
            {t('setup.secretsBackend', { backend: data?.secrets_backend ?? '—' })}
          </p>
        </li>
        <li>
          <h2>{t('setup.comfy')}</h2>
          <input
            data-testid="setup-comfy-url"
            aria-label="ComfyUI URL"
            value={comfyUrl || data?.comfy.url || ''}
            onChange={(e) => setComfyUrl(e.target.value)}
            placeholder="http://127.0.0.1:8188"
          />
          <p className="meta">
            {data?.comfy.reachable
              ? t('setup.connected')
              : `○ ${data?.comfy.detail || t('setup.checking')}`}
            {modelsTotal > 0
              ? t('setup.modelsSummary', { ok: modelsOk, total: modelsTotal })
              : ''}
          </p>
          <button
            type="button"
            className="btn"
            data-testid="setup-diagnose"
            onClick={() => save.mutate()}
            disabled={save.isPending}
          >
            {t('setup.saveDiagnose')}
          </button>
        </li>
        <li>
          <h2>{t('setup.requiredModels')}</h2>
          <ul className="list compact">
            {models.map((m) => (
              <li key={m.name}>
                {m.ok ? '✓' : '○'} {m.name} <span className="meta">{m.detail}</span>
              </li>
            ))}
          </ul>
        </li>
        <li>
          <h2>{t('setup.llm')}</h2>
          <select
            data-testid="setup-llm-provider"
            aria-label="LLM provider"
            value={llmProvider}
            onChange={(e) => setLlmProvider(e.target.value)}
          >
            <option value="stub">{t('setup.llmStub')}</option>
            <option value="openai_compatible">{t('setup.llmOpenAi')}</option>
          </select>
          {llmProvider === 'openai_compatible' && (
            <input
              data-testid="setup-llm-key"
              aria-label="LLM API key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={data?.llm.api_key_set ? t('setup.apiKeyKeep') : t('setup.apiKey')}
            />
          )}
        </li>
        <li>
          <h2>{t('setup.eagle')}</h2>
          <p className="meta">{t('setup.eagleLater')}</p>
        </li>
        <li>
          <h2>{t('setup.cspDir')}</h2>
          <input
            data-testid="setup-csp-dir"
            aria-label="CSP export directory"
            value={cspDir || data?.csp_export_dir || ''}
            onChange={(e) => setCspDir(e.target.value)}
            placeholder={t('setup.cspPlaceholder')}
          />
        </li>
      </ol>

      <div className="cta-row">
        <button
          type="button"
          className="btn primary"
          data-testid="setup-finish"
          onClick={() => finish.mutate()}
          disabled={finish.isPending}
        >
          {t('setup.finish')}
        </button>
        <Link to="/" className="btn">
          {t('setup.skip')}
        </Link>
      </div>
    </section>
  )
}
