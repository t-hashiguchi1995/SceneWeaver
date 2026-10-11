import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('M1 Foundation', () => {
  test.beforeEach(async ({ api }) => {
    await api.reset()
  })

  test('project create, job SSE Running→Succeeded, capabilities via UI', async ({
    page,
    home,
    projects,
    jobs,
    api,
  }) => {
    const health = await api.health()
    expect(health.environment).toBe('e2e')

    await home.goto()
    await expect(page.getByRole('heading', { name: '制作を続けましょう' })).toBeVisible()

    await home.openProjects()
    await projects.create('E2E Project Alpha')
    await expect(projects.projectLink('E2E Project Alpha')).toBeVisible()

    await home.openJobs()
    await jobs.enqueueStub()
    // Worker holds RUNNING long enough for SSE → UI (see worker stub delay).
    await expect(jobs.liveStatus()).toHaveText('処理中', { timeout: 20_000 })
    await expect(jobs.liveStatus()).toHaveText('完了', { timeout: 20_000 })
    await expect(page.getByTestId('job-live-status')).toBeVisible()

    const state = await api.state()
    expect(state.project_count).toBeGreaterThanOrEqual(1)
    expect(state.job_count).toBeGreaterThanOrEqual(1)
  })
})
