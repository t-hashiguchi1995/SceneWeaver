import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('M2 Story', () => {
  test('UI dialogue generate → 3 candidates → lock', async ({
    seedScenario,
    applySeedContext,
    home,
    story,
    page,
  }) => {
    const seeded = await seedScenario('m2_story')
    await applySeedContext(seeded)

    await home.openStory()
    await story.selectProject(`E2E m2_story`)
    await story.selectCharacter('リゼヘル')
    await story.createScene('Night Cafe')
    await expect(page.getByTestId('story-status')).toContainText('Scene created')
    await story.createBeat('stay a little longer')
    await expect(page.getByTestId('story-status')).toContainText('Beat created')
    await story.generateDialogue()
    await expect(story.candidate(0)).toBeVisible()
    await expect(story.candidate(1)).toBeVisible()
    await expect(story.candidate(2)).toBeVisible()
    await story.lockCandidate(1)
    await expect(page.getByTestId('story-locked-banner')).toBeVisible()
  })
})
