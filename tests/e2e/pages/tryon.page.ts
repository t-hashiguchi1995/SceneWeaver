import type { Page } from '@playwright/test'

export class TryOnPage {
  constructor(private page: Page) {}

  async generate() {
    await this.page.getByTestId('tryon-generate').click()
    await this.page.getByTestId('tryon-candidate-list').waitFor({ state: 'visible', timeout: 40_000 })
  }

  async adoptCandidate(index: number) {
    const tab = this.page.getByTestId('wardrobe-tab-tryon')
    if (await tab.count()) await tab.click()
    await this.page.getByTestId(`tryon-adopt-${index}`).click()
  }

  statusLabel() {
    return this.page.getByTestId('tryon-status-label')
  }

  candidate(index: number) {
    return this.page.getByTestId(`tryon-candidate-${index}`)
  }
}
