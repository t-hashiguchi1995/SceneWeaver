import type { Page } from '@playwright/test'

export class ReviewPage {
  constructor(private page: Page) {}

  async goto(shotId?: string, attemptId?: string) {
    if (shotId && attemptId) {
      await this.page.goto(`/shots/${shotId}/generations/${attemptId}`)
      return
    }
    if (shotId) {
      await this.page.goto(`/shots/${shotId}/generations`)
      return
    }
    await this.page.goto('/review')
  }

  async waitReady() {
    await this.page.getByTestId('generation-review').waitFor({ state: 'visible', timeout: 20_000 })
    await this.page.getByTestId('generation-candidate-list').waitFor({ state: 'visible', timeout: 40_000 })
  }

  candidate(index: number) {
    return this.page.getByTestId(`generation-candidate-${index}`)
  }

  async selectCandidate(index: number) {
    await this.page.getByTestId(`generation-select-${index}`).click()
  }

  async adoptCandidate(index: number) {
    await this.selectCandidate(index)
    await this.page.getByTestId('generation-adopt').click()
  }

  finalPositive() {
    return this.page.getByTestId('generation-final-positive')
  }

  adoptedBanner() {
    return this.page.getByTestId('generation-adopted-banner')
  }

  async openShotStudio() {
    await this.page.getByTestId('review-open-shot-studio').click()
    await this.page.getByTestId('shots-page').waitFor({ state: 'visible', timeout: 20_000 })
  }
}
