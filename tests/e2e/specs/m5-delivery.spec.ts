import { test, expect } from '../fixtures/sceneweaver.fixture'
import { expectFile, expectPanelMatchesAdopted, expectJsonFile } from '../support/assertions'

test.describe('M5 Delivery', () => {
  test('PagePlan → CSP handoff real bytes → Release X/pixiv/Patreon Preview', async ({
    seedScenario,
    applySeedContext,
    api,
    csp,
    release,
    page,
  }) => {
    const seeded = await seedScenario('m5_delivery')
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    const locked = await api.lockScript(dialogue.candidates[0].id)
    const shot = await api.planShot(seeded.beat_id!)
    const rendered = await api.renderShot(shot.id, true)
    const decision = await api.setAssetDecision(rendered.output_asset_ids[0], 'adopted')

    await applySeedContext(seeded, {
      lockedEventId: locked.id,
      lockedText: locked.text,
      shotId: shot.id,
      adoptedRenderAssetId: decision.asset_id,
      adoptedRenderSha256: decision.sha256,
    })

    await csp.goto()
    await csp.buildHandoff()
    await expect(csp.revision()).toHaveText('r001')
    await expect(csp.manifest()).toContainText(decision.asset_id)

    const state = await api.state()
    const handoff = state.handoffs[0]
    expect(handoff.panel_exists).toBe(true)
    await expectPanelMatchesAdopted(handoff.path, decision.sha256)
    await expectJsonFile(handoff.path + '/project_manifest.json', (data) => {
      const pages = data.pages as Array<{ panels: Array<{ asset_id: string; sha256: string }> }>
      return pages[0]?.panels[0]?.asset_id === decision.asset_id &&
        pages[0]?.panels[0]?.sha256 === decision.sha256
    })
    await expectFile(handoff.path + '/script/script_events.tsv')

    await release.goto()
    await release.buildPreview()
    await release.openPlatform('x')
    await expect(release.edition('x')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'X', exact: true })).toBeVisible()
    await release.openPlatform('pixiv')
    await expect(release.edition('pixiv')).toBeVisible()
    await release.openPlatform('patreon')
    await expect(release.edition('patreon')).toBeVisible()
  })
})
