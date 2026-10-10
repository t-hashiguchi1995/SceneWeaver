import { useMutation } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { api } from '../../lib/api'

export const Route = createFileRoute('/release/')({
  component: ReleasePage,
})

function ReleasePage() {
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const mutate = useMutation({
    mutationFn: () => api.releasePreview('SceneWeaver Preview', 'A local MVP release teaser'),
    onSuccess: (data) => setPreview(data as unknown as Record<string, unknown>),
  })
  const editions = (preview?.editions ?? null) as Record<string, unknown> | null

  return (
    <section className="page" data-testid="release-page">
      <h1>Release Preview</h1>
      <button
        type="button"
        className="btn primary"
        data-testid="release-preview-button"
        onClick={() => mutate.mutate()}
      >
        Build edition preview
      </button>
      {editions && (
        <div data-testid="release-editions">
          <article data-testid="release-edition-x">
            <h2>X Preview</h2>
            <pre>{JSON.stringify(editions.x, null, 2)}</pre>
          </article>
          <article data-testid="release-edition-pixiv">
            <h2>pixiv Preview</h2>
            <pre>{JSON.stringify(editions.pixiv, null, 2)}</pre>
          </article>
          <article data-testid="release-edition-patreon">
            <h2>Patreon Preview</h2>
            <pre>{JSON.stringify(editions.patreon, null, 2)}</pre>
          </article>
        </div>
      )}
      {preview && (
        <pre className="lede" data-testid="release-preview-json">
          {JSON.stringify(preview, null, 2)}
        </pre>
      )}
    </section>
  )
}
