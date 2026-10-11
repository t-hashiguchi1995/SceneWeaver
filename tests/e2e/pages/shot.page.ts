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
    await this.page.getByTestId('prompt-editor').waitFor({ state: 'visible', timeout: 20_000 })
    await this.page.getByTestId('shots-page').waitFor({ state: 'visible', timeout: 20_000 })
  }

  async enablePose(enabled = true) {
    const box = this.page.getByTestId('shot-use-pose')
    const checked = await box.isChecked()
    if (checked !== enabled) await box.click()
    if (enabled) {
      const uri = await this.page.evaluate(() => JSON.parse(sessionStorage.getItem('sceneweaver.studio') ?? '{}').poseAssetUri as string | undefined)
      await this.page.getByLabel('ポーズ参照画像URI').fill(uri ?? 'asset://pose/fixture.png')
    }
  }

  async appendPositive(fragment: string) {
    const box = this.page.getByTestId('prompt-positive')
    const current = await box.inputValue()
    await box.fill(`${current}, ${fragment}`)
  }

  async resetEdits() {
    await this.page.getByTestId('prompt-reset-edits').click()
  }

  async generate() {
    await this.page.getByTestId('shot-generate').click()
    await this.page.getByTestId('generation-review').waitFor({ state: 'visible', timeout: 40_000 })
    await this.page.getByTestId('generation-candidate-list').waitFor({ state: 'visible', timeout: 40_000 })
  }

  async openReview() {
    await this.page.getByTestId('shot-open-review').click()
    await this.page.getByTestId('generation-review').waitFor({ state: 'visible', timeout: 20_000 })
  }

  statusLabel() {
    return this.page.getByTestId('shot-status-label')
  }

  candidate(index: number) {
    return this.page.getByTestId(`generation-candidate-${index}`)
  }

  positive() {
    return this.page.getByTestId('prompt-positive')
  }
}
