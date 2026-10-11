import type { Page } from '@playwright/test'

export class CspPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/csp')
  }

  async buildHandoff() {
    await this.page.getByTestId('csp-build-handoff').click()
    await this.page.getByTestId('csp-result').waitFor()
    await this.page.locator('summary').filter({ hasText: 'マニフェストの詳細' }).click()
  }

  revision() {
    return this.page.getByTestId('csp-revision')
  }

  manifest() {
    return this.page.getByTestId('csp-manifest')
  }
}
