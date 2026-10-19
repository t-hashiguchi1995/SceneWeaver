type ActionableEmptyStateProps = {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  actionDisabled?: boolean
  actionTestId?: string
}

export function ActionableEmptyState({
  title,
  description,
  actionLabel,
  onAction,
  actionDisabled,
  actionTestId = 'actionable-empty-action',
}: ActionableEmptyStateProps) {
  return (
    <div className="actionable-empty" data-testid="actionable-empty">
      <p className="actionable-empty__title">{title}</p>
      {description && <p className="meta">{description}</p>}
      {actionLabel && onAction && (
        <button
          type="button"
          className="btn primary"
          data-testid={actionTestId}
          disabled={actionDisabled}
          onClick={onAction}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
