import type { Page } from '@playwright/test'

export class HomePage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/')
  }

  async openProjects() {
    await this.page.getByTestId('nav-projects').click()
  }

  async openStory() {
    await this.page.goto('/story')
  }

  async openWardrobe() {
    await this.page.goto('/wardrobe')
  }

  async openShots() {
    await this.page.goto('/shots')
  }

  async openCsp() {
    await this.page.goto('/csp')
  }

  async openJobs() {
    await this.page.goto('/jobs')
  }

  async openRelease() {
    await this.page.goto('/release')
  }
}
