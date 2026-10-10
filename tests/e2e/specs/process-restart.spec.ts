import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '../fixtures/sceneweaver.fixture'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')

/**
 * #6 completion gap: /api/test/reload ≠ real process restart.
 * Kill API+Worker, restart against same runtime DB/assets, assert Project/Shot/Generation/Release survive.
 */
test.describe('Process restart persistence', () => {
  test('API+Worker kill→restart retains Project / Shot / Generation / Release', async ({
    api,
    seedScenario,
  }) => {
    await api.reset()
    const seeded = await seedScenario('vertical_slice')
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    const tryon = await api.runTryOn(
      seeded.character_id!,
      seeded.marketplace_item_id!,
      seeded.scene_id,
    )
    await api.setAssetDecision(tryon.candidate_asset_ids[0], 'adopted')
    await api.adoptTryOn(tryon.session_id, tryon.candidate_asset_ids[0], seeded.scene_id)
    const shot = await api.planShot(seeded.beat_id!)
    const rendered = await api.renderShot(shot.id, false)
    await api.setAssetDecision(rendered.output_asset_ids[0], 'adopted')
    const handoff = await api.cspHandoff({
      project_id: seeded.project_id,
      pages: [
        {
          page_no: 1,
          panels: [
            {
              panel_no: 1,
              shot_id: shot.id,
              script_event_ids: [dialogue.candidates[0].id],
              asset_id: rendered.output_asset_ids[0],
            },
          ],
        },
      ],
      script_rows: [{ id: dialogue.candidates[0].id, text: 'restart smoke' }],
    })
    const preview = await api.releasePreview('Restart Smoke', 'persist across kill')

    const before = await api.state()
    expect(before.project_count).toBeGreaterThanOrEqual(1)
    expect(before.shot_count).toBeGreaterThanOrEqual(1)
    expect(before.generation_attempt_count).toBeGreaterThanOrEqual(1)
    expect(before.handoff_count).toBeGreaterThanOrEqual(1)
    expect(handoff.revision).toBeTruthy()
    expect(preview).toBeTruthy()

    execFileSync('bash', [path.join(root, 'scripts/e2e/restart-api-worker.sh'), 'e2e'], {
      cwd: root,
      env: {
        ...process.env,
        SCENEWEAVER_RUNTIME_DIR: process.env.SCENEWEAVER_RUNTIME_DIR ?? path.join(root, 'runtime-e2e'),
        SCENEWEAVER_PORT: process.env.SCENEWEAVER_PORT ?? '8010',
        SCENEWEAVER_CORS_ORIGINS:
          process.env.SCENEWEAVER_CORS_ORIGINS ??
          'http://127.0.0.1:5174,http://localhost:5174',
        SCENEWEAVER_FAKE_IMAGE_DELAY_MS: process.env.SCENEWEAVER_FAKE_IMAGE_DELAY_MS ?? '400',
      },
      stdio: 'inherit',
    })

    // Fresh TCP after kill — retry briefly (curl in script can race Node keep-alive).
    let health: Record<string, string> | null = null
    for (let i = 0; i < 20; i++) {
      try {
        health = await api.health()
        break
      } catch {
        await new Promise((r) => setTimeout(r, 250))
      }
    }
    expect(health?.environment).toBe('e2e')

    const after = await api.state()
    expect(after.project_count).toBe(before.project_count)
    expect(after.shot_count).toBe(before.shot_count)
    expect(after.generation_attempt_count).toBe(before.generation_attempt_count)
    expect(after.handoff_count).toBe(before.handoff_count)
    expect(after.projects.some((p: { id: string }) => p.id === seeded.project_id)).toBe(true)
    expect(after.shots.some((s: { id: string }) => s.id === shot.id)).toBe(true)
    expect(
      after.generation_attempts.some(
        (g: { id: string }) => g.id === rendered.generation_attempt_id,
      ),
    ).toBe(true)
  })
})
