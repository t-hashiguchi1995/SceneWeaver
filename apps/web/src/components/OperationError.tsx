import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { formatErrorMessage, parseErrorCode } from '../i18n/format'

export type OperationErrorProps = {
  message: string
  title?: string
  onRetry?: () => void
  className?: string
  comfyUrl?: string
}

export function OperationError({
  message,
  title,
  onRetry,
  className = 'operation-error',
  comfyUrl,
}: OperationErrorProps) {
  const { t } = useTranslation('common')
  const [open, setOpen] = useState(false)
  const code = parseErrorCode(message)
  const userMessage = formatErrorMessage(t, message)
  const showConnection = code === 'COMFY_UNREACHABLE'

  return (
    <div className={className} data-testid="operation-error" role="alert">
      <p className="operation-error__title" data-testid="operation-error-title">
        {title || userMessage}
      </p>
      {title && (
        <p className="operation-error__message" data-testid="operation-error-message">
          {userMessage}
        </p>
      )}
      <div className="cta-row">
        {onRetry && (
          <button type="button" className="btn primary" data-testid="operation-error-retry" onClick={onRetry}>
            {t('errors.retry')}
          </button>
        )}
        {showConnection && (
          <Link to="/integrations" className="btn" data-testid="operation-error-integrations">
            {t('errors.checkConnection')}
          </Link>
        )}
      </div>
      <details
        className="operation-error__details"
        open={open}
        onToggle={(event) => setOpen((event.target as HTMLDetailsElement).open)}
      >
        <summary data-testid="operation-error-details-toggle">{t('errors.technicalDetails')}</summary>
        <pre data-testid="operation-error-details">
          {message}
          {showConnection
            ? `\n${t('errors.comfyUnreachableDetail', {
                url: comfyUrl || 'http://127.0.0.1:8188',
              })}`
            : ''}
        </pre>
      </details>
    </div>
  )
}
