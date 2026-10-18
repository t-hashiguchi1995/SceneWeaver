import { Link, createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

export const Route = createFileRoute('/quick-test')({
  component: QuickTestStubPage,
})

function QuickTestStubPage() {
  const { t } = useTranslation('home')
  return (
    <section className="page" data-testid="quick-test-page">
      <h1>{t('quickTestTitle')}</h1>
      <p className="lede">{t('quickTestLede')}</p>
      <p className="meta">{t('quickTestComing')}</p>
      <div className="cta-row">
        <Link to="/projects" className="btn primary" data-testid="quick-test-fallback">
          {t('quickTestFallback')}
        </Link>
      </div>
    </section>
  )
}
