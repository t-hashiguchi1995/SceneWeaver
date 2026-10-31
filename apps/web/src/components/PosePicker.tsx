import { useTranslation } from 'react-i18next'

import type { SelectedPose } from '../pose/types'

export type PosePickerProps = {
  selected: SelectedPose | null
  onChoose: () => void
  onClear: () => void
}

export function PosePicker(props: PosePickerProps) {
  const { t } = useTranslation('generation')
  const { selected } = props

  return (
    <section className="pose-picker panel-card" data-testid="pose-picker">
      <div className="row-between">
        <h3>{t('poseGallery.sectionTitle')}</h3>
        <p className="meta">{t('poseGallery.characterAgnosticHint')}</p>
      </div>

      {!selected ? (
        <div className="pose-picker-empty">
          <button type="button" className="btn primary" data-testid="pose-choose" onClick={props.onChoose}>
            {t('poseGallery.choosePose')}
          </button>
          <p className="meta">{t('poseGallery.emptyHint')}</p>
        </div>
      ) : (
        <div className="pose-picker-selected" data-testid="pose-selected">
          <img src={selected.card.thumbUrl} alt="" className="pose-picker-thumb" />
          <div className="pose-picker-meta">
            <strong data-testid="pose-selected-title">{selected.card.title}</strong>
            <p className="meta" data-testid="pose-selected-view">
              {selected.poseId} / {selected.poseView}
            </p>
            <p className="meta" data-testid="pose-selected-strength">
              {t('poseGallery.strength')}: {selected.strength.toFixed(2)}
              {selected.flipHorizontal ? ` · ${t('poseGallery.flipped')}` : ''}
            </p>
            <p className="meta pose-picker-prompt" title={selected.card.posePrompt}>
              {selected.card.posePrompt}
            </p>
            <div className="cta-row">
              <button type="button" className="btn primary" data-testid="pose-change" onClick={props.onChoose}>
                {t('poseGallery.change')}
              </button>
              <button type="button" className="btn" data-testid="pose-clear" onClick={props.onClear}>
                {t('poseGallery.clear')}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
