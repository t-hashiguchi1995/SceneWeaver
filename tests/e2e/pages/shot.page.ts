import type { Page } from '@playwright/test'

export class ShotPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/shots')
  }

  async setBeatId(beatId: string) {
    await this.page.getByTestId('shot-beat-id').fill(beatId)
  }

  async planShot() {
    await this.page.getByTestId('shot-plan').click()
  }

  async enablePose(enabled = true) {
    const box = this.page.getByTestId('shot-use-pose')
    const checked = await box.isChecked()
    if (checked !== enabled) await box.click()
  }

  async generate() {
    await this.page.getByTestId('shot-generate').click()
  }

  async adoptCandidate(index: number) {
    await this.page.getByTestId(`generation-adopt-${index}`).click()
  }

  statusLabel() {
    return this.page.getByTestId('shot-status-label')
  }

  candidate(index: number) {
    return this.page.getByTestId(`generation-candidate-${index}`)
  }
}
