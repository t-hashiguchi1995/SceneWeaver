import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

export type PromptEditorProps = {
  templateLabel: string
  sourceKind: string
  templateSource?: string
  renderedBasePositive: string
  renderedBaseNegative: string
  editedPositive: string
  editedNegative: string
  modifiedPositive: boolean
  modifiedNegative: boolean
  stale: boolean
  generateDisabled?: boolean
  onPositiveChange: (value: string) => void
  onNegativeChange: (value: string) => void
  onResetEdits: () => void
  onRebuild: () => void
  onGenerate: () => void
  onDismissStale?: () => void
}

function lineDiff(base: string, edited: string): string[] {
  const a = base.split('\n')
  const b = edited.split('\n')
  const max = Math.max(a.length, b.length)
  const lines: string[] = []
  for (let i = 0; i < max; i += 1) {
    const left = a[i]
    const right = b[i]
    if (left === right) continue
    if (left != null && right == null) lines.push(`- ${left}`)
    else if (left == null && right != null) lines.push(`+ ${right}`)
    else {
      lines.push(`- ${left}`)
      lines.push(`+ ${right}`)
    }
  }
  return lines
}

export function PromptEditor(props: PromptEditorProps) {
  const { t } = useTranslation('prompt')
  const [tab, setTab] = useState<'rendered' | 'source'>('rendered')
  const [showDiff, setShowDiff] = useState(false)
  const modified = props.modifiedPositive || props.modifiedNegative

  const diffLines = useMemo(() => {
    const pos = lineDiff(props.renderedBasePositive, props.editedPositive)
    const neg = lineDiff(props.renderedBaseNegative, props.editedNegative)
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
      </div>

      {tab === 'source' ? (
        <pre className="lede" data-testid="prompt-source-body">
          {props.templateSource || props.sourceKind}
        </pre>
      ) : (
        <div className="stack">
          <label>
            {t('positive')}
            <textarea
              data-testid="prompt-positive"
              rows={8}
              value={props.editedPositive}
              onChange={(e) => props.onPositiveChange(e.target.value)}
            />
          </label>
          <label>
            {t('negative')}
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
    </section>
  )
}
