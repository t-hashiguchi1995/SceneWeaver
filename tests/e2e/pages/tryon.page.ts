import type { Page } from '@playwright/test'

export class TryOnPage {
  constructor(private page: Page) {}

  async generate() {
    await this.page.getByTestId('tryon-generate').click()
  }

  async adoptCandidate(index: number) {
    await this.page.getByTestId(`tryon-adopt-${index}`).click()
  }

  statusLabel() {
    return this.page.getByTestId('tryon-status-label')
  }

  candidate(index: number) {
    return this.page.getByTestId(`tryon-candidate-${index}`)
  }
}
