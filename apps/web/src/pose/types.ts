/** Frontend DTOs for Backend PoseDefinition — not a second domain. */

export type PoseAngle = 'front' | 'diag' | 'side' | 'above' | 'below'

export type PoseSummary = {
  id: string
  label: string
  categories: string[]
  tags: string[]
  people_count: number
  content_rating: string
  default_view: PoseAngle | string
  available_views: string[]
  thumbnail_url: string | null
}

export type PoseRefLine = {
  asset_id?: string | null
  url: string
  sha256: string
  mime?: string
}

export type PoseViewDetail = {
  id: string
  angle: string
  prompt: string
  references: {
    line?: PoseRefLine
  }
  qc_status: string
}

export type PoseDetail = PoseSummary & {
  views: Record<string, PoseViewDetail>
  source: {
    provider: string
    version: string
    license: string
    source_url?: string
    pack?: string
    modality?: string
  }
}

/** @deprecated Prefer PoseSummary from API. Kept for ShotStudio transitional SelectedPose. */
export type PoseCard = {
  id: string
  title: string
  subtitle?: string
  categories: string[]
  tags: string[]
  thumbUrl: string
  posePrompt: string
  referenceUri?: string
  backendKinds: Array<'prompt' | 'reference_image' | 'openpose' | 'pose_lora'>
  defaultStrength: number
  availableViews?: string[]
}

export type SelectedPose = {
  poseId: string
  poseView: string
  strength: number
  flipHorizontal: boolean
  appliedAt: string
  /** Transitional card projection for ShotStudio PosePicker display */
  card: PoseCard
}

export function summaryToCard(summary: PoseSummary, detail?: PoseDetail | null): PoseCard {
  const viewKey = summary.default_view
  const view = detail?.views?.[viewKey]
  const line = view?.references?.line
  return {
    id: summary.id,
    title: summary.label,
    categories: summary.categories,
    tags: summary.tags,
    thumbUrl: summary.thumbnail_url || '',
    posePrompt: view?.prompt || '',
    referenceUri: line?.url,
    backendKinds: line ? ['reference_image', 'prompt'] : ['prompt'],
    defaultStrength: 1,
    availableViews: summary.available_views,
  }
}
