import type { Page } from '@playwright/test'

export class ShotPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/shots', { waitUntil: 'domcontentloaded', timeout: 60_000 })
  }

  async setBeatId(beatId: string) {
    await this.page.getByTestId('shot-beat-id').fill(beatId)
  }

  async planShot() {
    await this.page.getByTestId('shot-plan').click()
    await this.page.getByTestId('prompt-editor').waitFor({ state: 'visible', timeout: 20_000 })
    await this.page.getByTestId('shots-page').waitFor({ state: 'visible', timeout: 20_000 })
  }

  async openAdvanced() {
    const panel = this.page.getByTestId('shot-advanced-settings')
    if (!(await panel.getAttribute('open'))) {
      await panel.locator('summary').click()
    }
  }

  async enablePose(enabled = true) {
    if (!enabled) {
      const clear = this.page.getByTestId('pose-clear')
      if (await clear.count()) await clear.click()
      return
    }
    // Gallery-first: open Pose Gallery and apply a reference-image pose.
    await this.page.getByTestId('pose-choose').or(this.page.getByTestId('pose-change')).click()
    await this.page.getByTestId('pose-gallery').waitFor({ state: 'visible', timeout: 10_000 })
    const seededUri = await this.page.evaluate(
      () =>
        JSON.parse(sessionStorage.getItem('sceneweaver.studio') ?? '{}').poseAssetUri as
          | string
          | undefined,
    )
    await this.page.getByTestId('pose-apply-pose_hand_on_hip').click()
    await this.page.getByTestId('pose-selected').waitFor({ state: 'visible', timeout: 10_000 })
    if (seededUri) {
      await this.page.evaluate((uri) => {
        const key = 'sceneweaver.studio'
        const ctx = JSON.parse(sessionStorage.getItem(key) ?? '{}')
        ctx.poseAssetUri = uri
        sessionStorage.setItem(key, JSON.stringify(ctx))
        const sel = JSON.parse(localStorage.getItem('sceneweaver.pose.selected') ?? 'null')
        if (sel?.card) {
          sel.card.referenceUri = uri
          localStorage.setItem('sceneweaver.pose.selected', JSON.stringify(sel))
        }
      }, seededUri)
    }
  }

  async selectGenerationEngine(capability: 'BaseRender' | 'LayoutGuidedRender') {
    await this.page.getByTestId('shot-generation-engine').selectOption(capability)
  }

  generationEngine() {
    return this.page.getByTestId('shot-generation-engine')
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
