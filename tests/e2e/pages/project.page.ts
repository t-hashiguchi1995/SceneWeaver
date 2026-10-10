import type { Page } from '@playwright/test'

export class ProjectsPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/projects')
  }

  async create(title: string) {
    await this.page.getByTestId('project-title-input').fill(title)
    await this.page.getByTestId('project-create-button').click()
  }

  projectLink(title: string) {
    return this.page.getByTestId('project-list').getByRole('link', { name: title })
  }
}