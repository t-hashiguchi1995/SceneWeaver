import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

export type PromptEditorProps = {
  templateLabel: string
  sourceKind: string
  templateSource?: string
  /** Compiler output (Anima tag sequence or MOSS caption) — read-only Base. */
  renderedBasePositive: string
  renderedBaseNegative: string
  /** User-editable Final Prompt. */
  editedPositive: string
  editedNegative: string
  modifiedPositive: boolean
  modifiedNegative: boolean
  stale: boolean
  components?: { ref: string; kind: string; text: string }[]
  warnings?: string[]
  saveStatus?: string
  generateDisabled?: boolean
  /** When set, show "Save as character prompt" (Gate 2.6 adopt). */
  canSaveCharacterPrompt?: boolean
  saveCharacterPromptStatus?: string
  onPositiveChange: (value: string) => void
  onNegativeChange: (value: string) => void
  onResetEdits: () => void
  onRebuild: () => void
  onGenerate: () => void
  onDismissStale?: () => void
  onSaveCharacterPrompt?: () => void
}

function tokenDiff(base: string, edited: string): string[] {
  const a = base.split(/[,\n]/).map((x) => x.trim()).filter(Boolean)
  const b = edited.split(/[,\n]/).map((x) => x.trim()).filter(Boolean)
  const before = new Set(a)
  const after = new Set(b)
  return [
    ...a.filter((x) => !after.has(x)).map((x) => `- ${x}`),
    ...b.filter((x) => !before.has(x)).map((x) => `+ ${x}`),
  ]
}

export function PromptEditor(props: PromptEditorProps) {
  const { t } = useTranslation('prompt')
  const [tab, setTab] = useState<'rendered' | 'components' | 'source'>('rendered')
  const [showDiff, setShowDiff] = useState(false)
  const modified = props.modifiedPositive || props.modifiedNegative

  const diffLines = useMemo(() => {
    const pos = tokenDiff(props.renderedBasePositive, props.editedPositive)
    const neg = tokenDiff(props.renderedBaseNegative, props.editedNegative)
    return { pos, neg }
  }, [
    props.renderedBasePositive,
    props.editedPositive,
    props.renderedBaseNegative,
    props.editedNegative,
  ])

  return (
    <section className="prompt-editor panel-card" data-testid="prompt-editor">
      <div className="row-between">
        <h2>{t('title')}</h2>
        <span className="meta" data-testid="prompt-template-label">
          {props.templateLabel} · {modified ? t('stateEdited') : t('statePristine')}
          {props.stale ? ` · ${t('stateStale')}` : ''}
        </span>
      </div>

      <p role="status" aria-live="polite" data-testid="prompt-save-status">
        {props.saveStatus}
      </p>
      {props.stale && (
        <div className="banner" data-testid="prompt-stale-banner">
          <p>{t('staleBanner')}</p>
          <div className="cta-row">
            <button type="button" className="btn primary" data-testid="prompt-rebuild" onClick={props.onRebuild}>
              {t('rebuild')}
            </button>
            <button
              type="button"
              className="btn"
              data-testid="prompt-keep-stale"
              onClick={props.onDismissStale}
            >
              {t('keep')}
            </button>
          </div>
        </div>
      )}

      <div className="cta-row">
        <button
          type="button"
          className={tab === 'rendered' ? 'btn primary' : 'btn'}
          data-testid="prompt-tab-rendered"
          onClick={() => setTab('rendered')}
        >
          {t('tabRendered')}
        </button>
        <button
          type="button"
          className={tab === 'source' ? 'btn primary' : 'btn'}
          data-testid="prompt-tab-source"
          onClick={() => setTab('source')}
        >
          {t('tabSource')}
        </button>
        <button
          type="button"
          className={tab === 'components' ? 'btn primary' : 'btn'}
          data-testid="prompt-tab-components"
          onClick={() => setTab('components')}
        >
          {t('tabComponents')}
        </button>
      </div>
      {props.warnings?.map((warning) => (
        <p className="hint" key={warning}>
          {warning}
        </p>
      ))}

      {tab === 'components' ? (
        <ul className="list">
          {props.components?.map((component) => (
            <li key={component.ref}>
              <code>{component.ref}</code>
              <span>{component.text}</span>
            </li>
          ))}
        </ul>
      ) : tab === 'source' ? (
        <pre className="lede" data-testid="prompt-source-body">
          {props.templateSource || props.sourceKind}
        </pre>
      ) : (
        <div className="stack">
          <label>
            {t('basePositive')}
            <textarea
              data-testid="prompt-base-positive"
              rows={5}
              readOnly
              value={props.renderedBasePositive}
            />
          </label>
          <label>
            {t('finalPositive')}
            <textarea
              data-testid="prompt-positive"
              rows={8}
              value={props.editedPositive}
              onChange={(e) => props.onPositiveChange(e.target.value)}
            />
          </label>
          <label>
            {t('baseNegative')}
            <textarea
              data-testid="prompt-base-negative"
              rows={3}
              readOnly
              value={props.renderedBaseNegative}
            />
          </label>
          <label>
            {t('finalNegative')}
            <textarea
              data-testid="prompt-negative"
              rows={4}
              value={props.editedNegative}
              onChange={(e) => props.onNegativeChange(e.target.value)}
            />
          </label>
        </div>
      )}

      {showDiff && (
        <div data-testid="prompt-diff">
          <h3>{t('diffTitle')}</h3>
          <pre className="lede">
            {[...diffLines.pos, ...diffLines.neg].join('\n') || '(no changes)'}
          </pre>
        </div>
      )}

      <div className="cta-row">
        <button type="button" className="btn" data-testid="prompt-reset-edits" onClick={props.onResetEdits}>
          {t('resetEdits')}
        </button>
        <button
          type="button"
          className="btn"
          data-testid="prompt-toggle-diff"
          onClick={() => setShowDiff((v) => !v)}
        >
          {showDiff ? t('hideDiff') : t('showDiff')}
        </button>
        {!props.stale && (
          <button type="button" className="btn" data-testid="prompt-rebuild" onClick={props.onRebuild}>
            {t('rebuild')}
          </button>
        )}
        {props.canSaveCharacterPrompt && props.onSaveCharacterPrompt && (
          <button
            type="button"
            className="btn"
            data-testid="prompt-save-character"
            onClick={props.onSaveCharacterPrompt}
          >
            {t('saveCharacterPrompt')}
          </button>
        )}
        <button
          type="button"
          className="btn primary"
          data-testid="shot-generate"
          disabled={props.generateDisabled}
          onClick={props.onGenerate}
        >
          {t('generate')}
        </button>
      </div>
      {props.saveCharacterPromptStatus ? (
        <p className="meta" data-testid="prompt-save-character-status">
          {props.saveCharacterPromptStatus}
        </p>
      ) : null}
    </section>
  )
}
