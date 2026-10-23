import { useParams, useSearch } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { useProjectContextQuery } from '../hooks/useProjectContextQuery'
import { loadStudioContext, type ProjectContext } from '../lib/api'

export type ProjectContextBarProps = {
  sceneId?: string
  beatId?: string
  shotId?: string
  /** When true, skip studio-context fallback (page already owns resolution). */
  strict?: boolean
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return `${text.slice(0, max - 1)}…`
}

export function ProjectContextBarView({
  context,
  isLoading,
}: {
  context?: ProjectContext
  isLoading?: boolean
}) {
  const { t } = useTranslation('context')
  if (isLoading && !context) {
    return (
      <div className="project-context-bar" data-testid="project-context-bar" aria-busy="true">
        <p className="meta">{t('loading')}</p>
      </div>
    )
  }
  if (!context?.project) return null

  return (
    <div className="project-context-bar" data-testid="project-context-bar">
      <nav className="project-context-bar__crumb" aria-label={t('breadcrumbLabel')}>
        <ol>
          <li>
            <span data-testid="context-project">{context.project.title}</span>
          </li>
          {context.scene && (
            <li className="project-context-bar__crumb-scene">
              <span data-testid="context-scene">{context.scene.title}</span>
            </li>
          )}
          {context.beat && (
            <li className="project-context-bar__crumb-beat">
              <span data-testid="context-beat">{context.beat.title}</span>
            </li>
          )}
          {context.shot && (
            <li>
              <span data-testid="context-shot">{context.shot.label}</span>
            </li>
          )}
        </ol>
      </nav>

      <div className="project-context-bar__mobile-primary" data-testid="context-mobile-primary">
        <strong data-testid="context-project-mobile">{context.project.title}</strong>
        <p className="meta">
          {[context.scene?.title, context.shot?.label].filter(Boolean).join(' › ')}
        </p>
      </div>

      {(context.character || context.outfit) && (
        <div className="project-context-bar__chips" data-testid="context-chips">
          {context.character && (
            <span className="project-context-chip" data-testid="context-character">
              {context.character.display_name}
            </span>
          )}
          {context.outfit && (
            <span className="project-context-chip" data-testid="context-outfit">
              {context.outfit.label}
            </span>
          )}
        </div>
      )}

      {context.script_excerpt && (
        <p className="project-context-bar__script" data-testid="context-script">
          <span className="project-context-bar__script-full">「{context.script_excerpt}」</span>
          <span className="project-context-bar__script-short">
            「{truncate(context.script_excerpt, 24)}」
          </span>
        </p>
      )}
    </div>
  )
}

/** Resolves route/search/studio IDs and renders the production context bar. */
export function ProjectContextBar(props: ProjectContextBarProps = {}) {
  const { projectId } = useParams({ strict: false })
  const search = useSearch({ strict: false }) as {
    sceneId?: string
    beatId?: string
  }
  const studio = props.strict ? {} : loadStudioContext()
  const ids = {
    projectId,
    sceneId: props.sceneId ?? search.sceneId ?? studio.sceneId,
    beatId: props.beatId ?? search.beatId ?? studio.beatId,
    shotId: props.shotId ?? studio.shotId,
  }
  const query = useProjectContextQuery(ids)
  if (!projectId) return null
  return <ProjectContextBarView context={query.data} isLoading={query.isLoading} />
}
