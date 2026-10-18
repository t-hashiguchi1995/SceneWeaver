import type { ProjectDashboard } from './api'

export type PrimaryNext = NonNullable<ProjectDashboard['workflow']>['primary_next']

export type WorkflowLink =
  | { to: '/projects/$projectId/story'; params: { projectId: string }; search?: { sceneId?: string; beatId?: string } }
  | { to: '/projects/$projectId/wardrobe'; params: { projectId: string } }
  | { to: '/projects/$projectId/shots'; params: { projectId: string }; search?: { beatId?: string } }
  | { to: '/projects/$projectId/shots/$shotId'; params: { projectId: string; shotId: string } }
  | {
      to: '/projects/$projectId/shots/$shotId/generations/$attemptId'
      params: { projectId: string; shotId: string; attemptId: string }
    }
  | { to: '/projects/$projectId/csp'; params: { projectId: string } }
  | { to: '/projects/$projectId/release'; params: { projectId: string } }
  | { to: '/projects/$projectId'; params: { projectId: string } }

export function primaryNextLink(projectId: string, next: PrimaryNext): WorkflowLink | null {
  switch (next.kind) {
    case 'create_story':
    case 'continue_story':
      return {
        to: '/projects/$projectId/story',
        params: { projectId },
        search: { sceneId: next.scene_id, beatId: next.beat_id },
      }
    case 'choose_outfit':
      return { to: '/projects/$projectId/wardrobe', params: { projectId } }
    case 'configure_shot':
      if (next.shot_id) {
        return {
          to: '/projects/$projectId/shots/$shotId',
          params: { projectId, shotId: next.shot_id },
        }
      }
      return {
        to: '/projects/$projectId/shots',
        params: { projectId },
        search: next.beat_id ? { beatId: next.beat_id } : undefined,
      }
    case 'review_generation':
      if (next.shot_id && next.attempt_id) {
        return {
          to: '/projects/$projectId/shots/$shotId/generations/$attemptId',
          params: { projectId, shotId: next.shot_id, attemptId: next.attempt_id },
        }
      }
      if (next.shot_id) {
        return {
          to: '/projects/$projectId/shots/$shotId',
          params: { projectId, shotId: next.shot_id },
        }
      }
      return { to: '/projects/$projectId/shots', params: { projectId } }
    case 'create_csp_handoff':
      return { to: '/projects/$projectId/csp', params: { projectId } }
    case 'prepare_release':
      return { to: '/projects/$projectId/release', params: { projectId } }
    case 'complete':
      return { to: '/projects/$projectId', params: { projectId } }
    default: {
      const _exhaustive: never = next.kind
      void _exhaustive
      return { to: '/projects/$projectId', params: { projectId } }
    }
  }
}

export function stageStatus(
  done: number,
  total: number,
): 'complete' | 'in_progress' | 'not_started' {
  if (total === 0) return 'not_started'
  if (done >= total) return 'complete'
  if (done > 0) return 'in_progress'
  return 'not_started'
}
