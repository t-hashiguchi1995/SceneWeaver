import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../lib/api'
import {
  POSE_CATEGORY_FILTERS,
  filterPoseSummaries,
  type PoseCategoryFilter,
} from '../pose/catalog'
import { loadFavoritePoseIds, loadRecentPoseIds, toggleFavoritePose } from '../pose/storage'
import {
  summaryToCard,
  type PoseDetail,
  type PoseSummary,
  type SelectedPose,
} from '../pose/types'

export type PoseGalleryProps = {
  open: boolean
  onClose: () => void
  onApply: (selected: SelectedPose) => void
  initialSelectedId?: string
}

export function PoseGallery(props: PoseGalleryProps) {
  const { t } = useTranslation('generation')
  const [items, setItems] = useState<PoseSummary[]>([])
  const [loadError, setLoadError] = useState('')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<PoseCategoryFilter>('all')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [favoriteIds, setFavoriteIds] = useState(() => loadFavoritePoseIds())
  const [recentIds] = useState(() => loadRecentPoseIds())
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [detail, setDetail] = useState<PoseDetail | null>(null)
  const [angle, setAngle] = useState('front')
  const [strength, setStrength] = useState(1)
  const [flip, setFlip] = useState(false)

  useEffect(() => {
    if (!props.open) return
    let cancelled = false
    setLoadError('')
    api
      .listReferencePoses()
      .then((rows) => {
        if (!cancelled) setItems(rows)
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message || 'failed to load poses')
      })
    return () => {
      cancelled = true
    }
  }, [props.open])

  const filtered = useMemo(
    () =>
      filterPoseSummaries(items, {
        query,
        category,
        favoritesOnly,
        favoriteIds,
      }),
    [items, query, category, favoritesOnly, favoriteIds],
  )

  const recentCards = useMemo(
    () => recentIds.map((id) => items.find((c) => c.id === id)).filter(Boolean) as PoseSummary[],
    [recentIds, items],
  )

  const openPreview = async (summary: PoseSummary) => {
    setPreviewId(summary.id)
    setStrength(1)
    setFlip(false)
    setAngle(summary.default_view || summary.available_views[0] || 'front')
    try {
      const d = await api.getReferencePose(summary.id)
      setDetail(d)
      setAngle(d.default_view || d.available_views[0] || 'front')
    } catch (err) {
      setDetail(null)
      setLoadError((err as Error).message)
    }
  }

  const apply = (summary: PoseSummary, view: string, nextStrength = strength, nextFlip = flip) => {
    const card = summaryToCard(summary, detail?.id === summary.id ? detail : null)
    const viewDetail = detail?.views?.[view]
    if (viewDetail?.prompt) {
      card.posePrompt = viewDetail.prompt
      card.referenceUri = viewDetail.references?.line?.url
      card.thumbUrl = viewDetail.references?.line?.url || card.thumbUrl
    }
    props.onApply({
      poseId: summary.id,
      poseView: view,
      strength: nextStrength,
      flipHorizontal: nextFlip,
      appliedAt: new Date().toISOString(),
      card,
    })
    props.onClose()
  }

  const copyPrompt = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      /* ignore */
    }
  }

  if (!props.open) return null

  const previewSummary = previewId ? items.find((i) => i.id === previewId) : null
  const previewView = detail?.views?.[angle]
  const previewUrl =
    previewView?.references?.line?.url || previewSummary?.thumbnail_url || ''

  return (
    <div className="pose-gallery-overlay" data-testid="pose-gallery" role="dialog" aria-modal="true">
      <div className="pose-gallery-shell">
        <header className="pose-gallery-header">
          <div>
            <h2>{t('poseGallery.title')}</h2>
            <p className="meta">{t('poseGallery.subtitle')}</p>
          </div>
          <div className="cta-row">
            <input
              data-testid="pose-gallery-search"
              placeholder={t('poseGallery.search')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              type="button"
              className={favoritesOnly ? 'btn primary' : 'btn'}
              data-testid="pose-gallery-favorites"
              onClick={() => setFavoritesOnly((v) => !v)}
            >
              ♡ {t('poseGallery.favorites')}
            </button>
            <button
              type="button"
              className="btn"
              data-testid="pose-gallery-random"
              onClick={() => {
                const pool = filtered.length ? filtered : items
                const card = pool[Math.floor(Math.random() * pool.length)]
                if (card) void openPreview(card)
              }}
            >
              {t('poseGallery.random')}
            </button>
            <button type="button" className="btn" data-testid="pose-gallery-close" onClick={props.onClose}>
              ×
            </button>
          </div>
        </header>

        {loadError ? <p className="error">{loadError}</p> : null}

        <div className="cta-row pose-gallery-cats">
          {POSE_CATEGORY_FILTERS.map((cat) => (
            <button
              key={cat}
              type="button"
              className={category === cat ? 'btn primary' : 'btn'}
              data-testid={`pose-cat-${cat}`}
              onClick={() => setCategory(cat)}
            >
              {t(`poseGallery.cat.${cat}`)}
            </button>
          ))}
        </div>

        {recentCards.length > 0 && !favoritesOnly && !query && category === 'all' && (
          <section className="pose-gallery-recent">
            <h3>{t('poseGallery.recent')}</h3>
            <div className="pose-gallery-grid pose-gallery-grid-compact">
              {recentCards.slice(0, 4).map((card) => (
                <button
                  key={`recent-${card.id}`}
                  type="button"
                  className="pose-card"
                  onClick={() => void openPreview(card)}
                >
                  {card.thumbnail_url ? <img src={card.thumbnail_url} alt="" /> : null}
                  <span>{card.label}</span>
                </button>
              ))}
            </div>
          </section>
        )}

        <div className="pose-gallery-body">
          <div className="pose-gallery-grid" data-testid="pose-gallery-grid">
            {filtered.map((card) => {
              const fav = favoriteIds.has(card.id)
              return (
                <article key={card.id} className="pose-card" data-testid={`pose-card-${card.id}`}>
                  <button type="button" className="pose-card-thumb" onClick={() => void openPreview(card)}>
                    {card.thumbnail_url ? <img src={card.thumbnail_url} alt="" /> : <span>{card.id}</span>}
                  </button>
                  <div className="pose-card-footer">
                    <strong>{card.label}</strong>
                    <div className="cta-row">
                      <button
                        type="button"
                        className={fav ? 'btn primary' : 'btn'}
                        data-testid={`pose-fav-${card.id}`}
                        aria-label={t('poseGallery.favorite')}
                        onClick={() => setFavoriteIds(toggleFavoritePose(card.id))}
                      >
                        ♡
                      </button>
                      <button
                        type="button"
                        className="btn primary"
                        data-testid={`pose-apply-${card.id}`}
                        onClick={() => apply(card, card.default_view || 'front', 1, false)}
                      >
                        {t('poseGallery.apply')}
                      </button>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>

          {previewSummary && (
            <aside className="pose-gallery-drawer" data-testid="pose-gallery-drawer">
              <div className="row-between">
                <h3>{t('poseGallery.preview')}</h3>
                <button type="button" className="btn" onClick={() => setPreviewId(null)}>
                  ×
                </button>
              </div>
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt=""
                  className="pose-drawer-image"
                  style={{ transform: flip ? 'scaleX(-1)' : undefined }}
                />
              ) : null}
              <strong>{previewSummary.label}</strong>
              <p className="meta">{previewSummary.tags.join(' / ')}</p>
              <label>
                Angle
                <select
                  data-testid="pose-angle-select"
                  value={angle}
                  onChange={(e) => setAngle(e.target.value)}
                >
                  {(detail?.available_views || previewSummary.available_views).map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('poseGallery.posePrompt')}
                <textarea
                  readOnly
                  rows={4}
                  value={previewView?.prompt || ''}
                  data-testid="pose-drawer-prompt"
                />
              </label>
              <button
                type="button"
                className="btn"
                data-testid="pose-copy-prompt"
                onClick={() => copyPrompt(previewView?.prompt || '')}
              >
                {t('poseGallery.copyPrompt')}
              </button>
              <label>
                {t('poseGallery.strength')}: {strength.toFixed(2)}
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={0.05}
                  value={strength}
                  data-testid="pose-strength"
                  onChange={(e) => setStrength(Number(e.target.value))}
                />
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={flip}
                  data-testid="pose-flip"
                  onChange={(e) => setFlip(e.target.checked)}
                />
                {t('poseGallery.flip')}
              </label>
              <div className="cta-row">
                <button
                  type="button"
                  className={favoriteIds.has(previewSummary.id) ? 'btn primary' : 'btn'}
                  onClick={() => setFavoriteIds(toggleFavoritePose(previewSummary.id))}
                >
                  ♡ {t('poseGallery.favorite')}
                </button>
                <button
                  type="button"
                  className="btn primary"
                  data-testid="pose-drawer-apply"
                  onClick={() => apply(previewSummary, angle)}
                >
                  {t('poseGallery.applyToShot')}
                </button>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}
