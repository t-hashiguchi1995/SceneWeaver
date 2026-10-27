import type { PoseCard } from './types'

/**
 * Built-in Pose Gallery seed.
 * Thumbs are anonymous mannequin / silhouette refs — never character identity.
 * referenceUri uses asset:// placeholders resolved when e2e/live seeds upload poses.
 */
export const POSE_CATALOG: PoseCard[] = [
  {
    id: 'pose_front_standing',
    title: 'Front standing',
    subtitle: 'full body / eye level',
    categories: ['standing'],
    tags: ['standing', 'front', 'full body', 'neutral'],
    thumbUrl: '/poses/pose_front_standing.png',
    posePrompt: 'standing, full body, facing viewer, arms at sides, natural posture',
    referenceUri: 'asset://pose/fixture.png',
    backendKinds: ['reference_image', 'prompt'],
    defaultStrength: 1.0,
  },
  {
    id: 'pose_hand_on_hip',
    title: 'One hand on hip',
    subtitle: 'standing / elegant',
    categories: ['standing', 'hands', 'cute'],
    tags: ['standing', 'hand on hip', 'elegant', 'slight 3/4'],
    thumbUrl: '/poses/pose_hand_on_hip.png',
    posePrompt: 'standing with one hand on hip, slight 3/4 view, confident posture, full body',
    referenceUri: 'asset://pose/fixture.png',
    backendKinds: ['reference_image', 'prompt'],
    defaultStrength: 1.0,
  },
  {
    id: 'pose_look_over_shoulder',
    title: 'Looking over shoulder',
    subtitle: 'standing / glance',
    categories: ['standing', 'cute', 'dynamic'],
    tags: ['standing', 'looking back', 'over shoulder', '3/4'],
    thumbUrl: '/poses/pose_look_over_shoulder.png',
    posePrompt: 'standing, looking over shoulder at viewer, twisted torso, full body',
    referenceUri: 'asset://pose/fixture.png',
    backendKinds: ['reference_image', 'prompt'],
    defaultStrength: 0.95,
  },
  {
    id: 'pose_sitting_chair',
    title: 'Sitting upright',
    subtitle: 'sitting / composed',
    categories: ['sitting'],
    tags: ['sitting', 'chair', 'upright', 'knees together'],
    thumbUrl: '/poses/pose_front_standing.png',
    posePrompt: 'sitting on chair, upright posture, hands on lap, knees together, medium full shot',
    backendKinds: ['prompt'],
    defaultStrength: 1.0,
  },
  {
    id: 'pose_running',
    title: 'Running',
    subtitle: 'action / dynamic',
    categories: ['action', 'walking', 'dynamic'],
    tags: ['running', 'action', 'dynamic', 'full body'],
    thumbUrl: '/poses/pose_hand_on_hip.png',
    posePrompt: 'running pose, dynamic motion, one leg forward, arms swinging, full body',
    backendKinds: ['prompt'],
    defaultStrength: 1.0,
  },
  {
    id: 'pose_fighting_stance',
    title: 'Fighting stance',
    subtitle: 'action / combat',
    categories: ['fighting', 'action', 'dynamic'],
    tags: ['fighting', 'stance', 'ready', 'dynamic'],
    thumbUrl: '/poses/pose_look_over_shoulder.png',
    posePrompt: 'fighting stance, knees bent, fists raised, ready to strike, full body',
    backendKinds: ['prompt'],
    defaultStrength: 1.0,
  },
  {
    id: 'pose_hands_together',
    title: 'Hands clasped',
    subtitle: 'hands / cute',
    categories: ['hands', 'cute', 'standing'],
    tags: ['hands together', 'clasped', 'shy', 'standing'],
    thumbUrl: '/poses/pose_front_standing.png',
    posePrompt: 'standing, hands clasped in front of chest, slight lean forward, cute posture',
    backendKinds: ['prompt'],
    defaultStrength: 1.0,
  },
  {
    id: 'pose_walking',
    title: 'Walking',
    subtitle: 'walking / casual',
    categories: ['walking', 'standing', 'dynamic'],
    tags: ['walking', 'stride', 'casual', 'full body'],
    thumbUrl: '/poses/pose_hand_on_hip.png',
    posePrompt: 'walking forward, mid-stride, natural arm swing, full body, slight 3/4',
    backendKinds: ['prompt'],
    defaultStrength: 1.0,
  },
]

export const POSE_CATEGORY_FILTERS = [
  'all',
  'standing',
  'sitting',
  'action',
  'walking',
  'fighting',
  'hands',
  'cute',
  'dynamic',
] as const

export type PoseCategoryFilter = (typeof POSE_CATEGORY_FILTERS)[number]

export function findPoseCard(id: string): PoseCard | undefined {
  return POSE_CATALOG.find((p) => p.id === id)
}

export function filterPoseCatalog(
  cards: PoseCard[],
  opts: { query?: string; category?: PoseCategoryFilter; favoritesOnly?: boolean; favoriteIds?: Set<string> },
): PoseCard[] {
  const q = (opts.query || '').trim().toLowerCase()
  const cat = opts.category || 'all'
  return cards.filter((card) => {
    if (opts.favoritesOnly && opts.favoriteIds && !opts.favoriteIds.has(card.id)) return false
    if (cat !== 'all' && !card.categories.includes(cat)) return false
    if (!q) return true
    const hay = `${card.title} ${card.subtitle || ''} ${card.tags.join(' ')} ${card.posePrompt}`.toLowerCase()
    return hay.includes(q)
  })
}
