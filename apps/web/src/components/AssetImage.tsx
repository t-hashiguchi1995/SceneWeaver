import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../lib/api'

export function AssetImage({ assetId, alt }: { assetId: string; alt: string }) {
  const [failed, setFailed] = useState('')
  const { t } = useTranslation('common')
  if (failed === assetId) return <span className="asset-unavailable" role="img" aria-label={alt}>{t('assetUnavailable')}</span>
  return <img className="asset-image" src={api.assetContentUrl(assetId)} alt={alt} loading="lazy" onError={() => setFailed(assetId)} />
}
