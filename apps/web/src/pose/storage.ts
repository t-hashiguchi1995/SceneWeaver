import type { SelectedPose } from './types'
import { findPoseCard } from './catalog'

const FAV_KEY = 'sceneweaver.pose.favorites'
const RECENT_KEY = 'sceneweaver.pose.recent'
const SELECTED_KEY = 'sceneweaver.pose.selected'

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function loadFavoritePoseIds(): Set<string> {
  return new Set(readJson<string[]>(FAV_KEY, []))
}

export function toggleFavoritePose(id: string): Set<string> {
  const next = loadFavoritePoseIds()
  if (next.has(id)) next.delete(id)
  else next.add(id)
  localStorage.setItem(FAV_KEY, JSON.stringify([...next]))
  return next
}

export function loadRecentPoseIds(): string[] {
  return readJson<string[]>(RECENT_KEY, [])
}

export function pushRecentPose(id: string): string[] {
  const prev = loadRecentPoseIds().filter((x) => x !== id)
  const next = [id, ...prev].slice(0, 12)
  localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  return next
}

export function loadSelectedPose(): SelectedPose | null {
  const raw = readJson<SelectedPose | null>(SELECTED_KEY, null)
  if (!raw?.card?.id) return null
  const card = findPoseCard(raw.card.id)
  if (!card) return raw
  return { ...raw, card }
}

export function saveSelectedPose(selected: SelectedPose | null): void {
  if (!selected) {
    localStorage.removeItem(SELECTED_KEY)
    return
  }
  localStorage.setItem(SELECTED_KEY, JSON.stringify(selected))
  pushRecentPose(selected.card.id)
}
