import type { PoseSummary } from './types'

/** Category chips for Gallery UI (not Shisei/ai-pose-gallery taxonomy). */
export type PoseCategoryFilter =
  | 'all'
  | 'standing'
  | 'sitting'
  | 'action'
  | 'walking'
  | 'fighting'
  | 'hands'
  | 'cute'
  | 'dynamic'

export const POSE_CATEGORY_FILTERS: PoseCategoryFilter[] = [
  'all',
  'standing',
  'sitting',
  'action',
  'hands',
  'dynamic',
]

/** @deprecated Static catalog removed — use GET /api/v1/references/poses */
export const POSE_CATALOG: PoseSummary[] = []

export function filterPoseSummaries(
  items: PoseSummary[],
  opts: {
    query: string
    category: PoseCategoryFilter
    favoritesOnly: boolean
    favoriteIds: Set<string>
  },
): PoseSummary[] {
  const q = opts.query.trim().toLowerCase()
  return items.filter((item) => {
    if (opts.favoritesOnly && !opts.favoriteIds.has(item.id)) return false
    if (opts.category !== 'all' && !item.categories.includes(opts.category)) return false
    if (!q) return true
    const hay = `${item.label} ${item.id} ${item.tags.join(' ')} ${item.categories.join(' ')}`.toLowerCase()
    return hay.includes(q)
  })
}

/** @deprecated */
export function filterPoseCatalog(
  items: PoseSummary[],
  opts: {
    query: string
    category: PoseCategoryFilter
    favoritesOnly: boolean
    favoriteIds: Set<string>
  },
) {
  return filterPoseSummaries(items, opts)
}
