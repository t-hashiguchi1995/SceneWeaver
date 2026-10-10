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
    await this.page.getByTestId('nav-story').click()
  }

  async openWardrobe() {
    await this.page.getByTestId('nav-wardrobe').click()
  }

  async openShots() {
    await this.page.getByTestId('nav-shots').click()
  }

  async openCsp() {
    await this.page.getByTestId('nav-csp').click()
  }

  async openJobs() {
    await this.page.getByTestId('nav-jobs').click()
  }

  async openRelease() {
    await this.page.getByTestId('nav-release').click()
  }
}
