import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, useSearch } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  api,
  loadStudioContext,
  saveStudioContext,
  type DialogueCandidate,
} from '../lib/api'

export function StoryPage() {
  const { t } = useTranslation('story')
  const params = useParams({ strict: false })
  const search = useSearch({ strict: false }) as { sceneId?: string; beatId?: string }
  const qc = useQueryClient()
  const scopedProjectId = params.projectId
  const ctx = scopedProjectId
    ? {
        projectId: scopedProjectId,
        sceneId: search.sceneId,
        beatId: search.beatId,
        characterId: undefined as string | undefined,
        lockedEventId: undefined as string | undefined,
      }
    : loadStudioContext()
  const [projectId, setProjectId] = useState(ctx.projectId ?? '')
  const [characterId, setCharacterId] = useState(ctx.characterId ?? '')
  const [sceneTitle, setSceneTitle] = useState('Cafe')
  const [beatIntent, setBeatIntent] = useState('もう少し一緒にいたい')
  const [sceneId, setSceneId] = useState(ctx.sceneId ?? '')
  const [beatId, setBeatId] = useState(ctx.beatId ?? '')
  const [candidates, setCandidates] = useState<DialogueCandidate[]>([])
  const [lockedId, setLockedId] = useState(ctx.lockedEventId ?? '')
  const [status, setStatus] = useState('')
  const [creatingScene, setCreatingScene] = useState(false)
  const [creatingBeat, setCreatingBeat] = useState(false)

  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })
  const projects = useQuery({
    queryKey: ['projects'],
    queryFn: api.listProjects,
    enabled: !scopedProjectId,
  })

  const dashboard = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.projectDashboard(projectId),
    enabled: Boolean(projectId),
  })

  useEffect(() => {
    if (!dashboard.data) return
    const scene = dashboard.data.scenes.find((s) => s.id === sceneId) ?? dashboard.data.scenes[0]
    if (scene && !sceneId) setSceneId(scene.id)
    const beat =
      dashboard.data.beats.find((b) => b.id === beatId) ??
      dashboard.data.beats.find((b) => b.scene_id === scene?.id)
    if (beat && !beatId) {
      setBeatId(beat.id)
      setCharacterId(beat.speaker_id ?? '')
    }
    const events = dashboard.data.script_events.filter((e) => e.beat_id === (beatId || beat?.id))
    setCandidates(events.filter((e) => !e.locked))
    setLockedId(events.find((e) => e.locked)?.id ?? '')
  }, [dashboard.data, sceneId, beatId])

  const refresh = () => void qc.invalidateQueries({ queryKey: ['project-dashboard', projectId] })

  const scenes = dashboard.data?.scenes ?? []
  const beats = (dashboard.data?.beats ?? []).filter((b) => b.scene_id === sceneId)
  const selectedScene = scenes.find((s) => s.id === sceneId)
  const selectedBeat = beats.find((b) => b.id === beatId)
  const previousBeat = useMemo(() => {
    if (!selectedBeat) return null
    const index = beats.findIndex((b) => b.id === selectedBeat.id)
    return index > 0 ? beats[index - 1] : null
  }, [beats, selectedBeat])
  const lockedText = dashboard.data?.script_events.find((e) => e.id === lockedId)?.text
  const inheritedLocked = previousBeat
    ? dashboard.data?.script_events.find((e) => e.beat_id === previousBeat.id && e.locked)?.text
    : undefined

  const createScene = useMutation({
    mutationFn: () => api.createScene(projectId, sceneTitle, 'stay together'),
    onSuccess: (scene) => {
      setSceneId(scene.id)
      saveStudioContext({ projectId, sceneId: scene.id })
      setBeatId('')
      setLockedId('')
      setCandidates([])
      setCreatingScene(false)
      refresh()
      setStatus(t('sceneCreated', { title: scene.title }))
    },
  })

  const createBeat = useMutation({
    mutationFn: () => api.createBeat(sceneId, beatIntent, characterId || undefined),
    onSuccess: (beat) => {
      setBeatId(beat.id)
      saveStudioContext({ beatId: beat.id, characterId })
      setCreatingBeat(false)
      refresh()
      setStatus(t('beatCreated', { intent: beat.intent }))
    },
  })

  const generate = useMutation({
    mutationFn: () => api.generateDialogue(beatId, characterId),
    onSuccess: (result) => {
      setCandidates(result.candidates)
      refresh()
      setStatus(t('candidatesReady'))
    },
    onError: (err) => setStatus((err as Error).message),
  })

  const lock = useMutation({
    mutationFn: (c: DialogueCandidate) => api.lockScript(c.id, c.text),
    onSuccess: (locked) => {
      setLockedId(locked.id)
      saveStudioContext({
        lockedEventId: locked.id,
        lockedText: locked.text,
        beatId,
        characterId,
        sceneId,
        projectId,
      })
      refresh()
      setStatus(t('scriptLocked'))
    },
  })

  return (
    <section className="page" data-testid="story-page">
      <h1>{t('title')}</h1>
      <p className="lede">{t('lede')}</p>

      <div className="story-columns">
        <div className="stack panel-card studio-form">
          {!scopedProjectId && (
            <label>
              {t('project')}
              <select
                aria-label={t('project')}
                data-testid="story-project-select"
                value={projectId}
                onChange={(e) => {
                  setSceneId('')
                  setBeatId('')
                  setCandidates([])
                  setLockedId('')
                  setProjectId(e.target.value)
                  saveStudioContext({ projectId: e.target.value })
                }}
              >
                <option value="">{t('selectProject')}</option>
                {(projects.data ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label>
            {t('character')}
            <select
              aria-label={t('character')}
              data-testid="story-character-select"
              value={characterId}
              onChange={(e) => {
                const id = e.target.value
                setCharacterId(id)
                const name = characters.data?.find((c) => c.id === id)?.display_name
                saveStudioContext({ characterId: id, characterName: name })
              }}
            >
              <option value="">{t('selectCharacter')}</option>
              {(characters.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.display_name}
                </option>
              ))}
            </select>
          </label>

          <div>
            <h3>{t('scenesNav')}</h3>
            <ul className="story-nav-list" data-testid="story-scene-nav">
              {scenes.map((scene) => (
                <li key={scene.id}>
                  <button
                    type="button"
                    className={scene.id === sceneId ? 'btn primary' : 'btn'}
                    data-testid={`story-scene-${scene.id}`}
                    onClick={() => {
                      setSceneId(scene.id)
                      setBeatId('')
                      setCandidates([])
                      setLockedId('')
                      setCreatingScene(false)
                    }}
                  >
                    {scene.title}
                  </button>
                </li>
              ))}
            </ul>
            {/* Keep select for e2e / accessibility parity with existing flows */}
            <label className="visually-hidden">
              {t('sceneTitle')}
              <select
                data-testid="story-scene-select"
                value={sceneId}
                onChange={(e) => {
                  setSceneId(e.target.value)
                  setBeatId('')
                  setCandidates([])
                  setLockedId('')
                }}
              >
                <option value="">—</option>
                {scenes.map((scene) => (
                  <option key={scene.id} value={scene.id}>
                    {scene.title}
                  </option>
                ))}
              </select>
            </label>
            {!creatingScene ? (
              <button
                type="button"
                className="btn"
                data-testid="story-add-scene"
                onClick={() => setCreatingScene(true)}
              >
                {t('addScene')}
              </button>
            ) : (
              <div className="inline-form">
                <input
                  aria-label={t('sceneTitle')}
                  data-testid="story-scene-title"
                  value={sceneTitle}
                  onChange={(e) => setSceneTitle(e.target.value)}
                />
                <button
                  type="button"
                  className="btn primary"
                  data-testid="story-create-scene"
                  disabled={!projectId || createScene.isPending}
                  onClick={() => createScene.mutate()}
                >
                  {t('createScene')}
                </button>
              </div>
            )}
          </div>

          <div>
            <h3>{t('beatsNav')}</h3>
            <ul className="story-nav-list" data-testid="story-beat-nav">
              {beats.map((beat) => (
                <li key={beat.id}>
                  <button
                    type="button"
                    className={beat.id === beatId ? 'btn primary' : 'btn'}
                    onClick={() => {
                      setBeatId(beat.id)
                      setCharacterId(beat.speaker_id ?? '')
                      setCreatingBeat(false)
                    }}
                  >
                    {beat.intent}
                  </button>
                </li>
              ))}
            </ul>
            <label className="visually-hidden">
              {t('beatIntent')}
              <select
                data-testid="story-beat-select"
                value={beatId}
                onChange={(e) => {
                  setBeatId(e.target.value)
                  const beat = dashboard.data?.beats.find((b) => b.id === e.target.value)
                  setCharacterId(beat?.speaker_id ?? '')
                }}
              >
                <option value="">—</option>
                {beats.map((beat) => (
                  <option key={beat.id} value={beat.id}>
                    {beat.intent}
                  </option>
                ))}
              </select>
            </label>
            {!creatingBeat ? (
              <button
                type="button"
                className="btn"
                data-testid="story-add-beat"
                disabled={!sceneId}
                onClick={() => setCreatingBeat(true)}
              >
                {t('addBeat')}
              </button>
            ) : (
              <div className="inline-form">
                <input
                  aria-label={t('beatIntent')}
                  data-testid="story-beat-intent"
                  value={beatIntent}
                  onChange={(e) => setBeatIntent(e.target.value)}
                />
                <button
                  type="button"
                  className="btn primary"
                  data-testid="story-create-beat"
                  disabled={!sceneId || createBeat.isPending}
                  onClick={() => createBeat.mutate()}
                >
                  {t('createBeat')}
                </button>
              </div>
            )}
          </div>

          {(selectedScene || selectedBeat || inheritedLocked) && (
            <p className="meta" data-testid="story-context">
              {selectedScene ? t('contextScene', { title: selectedScene.title }) : ''}
              {selectedBeat ? ` · ${t('contextBeat', { intent: selectedBeat.intent })}` : ''}
              {inheritedLocked ? ` · ${t('contextInherited')}` : ''}
            </p>
          )}
          {inheritedLocked && (
            <p className="lede" data-testid="story-inherited-line">
              {inheritedLocked}
            </p>
          )}

          <button
            type="button"
            className="btn primary"
            data-testid="story-generate-dialogue"
            disabled={!beatId || !characterId || generate.isPending}
            onClick={() => generate.mutate()}
          >
            {t('generateDialogue')}
          </button>
        </div>

        <div className="panel-card">
          {status && (
            <p className="hint" data-testid="story-status">
              {status}
            </p>
          )}

          <ul className="list" data-testid="dialogue-candidate-list">
            {candidates.map((c, index) => (
              <li key={c.id} data-testid={`dialogue-candidate-${index}`}>
                <label>
                  {t('editDialogue')}
                  <textarea
                    aria-label={t('editDialogue')}
                    value={c.text}
                    onChange={(e) =>
                      setCandidates((previous) =>
                        previous.map((candidate) =>
                          candidate.id === c.id
                            ? { ...candidate, text: e.target.value }
                            : candidate,
                        ),
                      )
                    }
                  />
                </label>
                <p className="meta">{c.tone}</p>
                <button
                  type="button"
                  className="btn"
                  data-testid={`dialogue-lock-${index}`}
                  onClick={() => lock.mutate(c)}
                >
                  {t('lockCandidate', { n: index + 1 })}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <aside className="panel-card">
          <h2>{t('lockedBanner')}</h2>
          {lockedId ? (
            <p data-testid="story-locked-banner">{t('lockedBanner')}</p>
          ) : (
            <p className="meta">{t('lockedEmpty')}</p>
          )}
          <p>{lockedText}</p>
          {(sceneId || beatId) && (
            <details className="meta technical-details">
              <summary>{t('technicalInfo')}</summary>
              <p className="meta" data-testid="story-ids">
                scene={sceneId || '—'} beat={beatId || '—'}
              </p>
              {lockedId && <p className="meta">event={lockedId}</p>}
            </details>
          )}
        </aside>
      </div>
    </section>
  )
}
