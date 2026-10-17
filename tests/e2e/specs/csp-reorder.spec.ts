import { test, expect } from '../fixtures/sceneweaver.fixture'

test('CSP panel reorder is sent to handoff and kept in the UI after build', async ({
  page,
  api,
  seedScenario,
  applySeedContext,
}) => {
  const seeded = await seedScenario('m4_visual')
  await applySeedContext(seeded)

  const dialogue1 = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
  await api.lockScript(dialogue1.candidates[0].id, 'パネルAのセリフ')
  const shot1 = await api.planShot(seeded.beat_id!)
  const render1 = await api.renderShot(shot1.id, true)
  const adopt1 = await api.setAssetDecision(render1.output_asset_ids[0], 'adopted')

  const beat2 = await api.createBeat(seeded.scene_id!, '二枚目の展開', seeded.character_id!)
  const dialogue2 = await api.generateDialogue(beat2.id, seeded.character_id!)
  await api.lockScript(dialogue2.candidates[0].id, 'パネルBのセリフ')
  const shot2 = await api.planShot(beat2.id)
  const render2 = await api.renderShot(shot2.id, true)
  const adopt2 = await api.setAssetDecision(render2.output_asset_ids[0], 'adopted')

  const projectPath = `/projects/${seeded.project_id}`
  await page.goto(`${projectPath}/csp`)
  await expect(page.getByTestId('csp-page-plan').locator('article')).toHaveCount(2)

  const beforeFirst = await page.getByTestId('csp-panel-0').getAttribute('data-asset-id')
  const beforeSecond = await page.getByTestId('csp-panel-1').getAttribute('data-asset-id')
  expect(beforeFirst).toBeTruthy()
  expect(beforeSecond).toBeTruthy()
  expect(beforeFirst).not.toBe(beforeSecond)

  await page.getByTestId('csp-panel-down-0').click()
  await expect(page.getByTestId('csp-panel-0')).toHaveAttribute('data-asset-id', beforeSecond!)
  await expect(page.getByTestId('csp-panel-1')).toHaveAttribute('data-asset-id', beforeFirst!)

  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/csp/handoffs') && response.request().method() === 'POST',
  )
  await page.getByTestId('csp-build-handoff').click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
  const result = await response.json()
  const panels = result.manifest.pages[0].panels as Array<{ asset_id: string; panel_no: number }>
  expect(panels.map((panel) => panel.asset_id)).toEqual([beforeSecond, beforeFirst])
  expect(panels.map((panel) => panel.panel_no)).toEqual([1, 2])
  expect([adopt1.asset_id, adopt2.asset_id].sort()).toEqual(
    [beforeFirst, beforeSecond].sort(),
  )

  await expect(page.getByTestId('csp-revision')).toHaveText('r001')
  await expect(page.getByTestId('csp-panel-0')).toHaveAttribute('data-asset-id', beforeSecond!)
  await expect(page.getByTestId('csp-panel-1')).toHaveAttribute('data-asset-id', beforeFirst!)
})
