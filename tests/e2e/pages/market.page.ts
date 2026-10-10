import type { Page } from '@playwright/test'

export class WardrobePage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/wardrobe')
  }

  itemRows() {
    return this.page.getByTestId('market-item')
  }

  async openOutfit(titleFragment: string) {
    await this.page.getByTestId('market-list').getByRole('button', { name: titleFragment }).click()
  }
}
