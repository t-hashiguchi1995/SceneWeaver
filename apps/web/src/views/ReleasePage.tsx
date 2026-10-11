import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../lib/api'


export function ReleasePage() {
  const { t } = useTranslation('release')
  const { projectId } = useParams({ strict: false })
  const project = useQuery({ queryKey: ['projects', projectId], queryFn: () => api.getProject(projectId!), enabled: Boolean(projectId) })
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const mutate = useMutation({
    mutationFn: () => api.releasePreview(title || project.data?.title || '', summary),
    onSuccess: (data) => setPreview(data as unknown as Record<string, unknown>),
  })
  const editions = (preview?.editions ?? null) as Record<string, unknown> | null

  return (
    <section className="page" data-testid="release-page">
      <h1>{t('title')}</h1>
      <label>{t("masterTitle")}<input value={title || project.data?.title || ""} onChange={(e) => setTitle(e.target.value)} /></label>
      <label>{t("masterSummary")}<textarea value={summary} onChange={(e) => setSummary(e.target.value)} /></label>
      <button
        type="button"
        className="btn primary"
        data-testid="release-preview-button"
        onClick={() => mutate.mutate()}
      >
        {t('build')}
      </button>
      {editions && (
        <div data-testid="release-editions">
          <article data-testid="release-edition-x">
            <h2>{t('editionX')}</h2>
            <p>{String((editions.x as Record<string, unknown>).text)}</p><p>{((editions.x as { hashtags: string[] }).hashtags).join(" ")}</p>
          </article>
          <article data-testid="release-edition-pixiv">
            <h2>{t('editionPixiv')}</h2>
            <h3>{String((editions.pixiv as Record<string, unknown>).title)}</h3><p>{String((editions.pixiv as Record<string, unknown>).description)}</p><p>{t("aiDisclosure")}</p>
          </article>
          <article data-testid="release-edition-patreon">
            <h2>{t('editionPatreon')}</h2>
            <h3>{String((editions.patreon as Record<string, unknown>).title)}</h3><p>{String((editions.patreon as Record<string, unknown>).body_markdown)}</p>
          </article>
        </div>
      )}
      {mutate.error && <p role="alert">{mutate.error.message}</p>}
      <p className="meta">{t('previewOnly')}</p>
    </section>
  )
}
