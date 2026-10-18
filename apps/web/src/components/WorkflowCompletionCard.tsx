import type { ReactNode } from 'react'

type WorkflowCompletionCardProps = {
  title: string
  description: string
  action: ReactNode
  testId?: string
}

export function WorkflowCompletionCard({
  title,
  description,
  action,
  testId = 'workflow-completion-card',
}: WorkflowCompletionCardProps) {
  return (
    <aside className="panel-card workflow-completion-card" data-testid={testId}>
      <p className="eyebrow">{title}</p>
      <p className="lede">{description}</p>
      <div className="cta-row">{action}</div>
    </aside>
  )
}
