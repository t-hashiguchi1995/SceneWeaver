import { useQuery } from '@tanstack/react-query'

import { api, type ProjectContext } from '../lib/api'

export type ProjectContextIds = {
  projectId?: string
  sceneId?: string
  beatId?: string
  shotId?: string
}

export function useProjectContextQuery(ids: ProjectContextIds) {
  const { projectId, sceneId, beatId, shotId } = ids
  return useQuery({
    queryKey: ['project-context', projectId, sceneId, beatId, shotId],
    queryFn: () =>
      api.projectContext(projectId!, {
        sceneId,
        beatId,
        shotId,
      }),
    enabled: Boolean(projectId),
  })
}

export type { ProjectContext }
