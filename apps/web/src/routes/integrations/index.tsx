import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { api, type DiagnoseCheck } from '../../lib/api'

export const Route = createFileRoute('/integrations/')({
  component: IntegrationsPage,
})

function CheckList({ items, showDetail = true }: { items: DiagnoseCheck[]; showDetail?: boolean }) {
  return (
    <ul className="list compact">
      {items.map((item) => (
        <li key={item.name}>
          {item.ok ? '✓' : '○'} {item.name}
          {showDetail ? <span className="meta"> {item.detail}</span> : null}
        </li>
      ))}
    </ul>
  )
}

function IntegrationsPage() {
  const { t } = useTranslation(['integrations', 'common'])
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const diagnose = useMutation({ mutationFn: api.diagnoseComfy })
  const report = diagnose.data
  const s = settings.data

  return (
    <section className="page" data-testid="integrations-page">
      <h1>{t('integrations:title')}</h1>
      <p className="lede">{t('integrations:lede')}</p>

      <div className="card-stack">
        <article className="panel-card" data-testid="integration-comfy">
          <h2>{t('integrations:comfy')}</h2>
          <p className="meta">{s?.comfy_url}</p>
          <p className="meta">{t('integrations:backend', { backend: s?.image_backend ? t(`integrations:backends.${s.image_backend}`) : '—' })}</p>
          <p className="meta">
            {!report && t('integrations:runDiagnose')}
            {report?.reachable && t('integrations:connected')}
            {report && !report.reachable && `○ ${report.detail}`}
          </p>
          <button
            type="button"
            className="btn primary"
            data-testid="comfy-diagnose"
            onClick={() => diagnose.mutate()}
            disabled={diagnose.isPending}
          >
            {t('integrations:diagnose')}
          </button>
          {report && (
            <>
              <h3>{t('integrations:models')}</h3>
              <CheckList items={report.models} />
              <h3>{t('integrations:nodes')}</h3>
              <CheckList items={report.nodes} showDetail={false} />
            </>
          )}
        </article>

        <article className="panel-card">
          <h2>{t('integrations:llm')}</h2>
          <p className="meta">
            {s?.llm_provider}
            {s?.llm_api_key_set ? t('integrations:keySet') : ''}
          </p>
        </article>

        <article className="panel-card">
          <h2>{t('integrations:eagle')}</h2>
          <p className="meta">
            {t('integrations:eagleUnavailable')}
          </p>
        </article>

        <article className="panel-card">
          <h2>{t('integrations:csp')}</h2>
          <p className="meta">
            {s?.csp_export_dir
              ? t('integrations:cspFolder', { path: s.csp_export_dir })
              : t('integrations:cspMissing')}
          </p>
        </article>

        <article className="panel-card">
          <h2>{t('integrations:capabilities')}</h2>
          <table className="table">
            <thead>
              <tr>
                <th>{t('integrations:capName')}</th>
                <th>{t('integrations:capModel')}</th>
                <th>{t('integrations:capConfigured')}</th>
                <th>{t('integrations:capRuntime')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(caps.data ?? {}).map(([name, c]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>
                    <code>{c.model_id}</code>
                  </td>
                  <td>{c.configured ? t('common:yes') : t('common:no')}</td>
                  <td>{c.runtime_available ? t('common:available') : t('common:offline')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </div>
    </section>
  )
}
