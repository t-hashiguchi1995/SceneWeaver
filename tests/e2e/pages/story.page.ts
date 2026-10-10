import type { Page } from '@playwright/test'

export class StoryPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/story')
  }

  async selectProject(title: string) {
    await this.page.getByTestId('story-project-select').selectOption({ label: title })
  }

  async selectCharacter(name: string) {
    await this.page.getByTestId('story-character-select').selectOption({ label: name })
  }

  async createScene(title = 'Cafe') {
    await this.page.getByTestId('story-scene-title').fill(title)
    await this.page.getByTestId('story-create-scene').click()
  }

  async createBeat(intent = 'もう少し一緒にいたい') {
    await this.page.getByTestId('story-beat-intent').fill(intent)
    await this.page.getByTestId('story-create-beat').click()
  }

  async generateDialogue() {
    await this.page.getByTestId('story-generate-dialogue').click()
  }

  async lockCandidate(index: number) {
    await this.page.getByTestId(`dialogue-lock-${index}`).click()
  }

  candidate(index: number) {
    return this.page.getByTestId(`dialogue-candidate-${index}`)
  }
}
