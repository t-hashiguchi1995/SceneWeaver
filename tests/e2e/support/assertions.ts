import { expect } from '@playwright/test'
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

const RUNTIME =
  process.env.SCENEWEAVER_RUNTIME_DIR ??
  path.resolve(process.cwd(), '../../runtime-e2e')

export function runtimePath(...parts: string[]): string {
  return path.join(RUNTIME, ...parts)
}

export async function expectFile(relativeOrAbsolute: string): Promise<void> {
  const full = path.isAbsolute(relativeOrAbsolute)
    ? relativeOrAbsolute
    : runtimePath(relativeOrAbsolute)
  await expect.poll(() => fs.existsSync(full), { timeout: 10_000 }).toBeTruthy()
}

export async function expectJsonFile(
  relativeOrAbsolute: string,
  predicate: (data: Record<string, unknown>) => boolean,
): Promise<void> {
  const full = path.isAbsolute(relativeOrAbsolute)
    ? relativeOrAbsolute
    : runtimePath(relativeOrAbsolute)
  await expect
    .poll(() => {
      if (!fs.existsSync(full)) return false
      const data = JSON.parse(fs.readFileSync(full, 'utf-8')) as Record<string, unknown>
      return predicate(data)
    })
    .toBeTruthy()
}

export function sha256File(filePath: string): string {
  const full = path.isAbsolute(filePath) ? filePath : runtimePath(filePath)
  return crypto.createHash('sha256').update(fs.readFileSync(full)).digest('hex')
}

export async function expectPanelMatchesAdopted(
  handoffPath: string,
  adoptedSha256: string,
): Promise<void> {
  const panel = path.join(handoffPath, 'pages', 'page_001', 'panel_01_clean.png')
  await expectFile(panel)
  expect(sha256File(panel)).toBe(adoptedSha256)
}
