import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { ErrorBanner } from '../components/ErrorBanner'
import {
  api,
  type VisualLibraryItemDetail,
  type VisualLibraryItemSummary,
  type VisualLibraryKind,
  type VisualLibraryPreviewKind,
} from '../lib/api'

export const Route = createFileRoute('/visual-library')({
  component: VisualLibraryPage,
})

const KIND_FILTERS: Array<VisualLibraryKind | 'all'> = [
  'all',
  'outfit',
  'pose',
  'expression',
  'camera',
  'lighting',
  'background',
]

function kindLabelKey(kind: VisualLibraryKind | 'all'): string {
  switch (kind) {
    case 'all':
      return 'kindAll'
    case 'outfit':
      return 'kindOutfit'
    case 'pose':
      return 'kindPose'
    case 'expression':
      return 'kindExpression'
    case 'camera':
      return 'kindCamera'
    case 'lighting':
      return 'kindLighting'
    case 'background':
      return 'kindBackground'
    case 'other':
      return 'kindOther'
    default: {
      const _exhaustive: never = kind
      return _exhaustive
    }
  }
}

function previewProvenanceKey(kind: VisualLibraryPreviewKind | null | undefined): string | null {
  switch (kind) {
    case 'curated':
      return 'previewCurated'
    case 'generated':
      return 'previewGenerated'
    case 'imported_reference':
      return 'previewImported'
    case undefined:
    case null:
      return null
    default: {
      const _exhaustive: never = kind
      return _exhaustive
    }
  }
}

function displayLabel(item: VisualLibraryItemSummary): string {
  return item.label_ja?.trim() || item.label
}

function VisualLibraryPage() {
  const { t } = useTranslation('visualLibrary')
  const [q, setQ] = useState('')
  const [kind, setKind] = useState<VisualLibraryKind | 'all'>('all')
  const [selected, setSelected] = useState<{
    source_type: string
    source_id: string
  } | null>(null)
  const [promptOpen, setPromptOpen] = useState(false)

  const list = useQuery({
    queryKey: ['visual-library', kind, q],
    queryFn: () =>
      api.listVisualLibrary({
        q: q.trim() || undefined,
        kind: kind === 'all' ? undefined : kind,
        content_rating: 'general',
      }),
  })

  const detail = useQuery({
    queryKey: ['visual-library-item', selected?.source_type, selected?.source_id],
    queryFn: () => api.getVisualLibraryItem(selected!.source_type, selected!.source_id),
    enabled: Boolean(selected),
  })

  const items = list.data ?? []
  const filteredCount = items.length

  const openDetail = (item: VisualLibraryItemSummary) => {
    setPromptOpen(false)
    setSelected({ source_type: item.source_type, source_id: item.source_id })
  }

  const closeDetail = () => {
    setSelected(null)
    setPromptOpen(false)
  }

  if (selected) {
    return (
      <section className="page visual-library-page" data-testid="visual-library-page">
        <button type="button" className="btn ghost" onClick={closeDetail} data-testid="visual-library-back">
          {t('backToList')}
        </button>
        {detail.isError && <ErrorBanner message={t('loadError')} />}
        {detail.data && (
          <VisualLibraryDetail
            item={detail.data}
            promptOpen={promptOpen}
            onTogglePrompt={() => setPromptOpen((v) => !v)}
          />
        )}
      </section>
    )
  }

  return (
    <section className="page visual-library-page" data-testid="visual-library-page">
      <h1 data-testid="visual-library-title">{t('title')}</h1>
      <p className="lede">{t('lede')}</p>

      <label className="visual-library-search">
        <span className="visually-hidden">{t('searchPlaceholder')}</span>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('searchPlaceholder')}
          data-testid="visual-library-search"
        />
      </label>

      <div className="visual-library-filters" role="tablist" aria-label={t('title')} data-testid="visual-library-filters">
        {KIND_FILTERS.map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={kind === k}
            className={kind === k ? 'chip active' : 'chip'}
            data-testid={`visual-library-filter-${k}`}
            onClick={() => setKind(k)}
          >
            {t(kindLabelKey(k))}
          </button>
        ))}
      </div>

      <p className="meta" data-testid="visual-library-count">
        {t('count', { count: filteredCount })}
      </p>

      {list.isError && <ErrorBanner message={t('loadError')} />}

      {!list.isError && items.length === 0 && (
        <p className="meta" data-testid="visual-library-empty">
          {t('empty')}
        </p>
      )}

      <ul className="visual-library-grid" data-testid="visual-library-grid">
        {items.map((item) => (
          <li key={item.ref}>
            <button
              type="button"
              className="visual-library-card"
              data-testid="visual-library-card"
              data-ref={item.ref}
              data-kind={item.kind}
              data-has-preview={item.has_preview ? 'true' : 'false'}
              onClick={() => openDetail(item)}
            >
              <div className="visual-library-thumb">
                {item.thumbnail_asset_id ? (
                  <AssetImage assetId={item.thumbnail_asset_id} alt={displayLabel(item)} />
                ) : (
                  <div className="visual-library-placeholder" data-testid="visual-library-no-preview">
                    {t('noPreview')}
                  </div>
                )}
              </div>
              <div className="visual-library-card-body">
                <strong>{displayLabel(item)}</strong>
                <span className="meta">{t(kindLabelKey(item.kind))}</span>
                {item.tags.length > 0 && (
                  <span className="visual-library-tags" data-testid="visual-library-card-tags">
                    {item.tags.map((tag) => `#${tag}`).join(' ')}
                  </span>
                )}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

function VisualLibraryDetail({
  item,
  promptOpen,
  onTogglePrompt,
}: {
  item: VisualLibraryItemDetail
  promptOpen: boolean
  onTogglePrompt: () => void
}) {
  const { t } = useTranslation('visualLibrary')
  const provenanceKey = useMemo(() => previewProvenanceKey(item.preview_kind), [item.preview_kind])
  const label = displayLabel(item)

  return (
    <article className="visual-library-detail" data-testid="visual-library-detail" data-ref={item.ref}>
      <h1 data-testid="visual-library-detail-title">{label}</h1>

      <div className="visual-library-detail-preview">
        {item.thumbnail_asset_id ? (
          <AssetImage assetId={item.thumbnail_asset_id} alt={label} />
        ) : (
          <div className="visual-library-placeholder large" data-testid="visual-library-detail-no-preview">
            {t('noPreview')}
          </div>
        )}
        {provenanceKey && item.thumbnail_asset_id && (
          <p className="visual-library-provenance" data-testid="visual-library-provenance">
            {t(provenanceKey)}
          </p>
        )}
      </div>

      {item.description && (
        <section data-testid="visual-library-overview">
          <h2>{t('overview')}</h2>
          <p>{item.description}</p>
        </section>
      )}

      {item.tags.length > 0 && (
        <section data-testid="visual-library-detail-tags">
          <h2>{t('tags')}</h2>
          <p>{item.tags.join(' / ')}</p>
        </section>
      )}

      {item.model_scope.length > 0 && (
        <section data-testid="visual-library-models">
          <h2>{t('models')}</h2>
          <p>{item.model_scope.map((m) => (m === 'anima' ? 'Anima' : m)).join(', ')}</p>
        </section>
      )}

      {item.prompt_fragment && (
        <section data-testid="visual-library-prompt-section">
          <h2>{t('prompt')}</h2>
          <button
            type="button"
            className="btn ghost"
            data-testid="visual-library-prompt-toggle"
            aria-expanded={promptOpen}
            onClick={onTogglePrompt}
          >
            {promptOpen ? t('hidePrompt') : t('showPrompt')}
          </button>
          {promptOpen && (
            <pre className="visual-library-prompt" data-testid="visual-library-prompt">
              {item.prompt_fragment}
            </pre>
          )}
        </section>
      )}

      {item.source_type === 'marketplace_item' && (
        <div className="cta-row">
          <Link to="/wardrobe" className="btn" data-testid="visual-library-open-wardrobe">
            {t('openWardrobe')}
          </Link>
        </div>
      )}
    </article>
  )
}
