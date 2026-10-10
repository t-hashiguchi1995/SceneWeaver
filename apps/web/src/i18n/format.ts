import type { TFunction } from 'i18next'

const ERROR_CODES = [
  'COMFY_UNREACHABLE',
  'MODEL_NOT_FOUND',
  'CUSTOM_NODE_MISSING',
  'WORKFLOW_INVALID',
  'SUBMIT_FAILED',
  'GENERATION_FAILED',
  'OUTPUT_NOT_FOUND',
  'TIMEOUT',
] as const

export type KnownErrorCode = (typeof ERROR_CODES)[number]

export function formatStatus(t: TFunction, status: string): string {
  const key = `status.${status}`
  const translated = t(key, { ns: 'common', defaultValue: '' })
  return translated || status
}

export function parseErrorCode(message: string): KnownErrorCode | null {
  const match = message.match(/\b([A-Z][A-Z0-9_]+)\b/)
  if (!match) return null
  const code = match[1] as KnownErrorCode
  return (ERROR_CODES as readonly string[]).includes(code) ? code : null
}

export function formatErrorMessage(t: TFunction, message: string): string {
  const code = parseErrorCode(message)
  if (!code) return message || t('errors.generic', { ns: 'common' })
  return t(`errors.${code}`, { ns: 'common' })
}

export function formatDateTime(value: string | null | undefined, locale: string): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const tag = locale.startsWith('en') ? 'en-US' : 'ja-JP'
  return new Intl.DateTimeFormat(tag, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}
