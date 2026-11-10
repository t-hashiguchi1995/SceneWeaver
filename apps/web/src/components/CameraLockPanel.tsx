import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, parseApiError, type CameraFacePolicy, type ShotCameraBinding } from '../lib/api'
import { AssetImage } from './AssetImage'
import { ErrorBanner } from './ErrorBanner'

export function CameraLockPanel(props: { projectId: string; shotId: string }) {
  return props.projectId ? <CameraLockControls key={`${props.projectId}:${props.shotId}`} {...props} /> : null
}

function CameraLockControls({ projectId, shotId }: { projectId: string; shotId: string }) {
  const { t } = useTranslation(['generation', 'common'])
  const label = (key: string) => t(`generation:cameraLock.${key}`)
  const qc = useQueryClient()
  const rigsKey = ['camera-rigs', projectId]
  const bindingKey = ['camera-binding', shotId]
  const attemptsKey = ['generation-attempts', shotId]
  const rigs = useQuery({ queryKey: rigsKey, queryFn: () => api.listCameraRigs(projectId) })
  const binding = useQuery({ queryKey: bindingKey, queryFn: () => api.getShotCameraBinding(shotId) })
  const attempts = useQuery({ queryKey: attemptsKey, queryFn: async () => {
    const result = await api.listGenerationAttempts(shotId)
    // P0a's list response may omit camera_stale; preserve explicit null provenance.
    const items = await Promise.all(result.items.map(async attempt => attempt.camera_stale === undefined
      ? { ...attempt, camera_stale: (await api.getGenerationAttempt(attempt.id)).camera_stale }
      : attempt))
    return { ...result, items }
  } })
  const dashboard = useQuery({ queryKey: ['project-dashboard', projectId], queryFn: () => api.projectDashboard(projectId) })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const rig = rigs.data?.find(r => r.id === (selectedId ?? binding.data?.rig_id)) ?? rigs.data?.[0]
  const [name, setName] = useState('')
  const [width, setWidth] = useState(1536)
  const [height, setHeight] = useState(864)
  const [facePolicy, setFacePolicy] = useState<CameraFacePolicy>('full_visible')
  const [bindingPolicy, setBindingPolicy] = useState<ShotCameraBinding['face_policy']>('full_visible')
  const [assetId, setAssetId] = useState('')
  const [notice, setNotice] = useState(false)
  const anchorAsset = useQuery({ queryKey: ['asset', rig?.anchor_asset_id], queryFn: () => api.getAsset(rig!.anchor_asset_id!), enabled: !!rig?.anchor_asset_id })
  const refresh = async () => { await Promise.all([qc.invalidateQueries({ queryKey: rigsKey }), qc.invalidateQueries({ queryKey: attemptsKey })]) }
  const create = useMutation({ mutationFn: () => api.createCameraRig(projectId, { name, frame: { width, height }, face_policy: facePolicy }), onSuccess: async r => { setSelectedId(r.id); await refresh() } })
  const lock = useMutation({ mutationFn: () => api.updateCameraRig(rig!.id, { expected_revision: rig!.revision, status: 'locked' }), onSuccess: refresh, onError: err => { if (parseApiError(err).code === 'CAMERA_RIG_STALE') void refresh() } })
  const anchor = useMutation({ mutationFn: () => api.registerCameraAnchor(rig!.id, assetId.trim()), onSuccess: refresh })
  const bind = useMutation({ mutationFn: () => api.bindShotCamera(shotId, { camera_rig_id: rig!.id, face_policy: bindingPolicy }), onSuccess: async () => { await Promise.all([qc.invalidateQueries({ queryKey: bindingKey }), qc.invalidateQueries({ queryKey: attemptsKey })]) } })
  const render = useMutation({ mutationFn: () => api.renderShot(shotId, false, undefined, undefined, undefined, { enabled: true, rig_id: rig!.id, expected_rig_revision: rig!.revision }), onSuccess: () => qc.invalidateQueries({ queryKey: attemptsKey }) })
  const candidates = [...new Set([...(dashboard.data?.recent_generations.flatMap(g => g.output_asset_ids) ?? []), ...(dashboard.data?.adopted_assets.map(a => a.asset_id) ?? []), ...(attempts.data?.items.flatMap(a => a.output_asset_ids) ?? [])])]
  const errorText = (err: unknown) => { const e = parseApiError(err); return [e.code, e.message].filter(Boolean).join(': ') }
  const anchorError = anchor.error ? parseApiError(anchor.error) : null
  const queryError = rigs.error ?? binding.error ?? attempts.error ?? dashboard.error ?? anchorAsset.error
  return <section className="stack panel-card" data-testid="camera-lock-panel">
    <h2>{label('title')}</h2>
    {queryError && <ErrorBanner message={errorText(queryError)} />}
    <label>{label('rig')}<select data-testid="camera-rig-select" value={rig?.id ?? ''} onChange={e => { setSelectedId(e.target.value); anchor.reset(); lock.reset(); render.reset() }}>
      {!rig && <option value="">{label('noRigs')}</option>}
      {rigs.data?.map(r => <option key={r.id} value={r.id}>{r.name} — {label('revision')} {r.revision}</option>)}
    </select></label>
    {rig && <><p className="meta" data-testid="camera-rig-status">{rig.name} · {label('revision')} {rig.revision} · {rig.status === 'locked' ? 'LOCKED' : rig.status}</p>
      <button className="btn" data-testid="camera-rig-lock" disabled={rig.status === 'locked' || lock.isPending} onClick={() => lock.mutate()}>{label('lockRig')}</button></>}
    {lock.error && <ErrorBanner message={parseApiError(lock.error).code === 'CAMERA_RIG_STALE' ? label('staleRigError') : errorText(lock.error)} />}
    <form className="stack" onSubmit={e => { e.preventDefault(); create.mutate() }}>
      <h3>{label('createRig')}</h3>
      <label>{label('name')}<input required data-testid="camera-rig-name" value={name} onChange={e => setName(e.target.value)} /></label>
      <div className="semantic-grid">
        <label>{label('width')}<input required min="1" type="number" data-testid="camera-rig-frame-width" value={width} onChange={e => setWidth(Number(e.target.value))} /></label>
        <label>{label('height')}<input required min="1" type="number" data-testid="camera-rig-frame-height" value={height} onChange={e => setHeight(Number(e.target.value))} /></label>
      </div>
      <label>{label('facePolicy')}<select data-testid="camera-rig-face-policy" value={facePolicy} onChange={e => setFacePolicy(e.target.value as CameraFacePolicy)}>{(['full_visible', 'partial_allowed', 'not_required'] as const).map(p => <option key={p} value={p}>{label(p)}</option>)}</select></label>
      <button className="btn" data-testid="camera-rig-create" disabled={create.isPending}>{label('createRig')}</button>
      {create.error && <ErrorBanner message={errorText(create.error)} />}
    </form>
    {rig && <>
      <h3>{label('anchor')}</h3>
      <div className="semantic-grid">{candidates.map(id => <button type="button" className="btn" style={{ maxWidth: 144 }} key={id} data-testid={`camera-anchor-candidate-${id}`} onClick={() => setAssetId(id)} aria-label={`${label('anchor')} ${id}`}><AssetImage assetId={id} alt={id} /></button>)}</div>
      <label>{label('assetId')}<input data-testid="camera-anchor-asset-id" value={assetId} onChange={e => setAssetId(e.target.value)} /></label>
      <button className="btn" data-testid="camera-anchor-register" disabled={!assetId.trim() || anchor.isPending} onClick={() => anchor.mutate()}>{label('registerAnchor')}</button>
      {rig.anchor_asset_id && <div className="stack" data-testid="camera-anchor-info"><div style={{ maxWidth: 192 }}><AssetImage assetId={rig.anchor_asset_id} alt={label('anchor')} /></div><span className="meta">SHA256: {anchorAsset.data?.sha256.slice(0, 12)}{anchor.data?.rig_id === rig.id && ` · ${label('revision')} ${anchor.data.revision}`}</span></div>}
      {anchorError?.code === 'ANCHOR_FACE_INVALID' ? <div className="error" role="alert" data-testid="camera-anchor-face-warning">{label('anchorFaceWarning')} {anchorError.message}</div> : anchorError && <p role="alert" className="error" data-testid="camera-anchor-error">{errorText(anchor.error)}</p>}
      <h3>{label('binding')}</h3>
      <label>{label('facePolicy')}<select data-testid="camera-binding-face-policy" value={bindingPolicy} onChange={e => setBindingPolicy(e.target.value as ShotCameraBinding['face_policy'])}>{(['full_visible', 'partial_allowed'] as const).map(p => <option key={p} value={p}>{label(p)}</option>)}</select></label>
      <button className="btn" data-testid="camera-binding-bind" disabled={!rig.anchor_asset_id || bind.isPending} onClick={() => bind.mutate()}>{label('bind')}</button>
      {!rig.anchor_asset_id && <p className="hint">{label('needAnchorFirst')}</p>}
      {bind.error && <ErrorBanner message={errorText(bind.error)} />}
      <button className="btn" data-testid="camera-lock-render" disabled={binding.data?.rig_id !== rig.id || render.isPending} onClick={() => render.mutate()}>{label('render')}</button>
    </>}
    <p className="meta" data-testid="camera-binding-state">{binding.data ? `${label('bound')}: ${rigs.data?.find(r => r.id === binding.data?.rig_id)?.name ?? binding.data.rig_id} · ${label('revision')} ${binding.data.rig_revision} · ${binding.data.anchor_asset_sha256.slice(0, 12)}` : label('notBound')}</p>
    {render.error && (parseApiError(render.error).code === 'CAMERA_LOCK_CAPABILITY_UNAVAILABLE' ? <div role="alert" className="hint" data-testid="camera-lock-unavailable">{label('unavailable')}</div> : <p role="alert" className="error" data-testid="camera-lock-render-error">{errorText(render.error)}</p>)}
    <div className="stack" data-testid="camera-attempts"><h3>{label('attempts')}</h3>{attempts.data?.items.map(a => <div key={a.id} data-testid={`camera-attempt-${a.id}`} className="stack"><span className="meta">{a.status} · {label('seed')} {a.seed} · {a.created_at}</span>{a.camera_stale === true && <div className="cta-row"><span className="hint" data-testid={`camera-attempt-stale-${a.id}`}>{label('attemptStale')}</span><button className="btn" data-testid={`camera-attempt-regenerate-${a.id}`} onClick={() => setNotice(true)}>{label('regenerate')}</button></div>}</div>)}</div>
    {notice && <p className="hint" data-testid="camera-regenerate-notice">{label('regenerateHint')}</p>}
  </section>
}
