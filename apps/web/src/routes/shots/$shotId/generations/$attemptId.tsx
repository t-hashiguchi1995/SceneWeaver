import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'

import { GenerationReviewView } from '../../../../components/GenerationReviewView'
import { saveStudioContext } from '../../../../lib/api'

export const Route = createFileRoute('/shots/$shotId/generations/$attemptId')({
  component: GenerationAttemptPage,
})

function GenerationAttemptPage() {
  const { shotId, attemptId } = Route.useParams()
  useEffect(() => {
    saveStudioContext({ shotId, generationAttemptId: attemptId })
  }, [shotId, attemptId])
  return <GenerationReviewView shotId={shotId} attemptId={attemptId} />
}
