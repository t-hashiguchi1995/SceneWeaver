import type { Page } from '@playwright/test'

export class JobsPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/jobs')
  }

  async enqueueStub() {
    await this.page.getByTestId('job-enqueue-stub').click()
  }

  jobStatuses() {
    return this.page.getByTestId('job-status')
  }

  liveStatus() {
    return this.page.getByTestId('job-live-status-label')
  }
}
