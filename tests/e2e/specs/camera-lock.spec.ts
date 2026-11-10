import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '../fixtures/sceneweaver.fixture'
import { type ApiClient, type SeedResult } from '../support/api-client'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
async function plan(api: ApiClient, seed: SeedResult) {
  const shotIds: string[] = []
  for (const beatId of seed.extras!.beat_ids as string[]) shotIds.push((await api.planShot(beatId)).id)
  return { shotIds, projectId: seed.project_id!, assetId: seed.extras!.anchor_asset_id as string }
}
async function anchored(api: ApiClient, projectId: string, assetId: string) {
  const rig = await api.createCameraRig(projectId, { name: 'Studio rig', frame: { width: 1536, height: 864 }, face_policy: 'partial_allowed' })
  const anchor = await api.registerCameraAnchor(rig.id, assetId)
  expect(anchor.status).toBe(200)
  return { rig, anchor: anchor.body }
}

test.describe('Camera lock Gate 1', () => {
  test('anchor + bind shots 01-10 to one rig', async ({ api, page, cameraLock, seedScenario, applySeedContext }) => {
    const seed = await seedScenario('camera_lock')
    const { shotIds, projectId, assetId } = await plan(api, seed)
    await applySeedContext(seed)
    await page.goto(`/projects/${projectId}/shots/${shotIds[0]}`)
    await cameraLock.createRig('Ten shots', 'partial_allowed')
    await expect(cameraLock.rigStatus).toContainText('Ten shots')
    await cameraLock.registerAnchorById(assetId)
    await expect(cameraLock.anchorInfo).toBeVisible()
    await cameraLock.bindCurrentShot('full_visible')
    await expect(cameraLock.bindingState).toContainText('Ten shots')
    const [rig] = await api.listCameraRigs(projectId)
    const firstBinding = await api.getShotCameraBinding(shotIds[0])
    const asset = await fetch(`${api.baseUrl}/api/v1/assets/${rig.anchor_asset_id}`).then(r => r.json())
    expect(firstBinding.anchor_asset_sha256).toBe(asset.sha256)
    for (const shotId of shotIds.slice(1)) await api.bindShotCamera(shotId, { camera_rig_id: rig.id, face_policy: 'full_visible' })
    for (const shotId of shotIds) {
      const binding = await api.getShotCameraBinding(shotId)
      expect(binding.rig_id).toBe(rig.id)
      expect(binding.anchor_asset_sha256).toBe(asset.sha256)
    }
    await page.goto(`/projects/${projectId}/shots/${shotIds[1]}`)
    await expect(cameraLock.bindingState).toContainText('Ten shots')
    await cameraLock.renderWithLock()
    await expect(page.getByTestId('camera-lock-unavailable')).toBeVisible()
  })

  test('rig edit does not mutate attempts; stale is shown', async ({ api, page, cameraLock, seedScenario, applySeedContext }) => {
    const seed = await seedScenario('camera_lock')
    const { shotIds, projectId, assetId } = await plan(api, seed)
    const { rig } = await anchored(api, projectId, assetId)
    await api.bindShotCamera(shotIds[0], { camera_rig_id: rig.id, face_policy: 'full_visible' })
    const rendered = await api.renderShot(shotIds[0])
    const id = rendered.generation_attempt_id
    const before = await api.getGenerationAttempt(id)
    expect(before.camera_stale).toBe(false)
    expect(before.payload.camera_rig_revision).toBe(1)
    await applySeedContext(seed)
    await page.goto(`/projects/${projectId}/shots/${shotIds[0]}`)
    await expect(page.getByTestId(`camera-attempt-${id}`)).toBeVisible()
    await expect(page.getByTestId(`camera-attempt-stale-${id}`)).toHaveCount(0)
    await cameraLock.lockRig()
    await expect(cameraLock.rigStatus).toContainText('LOCKED')
    await expect(page.getByTestId(`camera-attempt-stale-${id}`)).toBeVisible()
    const after = await api.getGenerationAttempt(id)
    expect(after.camera_stale).toBe(true)
    expect(after.payload.camera_rig_revision).toBe(1)
    let apiCalls = 0
    page.on('request', request => { if (request.url().includes('/api/')) apiCalls++ })
    await page.getByTestId(`camera-attempt-regenerate-${id}`).click()
    await expect(page.getByTestId('camera-regenerate-notice')).toBeVisible()
    expect(apiCalls).toBe(0)
  })

  test('anchor-invalid cannot be adopted', async ({ api, page, cameraLock, seedScenario, applySeedContext }) => {
    const seed = await seedScenario('camera_lock')
    const { shotIds, projectId, assetId } = await plan(api, seed)
    await applySeedContext(seed)
    await page.goto(`/projects/${projectId}/shots/${shotIds[0]}`)
    await cameraLock.createRig('Full face', 'full_visible')
    await expect(cameraLock.rigStatus).toContainText('Full face')
    await cameraLock.registerAnchorById(assetId)
    await expect(cameraLock.faceWarning).toBeVisible()
    const [rig] = await api.listCameraRigs(projectId)
    expect((await api.getCameraRig(rig.id)).anchor_asset_id).toBeNull()
    const rejected = await api.registerCameraAnchor(rig.id, assetId)
    expect(rejected.status).toBe(422)
    expect(rejected.body.detail.code).toBe('ANCHOR_FACE_INVALID')
    await expect(cameraLock.bindButton).toBeDisabled()
  })

  test('state persists across API restart', async ({ api, page, cameraLock, seedScenario, applySeedContext }) => {
    const seed = await seedScenario('camera_lock')
    const { shotIds, projectId, assetId } = await plan(api, seed)
    const { rig } = await anchored(api, projectId, assetId)
    for (const shotId of shotIds.slice(0, 2)) await api.bindShotCamera(shotId, { camera_rig_id: rig.id, face_policy: 'full_visible' })
    const rendered = await api.renderShot(shotIds[0])
    const beforeRig = await api.getCameraRig(rig.id)
    const beforeBindings = await Promise.all(shotIds.slice(0, 2).map(id => api.getShotCameraBinding(id)))
    const beforeAttempt = await api.getGenerationAttempt(rendered.generation_attempt_id)
    await applySeedContext(seed)
    await page.goto(`/projects/${projectId}/shots/${shotIds[0]}`)
    await expect(cameraLock.bindingState).toContainText(rig.name)
    execFileSync('bash', [path.join(root, 'scripts/e2e/restart-api-worker.sh'), 'e2e'], {
      cwd: root,
      env: {
        ...process.env,
        SCENEWEAVER_RUNTIME_DIR: process.env.SCENEWEAVER_RUNTIME_DIR ?? path.join(root, 'runtime-e2e'),
        SCENEWEAVER_PORT: process.env.SCENEWEAVER_PORT ?? '8010',
        SCENEWEAVER_CORS_ORIGINS: process.env.SCENEWEAVER_CORS_ORIGINS ?? 'http://127.0.0.1:5174,http://localhost:5174',
        SCENEWEAVER_FAKE_IMAGE_DELAY_MS: process.env.SCENEWEAVER_FAKE_IMAGE_DELAY_MS ?? '400',
      },
      stdio: 'inherit',
    })
    let health: Record<string, string> | null = null
    for (let i = 0; i < 20; i++) {
      try { health = await api.health(); break } catch { await new Promise(r => setTimeout(r, 250)) }
    }
    expect(health?.environment).toBe('e2e')
    const afterRig = await api.getCameraRig(rig.id)
    expect({ id: afterRig.id, revision: afterRig.revision, anchor_asset_id: afterRig.anchor_asset_id }).toEqual({ id: beforeRig.id, revision: beforeRig.revision, anchor_asset_id: beforeRig.anchor_asset_id })
    expect(await Promise.all(shotIds.slice(0, 2).map(id => api.getShotCameraBinding(id)))).toEqual(beforeBindings)
    expect((await api.getGenerationAttempt(rendered.generation_attempt_id)).camera_stale).toBe(beforeAttempt.camera_stale)
    await page.reload()
    await expect(cameraLock.rigStatus).toContainText(rig.name)
    await expect(cameraLock.bindingState).toContainText(rig.name)
  })

  test('390px viewport operable', async ({ api, page, cameraLock, seedScenario, applySeedContext }) => {
    const seed = await seedScenario('camera_lock')
    const { shotIds, projectId, assetId } = await plan(api, seed)
    const { rig } = await anchored(api, projectId, assetId)
    const other = await api.createCameraRig(projectId, { name: 'Second rig', frame: { width: 1536, height: 864 }, face_policy: 'partial_allowed' })
    await applySeedContext(seed)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`/projects/${projectId}/shots/${shotIds[0]}`)
    await expect(cameraLock.panel).toBeVisible()
    await expect(cameraLock.rigSelect).toBeVisible()
    await cameraLock.rigSelect.selectOption(other.id)
    await expect(cameraLock.rigStatus).toContainText(other.name)
    await cameraLock.rigSelect.selectOption(rig.id)
    await expect(cameraLock.rigStatus).toContainText(rig.name)
  })
})
