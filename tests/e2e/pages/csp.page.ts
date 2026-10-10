import type { Page } from '@playwright/test'

export class CspPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/csp')
  }

  async buildHandoff() {
    await this.page.getByTestId('csp-build-handoff').click()
  }

  revision() {
    return this.page.getByTestId('csp-revision')
  }

  manifest() {
    return this.page.getByTestId('csp-manifest')
  }
}
