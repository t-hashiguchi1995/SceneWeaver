import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { formatErrorMessage, parseErrorCode } from '../i18n/format'

type Props = {
  message: string
  comfyUrl?: string
  className?: string
}

export function ErrorBanner({ message, comfyUrl, className = 'error' }: Props) {
  const { t } = useTranslation('common')
  const code = parseErrorCode(message)
  const title = formatErrorMessage(t, message)
  const showComfyHelp = code === 'COMFY_UNREACHABLE'

  return (
    <div className={className} data-testid="error-banner" role="alert">
      <p data-testid="error-title">{title}</p>
      {showComfyHelp && (
        <>
          <p className="meta" data-testid="error-detail">
            {t('errors.comfyUnreachableDetail', {
              url: comfyUrl || 'http://127.0.0.1:8188',
            })}
          </p>
          <div className="cta-row">
            <Link to="/integrations" className="btn" data-testid="error-open-integrations">
              {t('errors.openIntegrations')}
            </Link>
          </div>
        </>
      )}
      {code && (
        <p className="meta" data-testid="error-code">
          {code}
        </p>
      )}
    </div>
  )
}
