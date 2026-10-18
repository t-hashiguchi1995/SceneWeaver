import { Link, createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

export const Route = createFileRoute('/visual-library')({
  component: VisualLibraryStubPage,
})

function VisualLibraryStubPage() {
  const { t } = useTranslation('home')
  return (
    <section className="page" data-testid="visual-library-page">
      <h1>{t('visualLibraryTitle')}</h1>
      <p className="lede">{t('visualLibraryLede')}</p>
      <p className="meta">{t('visualLibraryComing')}</p>
      <div className="cta-row">
        <Link to="/projects" className="btn primary" data-testid="visual-library-fallback">
          {t('visualLibraryFallback')}
        </Link>
      </div>
    </section>
  )
}
