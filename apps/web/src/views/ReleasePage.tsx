import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ProjectContextBar } from '../components/ProjectContextBar'
import { api } from '../lib/api'

type Platform = 'x' | 'pixiv' | 'patreon'

export function ReleasePage() {
  const { t } = useTranslation('release')
  const { projectId } = useParams({ strict: false })
  const project = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: Boolean(projectId),
  })
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [platform, setPlatform] = useState<Platform>('x')
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const mutate = useMutation({
    mutationFn: () => api.releasePreview(title || project.data?.title || '', summary),
    onSuccess: (data) => setPreview(data as unknown as Record<string, unknown>),
  })
  const editions = (preview?.editions ?? null) as Record<string, Record<string, unknown>> | null

  return (
    <section className="page release-page" data-testid="release-page">
      {projectId && <ProjectContextBar />}
      <h1>{t('title')}</h1>
      <p className="lede">{t('lede')}</p>

      <form
        className="release-form panel-card stack"
        data-testid="release-master-form"
        onSubmit={(e) => {
          e.preventDefault()
          mutate.mutate()
        }}
      >
        <h2>{t('masterSection')}</h2>
        <label>
          {t('masterTitle')}
          <input
            data-testid="release-title"
            value={title || project.data?.title || ''}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          {t('masterSummary')}
          <textarea
            data-testid="release-summary"
            rows={6}
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />
        </label>
        <div className="cta-row">
          <button type="submit" className="btn primary" data-testid="release-preview-button">
            {t('build')}
          </button>
        </div>
      </form>

      {editions && (
        <section className="release-previews panel-card" data-testid="release-editions">
          <h2>{t('platformSection')}</h2>
          <div className="cta-row release-tabs" role="tablist">
            {(['x', 'pixiv', 'patreon'] as const).map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={platform === key}
                className={platform === key ? 'btn primary' : 'btn'}
                data-testid={`release-tab-${key}`}
                onClick={() => setPlatform(key)}
              >
                {t(
                  key === 'x'
                    ? 'editionX'
                    : key === 'pixiv'
                      ? 'editionPixiv'
                      : 'editionPatreon',
                )}
              </button>
            ))}
          </div>

          {platform === 'x' && (
            <article data-testid="release-edition-x" className="release-edition">
              <h3>{t('editionX')}</h3>
              <p>{String(editions.x.text)}</p>
              <p className="meta">{((editions.x as { hashtags: string[] }).hashtags).join(' ')}</p>
            </article>
          )}
          {platform === 'pixiv' && (
            <article data-testid="release-edition-pixiv" className="release-edition">
              <h3>{String(editions.pixiv.title)}</h3>
              <p>{String(editions.pixiv.description)}</p>
              <p className="meta">{t('aiDisclosure')}</p>
            </article>
          )}
          {platform === 'patreon' && (
            <article data-testid="release-edition-patreon" className="release-edition">
              <h3>{String(editions.patreon.title)}</h3>
              <p>{String(editions.patreon.body_markdown)}</p>
            </article>
          )}
        </section>
      )}

      {mutate.error && <p role="alert">{mutate.error.message}</p>}
      <p className="meta">{t('previewOnly')}</p>
    </section>
  )
}
