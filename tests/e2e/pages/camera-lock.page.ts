import { type Page } from '@playwright/test'

export class CameraLockPage {
  constructor(readonly page: Page) {}
  get panel() { return this.page.getByTestId('camera-lock-panel') }
  get rigSelect() { return this.panel.getByTestId('camera-rig-select') }
  get rigStatus() { return this.panel.getByTestId('camera-rig-status') }
  get anchorInfo() { return this.panel.getByTestId('camera-anchor-info') }
  get faceWarning() { return this.panel.getByTestId('camera-anchor-face-warning') }
  get bindButton() { return this.panel.getByTestId('camera-binding-bind') }
  get bindingState() { return this.panel.getByTestId('camera-binding-state') }
  get attempts() { return this.panel.getByTestId('camera-attempts') }
  async createRig(name: string, facePolicy = 'partial_allowed') {
    await this.panel.getByTestId('camera-rig-name').fill(name)
    await this.panel.getByTestId('camera-rig-frame-width').fill('1536')
    await this.panel.getByTestId('camera-rig-frame-height').fill('864')
    await this.panel.getByTestId('camera-rig-face-policy').selectOption(facePolicy)
    await this.panel.getByTestId('camera-rig-create').click()
  }
  async registerAnchorById(assetId: string) {
    await this.panel.getByTestId('camera-anchor-asset-id').fill(assetId)
    await this.panel.getByTestId('camera-anchor-register').click()
  }
  async bindCurrentShot(facePolicy = 'full_visible') {
    await this.panel.getByTestId('camera-binding-face-policy').selectOption(facePolicy)
    await this.bindButton.click()
  }
  async lockRig() { await this.panel.getByTestId('camera-rig-lock').click() }
  async renderWithLock() { await this.panel.getByTestId('camera-lock-render').click() }
}
