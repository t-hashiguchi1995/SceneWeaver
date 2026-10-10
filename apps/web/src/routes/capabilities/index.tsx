import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { api } from '../../lib/api'

export const Route = createFileRoute('/capabilities/')({
  component: CapabilitiesPage,
})

function CapabilitiesPage() {
  const { t } = useTranslation(['integrations', 'common'])
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })

  return (
    <section className="page">
      <h1>{t('integrations:capTitle')}</h1>
      <p className="lede">{t('integrations:capLede')}</p>
      {caps.isLoading && <p>{t('common:loading')}</p>}
      <table className="table">
        <thead>
          <tr>
            <th>{t('integrations:capName')}</th>
            <th>{t('integrations:capModel')}</th>
            <th>{t('integrations:capConfigured')}</th>
            <th>{t('integrations:capRuntime')}</th>
            <th>{t('integrations:capDetail')}</th>
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
              <td>{c.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
