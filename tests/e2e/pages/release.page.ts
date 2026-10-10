import type { Page } from '@playwright/test'

export class ReleasePage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/release')
  }

  async buildPreview() {
    await this.page.getByTestId('release-preview-button').click()
  }

  previewJson() {
    return this.page.getByTestId('release-preview-json')
  }

  edition(platform: 'x' | 'pixiv' | 'patreon') {
    return this.page.getByTestId(`release-edition-${platform}`)
  }
}
