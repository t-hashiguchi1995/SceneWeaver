import { test as base } from '@playwright/test'

import { ApiClient, type SeedResult } from '../support/api-client'
import { HomePage } from '../pages/home.page'
import { ProjectsPage } from '../pages/project.page'
import { JobsPage } from '../pages/jobs.page'
import { ReleasePage } from '../pages/release.page'
import { WardrobePage } from '../pages/market.page'
import { StoryPage } from '../pages/story.page'
import { ShotPage } from '../pages/shot.page'
import { CspPage } from '../pages/csp.page'
import { TryOnPage } from '../pages/tryon.page'

type SceneWeaverFixtures = {
  api: ApiClient
  home: HomePage
  projects: ProjectsPage
  jobs: JobsPage
  story: StoryPage
  wardrobe: WardrobePage
  tryon: TryOnPage
  shots: ShotPage
  release: ReleasePage
  csp: CspPage
  seedScenario: (scenario: string) => Promise<SeedResult>
  applySeedContext: (seed: SeedResult, extra?: Record<string, string>) => Promise<void>
}

export const test = base.extend<SceneWeaverFixtures>({
  api: async ({}, use) => {
    const api = new ApiClient()
    await use(api)
  },
  home: async ({ page }, use) => {
    await use(new HomePage(page))
  },
  projects: async ({ page }, use) => {
    await use(new ProjectsPage(page))
  },
  jobs: async ({ page }, use) => {
    await use(new JobsPage(page))
  },
  story: async ({ page }, use) => {
    await use(new StoryPage(page))
  },
  wardrobe: async ({ page }, use) => {
    await use(new WardrobePage(page))
  },
  tryon: async ({ page }, use) => {
    await use(new TryOnPage(page))
  },
  shots: async ({ page }, use) => {
    await use(new ShotPage(page))
  },
  release: async ({ page }, use) => {
    await use(new ReleasePage(page))
  },
  csp: async ({ page }, use) => {
    await use(new CspPage(page))
  },
  seedScenario: async ({ api }, use) => {
    await use(async (scenario: string) => {
      await api.reset()
      return api.seed(scenario)
    })
  },
  applySeedContext: async ({ page }, use) => {
    await use(async (seed, extra = {}) => {
      await page.goto('/')
      await page.evaluate(
        ({ seed, extra }) => {
          const ctx = {
            projectId: seed.project_id,
            characterId: seed.character_id,
            sceneId: seed.scene_id,
            beatId: seed.beat_id,
            marketplaceItemId: seed.marketplace_item_id,
            characterName: 'リゼヘル',
            ...extra,
          }
          sessionStorage.setItem('sceneweaver.studio', JSON.stringify(ctx))
        },
        { seed, extra },
      )
    })
  },
})

export { expect } from '@playwright/test'
