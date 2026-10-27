import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  POSE_CATALOG,
  POSE_CATEGORY_FILTERS,
  filterPoseCatalog,
  type PoseCategoryFilter,
} from '../pose/catalog'
import { loadFavoritePoseIds, loadRecentPoseIds, toggleFavoritePose } from '../pose/storage'
import type { PoseCard, SelectedPose } from '../pose/types'

export type PoseGalleryProps = {
  open: boolean
  onClose: () => void
  onApply: (selected: SelectedPose) => void
  initialSelectedId?: string
}

export function PoseGallery(props: PoseGalleryProps) {
  const { t } = useTranslation('generation')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<PoseCategoryFilter>('all')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [favoriteIds, setFavoriteIds] = useState(() => loadFavoritePoseIds())
  const [recentIds] = useState(() => loadRecentPoseIds())
  const [preview, setPreview] = useState<PoseCard | null>(null)
  const [strength, setStrength] = useState(1)
  const [flip, setFlip] = useState(false)

  const filtered = useMemo(
    () =>
      filterPoseCatalog(POSE_CATALOG, {
        query,
        category,
        favoritesOnly,
        favoriteIds,
      }),
    [query, category, favoritesOnly, favoriteIds],
  )

  const recentCards = useMemo(
    () => recentIds.map((id) => POSE_CATALOG.find((c) => c.id === id)).filter(Boolean) as PoseCard[],
    [recentIds],
  )

  if (!props.open) return null

  const openPreview = (card: PoseCard) => {
    setPreview(card)
    setStrength(card.defaultStrength)
    setFlip(false)
  }

  const apply = (card: PoseCard, nextStrength = strength, nextFlip = flip) => {
    props.onApply({
      card,
      strength: nextStrength,
      flipHorizontal: nextFlip,
      appliedAt: new Date().toISOString(),
    })
    props.onClose()
  }

  const copyPrompt = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // clipboard may be unavailable in some test envs
    }
  }

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
                const pool = filtered.length ? filtered : POSE_CATALOG
                const card = pool[Math.floor(Math.random() * pool.length)]
                if (card) openPreview(card)
              }}
            >
              {t('poseGallery.random')}
            </button>
            <button type="button" className="btn" data-testid="pose-gallery-close" onClick={props.onClose}>
              ×
            </button>
          </div>
        </header>

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
                  onClick={() => openPreview(card)}
                >
                  <img src={card.thumbUrl} alt="" />
                  <span>{card.title}</span>
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
                  <button type="button" className="pose-card-thumb" onClick={() => openPreview(card)}>
                    <img src={card.thumbUrl} alt="" />
                  </button>
                  <div className="pose-card-footer">
                    <strong>{card.title}</strong>
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
                        onClick={() => apply(card, card.defaultStrength, false)}
                      >
                        {t('poseGallery.apply')}
                      </button>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>

          {preview && (
            <aside className="pose-gallery-drawer" data-testid="pose-gallery-drawer">
              <div className="row-between">
                <h3>{t('poseGallery.preview')}</h3>
                <button type="button" className="btn" onClick={() => setPreview(null)}>
                  ×
                </button>
              </div>
              <img
                src={preview.thumbUrl}
                alt=""
                className="pose-drawer-image"
                style={{ transform: flip ? 'scaleX(-1)' : undefined }}
              />
              <strong>{preview.title}</strong>
              <p className="meta">{preview.subtitle}</p>
              <p className="meta">{preview.tags.join(' / ')}</p>
              <label>
                {t('poseGallery.posePrompt')}
                <textarea readOnly rows={4} value={preview.posePrompt} data-testid="pose-drawer-prompt" />
              </label>
              <button type="button" className="btn" data-testid="pose-copy-prompt" onClick={() => copyPrompt(preview.posePrompt)}>
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
                  className={favoriteIds.has(preview.id) ? 'btn primary' : 'btn'}
                  onClick={() => setFavoriteIds(toggleFavoritePose(preview.id))}
                >
                  ♡ {t('poseGallery.favorite')}
                </button>
                <button
                  type="button"
                  className="btn primary"
                  data-testid="pose-drawer-apply"
                  onClick={() => apply(preview)}
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
