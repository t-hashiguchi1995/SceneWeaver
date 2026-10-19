import { useSyncExternalStore } from 'react'

export type ActiveOperationStatus = 'queued' | 'running'

export type ActiveOperation = {
  id: string
  kind: string
  detail?: string
  progress?: number
  status: ActiveOperationStatus
}

let operations: ActiveOperation[] = []
const listeners = new Set<() => void>()

function emit() {
  for (const listener of listeners) listener()
}

export function startActiveOperation(op: ActiveOperation): () => void {
  operations = [...operations.filter((item) => item.id !== op.id), op]
  emit()
  return () => endActiveOperation(op.id)
}

export function updateActiveOperation(id: string, patch: Partial<ActiveOperation>): void {
  operations = operations.map((item) => (item.id === id ? { ...item, ...patch } : item))
  emit()
}

export function endActiveOperation(id: string): void {
  const next = operations.filter((item) => item.id !== id)
  if (next.length === operations.length) return
  operations = next
  emit()
}

export function getActiveOperations(): ActiveOperation[] {
  return operations
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useActiveOperations(): ActiveOperation[] {
  return useSyncExternalStore(subscribe, getActiveOperations, getActiveOperations)
}
