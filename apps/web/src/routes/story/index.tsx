import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import {
  api,
  loadStudioContext,
  saveStudioContext,
  type DialogueCandidate,
} from '../../lib/api'

export const Route = createFileRoute('/story/')({
  component: StoryPage,
})

function StoryPage() {
  const ctx = loadStudioContext()
  const [projectId, setProjectId] = useState(ctx.projectId ?? '')
  const [characterId, setCharacterId] = useState(ctx.characterId ?? '')
  const [sceneTitle, setSceneTitle] = useState('Cafe')
  const [beatIntent, setBeatIntent] = useState('もう少し一緒にいたい')
  const [sceneId, setSceneId] = useState(ctx.sceneId ?? '')
  const [beatId, setBeatId] = useState(ctx.beatId ?? '')
  const [candidates, setCandidates] = useState<DialogueCandidate[]>([])
  const [lockedId, setLockedId] = useState(ctx.lockedEventId ?? '')
  const [status, setStatus] = useState('')

  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.listProjects })

  const createScene = useMutation({
    mutationFn: () => api.createScene(projectId, sceneTitle, 'stay together'),
    onSuccess: (scene) => {
      setSceneId(scene.id)
      saveStudioContext({ projectId, sceneId: scene.id })
      setStatus(`Scene created: ${scene.title}`)
    },
  })

  const createBeat = useMutation({
    mutationFn: () => api.createBeat(sceneId, beatIntent, characterId || undefined),
    onSuccess: (beat) => {
      setBeatId(beat.id)
      saveStudioContext({ beatId: beat.id, characterId })
      setStatus(`Beat created: ${beat.intent}`)
    },
  })

  const generate = useMutation({
    mutationFn: () => api.generateDialogue(beatId, characterId),
    onSuccess: (result) => {
      setCandidates(result.candidates)
      setStatus('Dialogue candidates ready')
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
      setStatus('Script locked')
    },
  })

  return (
    <section className="page" data-testid="story-page">
      <h1>Story</h1>
      <p className="lede">Character → Scene → Beat → Dialogue → Lock</p>

      <div className="stack">
        <label>
          Project
          <select
            aria-label="Project"
            data-testid="story-project-select"
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value)
              saveStudioContext({ projectId: e.target.value })
            }}
          >
            <option value="">Select project…</option>
            {(projects.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </label>

        <label>
          Character
          <select
            aria-label="Character"
            data-testid="story-character-select"
            value={characterId}
            onChange={(e) => {
              const id = e.target.value
              setCharacterId(id)
              const name = characters.data?.find((c) => c.id === id)?.display_name
              saveStudioContext({ characterId: id, characterName: name })
            }}
          >
            <option value="">Select character…</option>
            {(characters.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.display_name}
              </option>
            ))}
          </select>
        </label>

        <div className="inline-form">
          <input
            aria-label="Scene title"
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
            Create Scene
          </button>
        </div>

        <div className="inline-form">
          <input
            aria-label="Beat intent"
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
            Create Beat
          </button>
        </div>

        <button
          type="button"
          className="btn primary"
          data-testid="story-generate-dialogue"
          disabled={!beatId || !characterId || generate.isPending}
          onClick={() => generate.mutate()}
        >
          Generate Dialogue
        </button>
      </div>

      {status && (
        <p className="hint" data-testid="story-status">
          {status}
        </p>
      )}

      <ul className="list" data-testid="dialogue-candidate-list">
        {candidates.map((c, index) => (
          <li key={c.id} data-testid={`dialogue-candidate-${index}`}>
            <p>{c.text}</p>
            <button
              type="button"
              className="btn"
              data-testid={`dialogue-lock-${index}`}
              onClick={() => lock.mutate(c)}
            >
              Lock candidate {index + 1}
            </button>
          </li>
        ))}
      </ul>

      {lockedId && (
        <p data-testid="story-locked-banner">
          Locked event <code>{lockedId}</code>
        </p>
      )}
      {(sceneId || beatId) && (
        <p className="meta" data-testid="story-ids">
          scene={sceneId || '—'} beat={beatId || '—'}
        </p>
      )}
    </section>
  )
}
