import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type Character } from '../../lib/api'
import { useCharacterAutosave } from '../../hooks/useCharacterAutosave'
import { AssetImage } from '../../components/AssetImage'

export const Route = createFileRoute('/characters/$characterId')({ component: CharacterPage })
function CharacterPage() {
  const { characterId } = Route.useParams()
  const { t } = useTranslation('common')
  const query = useQuery({ queryKey: ['character', characterId], queryFn: () => api.getCharacter(characterId) })
  if (query.error) return <p role="alert">{query.error.message}</p>
  if (!query.data) return <p>{t('loading')}</p>
  return <CharacterEditor key={characterId} character={query.data} />
}
function CharacterEditor({ character }: { character: Character }) {
  const { t } = useTranslation(['character', 'common'])
  const [tab, setTab] = useState<'persona' | 'visual_identity'>('persona')
  const [persona, setPersona] = useState(character.persona)
  const [visual, setVisual] = useState(character.visual_identity)
  const data = tab === 'persona' ? persona : visual
  const update = (key: string, value: unknown) => tab === 'persona' ? setPersona({ ...persona, [key]: value }) : setVisual({ ...visual, [key]: value })
  const save = useCharacterAutosave(character.id, persona, visual)
  const keys = tab === 'persona' ? ['first_person', 'second_person', 'max_chars', 'max_fragments', 'forbidden_patterns'] : ['hair', 'eyes', 'body', 'identity_tags', 'identity_ref_asset_ids', 'tryon_base_asset_id']
  return <section className="page" data-testid="character-editor">
    <h1>{character.display_name}</h1>
    <div className="cta-row" role="tablist" aria-label={t('character:editor')}>
      {(['persona', 'visual_identity'] as const).map((value) => <button role="tab" aria-selected={tab === value} className={tab === value ? 'btn primary' : 'btn'} key={value} onClick={() => setTab(value)}>{t(`character:${value}`)}</button>)}
    </div>
    <form className="stack-form panel-card" onSubmit={(e) => { e.preventDefault(); void save.flush().catch(() => undefined) }}>
      {keys.map((key) => <label key={key}>{t(`character:fields.${key}`)}
        {typeof data[key] === 'number' ? <input type="number" min={1} value={Number(data[key])} onChange={(e) => update(key, Number(e.target.value))} /> :
          <input data-testid={`character-field-${key}`} value={Array.isArray(data[key]) ? (data[key] as string[]).join(', ') : String(data[key] ?? '')} onChange={(e) => update(key, Array.isArray(data[key]) ? e.target.value.split(',').map((x) => x.trim()).filter(Boolean) : e.target.value || (key === 'tryon_base_asset_id' ? null : ''))} />}
      </label>)}
      {tab === 'persona' && <>
        <label>{t('character:speechRules')}<textarea value={String((persona.speech_rules as Record<string, unknown>)?.style ?? '')} onChange={(e) => setPersona({ ...persona, speech_rules: { ...(persona.speech_rules as object), style: e.target.value } })} /></label>
        <label>{t('character:voiceExamples')}<textarea value={((persona.voice_examples ?? []) as { text?: string }[]).map((example) => example.text ?? '').join('\n')} onChange={(e) => setPersona({ ...persona, voice_examples: e.target.value.split('\n').filter(Boolean).map((text) => ({ text })) })} /></label>
      </>}
      {tab === 'visual_identity' && <div className="candidate-grid">{((visual.identity_ref_asset_ids ?? []) as string[]).map((id) => <AssetImage key={id} assetId={id} alt={character.display_name} />)}</div>}
      <button className="btn primary" disabled={save.status === 'saving'} data-testid="character-save">{t('common:actions.save')}</button>
      <p role="status">{t(`common:${save.status}`)}</p>
      {save.error && <p role="alert">{save.error}</p>}
    </form>
  </section>
}
