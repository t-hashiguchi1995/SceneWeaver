import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import { api } from '../../lib/api'

export const Route = createFileRoute('/capabilities/')({
  component: CapabilitiesPage,
})

function CapabilitiesPage() {
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })

  return (
    <section className="page">
      <h1>Capabilities</h1>
      <p className="lede">Approved model registry only — arbitrary checkpoints are never selectable.</p>
      {caps.isLoading && <p>Loading…</p>}
      <table className="table">
        <thead>
          <tr>
            <th>Capability</th>
            <th>Model</th>
            <th>Configured</th>
            <th>Runtime</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(caps.data ?? {}).map(([name, c]) => (
            <tr key={name}>
              <td>{name}</td>
              <td>
                <code>{c.model_id}</code>
              </td>
              <td>{c.configured ? 'yes' : 'no'}</td>
              <td>{c.runtime_available ? 'available' : 'offline'}</td>
              <td>{c.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}