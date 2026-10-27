export type PoseBackendKind = 'prompt' | 'reference_image' | 'openpose' | 'pose_lora'

export type PoseCategory =
  | 'standing'
  | 'sitting'
  | 'action'
  | 'walking'
  | 'fighting'
  | 'hands'
  | 'cute'
  | 'dynamic'

export type PoseCard = {
  id: string
  title: string
  subtitle?: string
  categories: PoseCategory[]
  tags: string[]
  /** Gallery thumbnail (static /public path). No character identity. */
  thumbUrl: string
  /** Text pose instruction — character-agnostic. */
  posePrompt: string
  /** Optional image URI for LLLite / OpenPose control (asset:// when seeded). */
  referenceUri?: string
  backendKinds: PoseBackendKind[]
  defaultStrength: number
}

export type SelectedPose = {
  card: PoseCard
  strength: number
  flipHorizontal: boolean
  appliedAt: string
}
