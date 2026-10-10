import type { Page } from '@playwright/test'

export class ReviewPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/shots')
  }
}