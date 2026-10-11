#!/usr/bin/env python3
"""Persist a three-scene Rize validation: story state, dialogue, prompts and real Comfy assets.

Uses an isolated runtime; never resets or overwrites the user's working database.
Real dialogue/story quality is pending when --allow-stub is explicitly requested.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import struct
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

from creator_studio.adapters.image import ComfyImageBackend
from creator_studio.adapters.llm import OpenAICompatibleProvider, StubLLMProvider
from creator_studio.application.dialogue.pipeline import DialoguePipeline
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.shots.pipeline import ShotPipeline
from creator_studio.infrastructure.container import Container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.settings import Settings, get_settings
from scripts.import_legacy_prompts import SOURCE, apply_plan, build_plan, reconcile_idempotency


def plain(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)))


class RecordingGateway:
    def __init__(self, inner: Any):
        self.inner = inner
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, **kwargs: Any) -> Any:
        result = self.inner.complete_json(**kwargs)
        self.calls.append({**kwargs, 'response': result})
        return result


def write_report(run_dir: Path, report: dict[str, Any]) -> None:
    (run_dir / 'results.json').write_text(json.dumps(plain(report), ensure_ascii=False, indent=2))
    e = lambda value: html.escape(str(value))
    sections = []
    for pattern in report['patterns']:
        panels = []
        for beat in pattern['beats']:
            images = ''.join(f'<a href="{e(a["file"])}"><img loading="lazy" src="{e(a["file"])}" alt="{e(pattern["title"])} 第{beat["seq"]}コマ 候補{i + 1}"></a>' for i, a in enumerate(beat.get('assets', [])))
            candidates = ''.join(f'<li>{e(c["text"])} <small>{e(c["tone"])}</small></li>' for c in beat['dialogue']['candidates'])
            panels.append(f'''<article><h3>{beat['seq']}. {e(beat['intent'])}</h3>
              <p class="line">「{e(beat['locked_text'])}」</p><p class="meta">確定セリフの出典: {e(beat['locked_text_source'])}</p>
              <p>裏の意図: {e(beat['subtext'])}</p><p>状態変化: {e(json.dumps(beat['state_delta'], ensure_ascii=False))}</p>
              <div class="images">{images}</div>
              <details><summary>セリフ候補・Director / Critic</summary><ol>{candidates}</ol><pre>{e(json.dumps(beat['dialogue'], ensure_ascii=False, indent=2))}</pre></details>
              <details><summary>最終Prompt・生成条件・構成要素</summary><p>seed: {beat.get('seed', '')}</p><pre>{e(json.dumps(beat.get('draft', {}), ensure_ascii=False, indent=2))}</pre></details>
            </article>''')
        sections.append(f'<section id="{e(pattern["id"])}"><h2>{e(pattern["title"])}</h2><p>{e(pattern["objective"])}</p>{"".join(panels)}</section>')
    checks = ''.join(f'<li class="{e(c["status"])}">[{e(c["status"])}] {e(c["name"])}: {e(c["detail"])}</li>' for c in report['checks'])
    llm_label = '実LLM' if report['llm']['real'] else 'stub（固定応答。セリフ品質は不適合、実LLM品質は未検証）'
    doc = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>リゼ・ヘルエスタ 検証</title>
    <style>body{{font:16px/1.7 system-ui,sans-serif;margin:0;background:#10131a;color:#edf1fa}}main{{max-width:1280px;margin:auto;padding:24px}}a{{color:#8cc9ff}}article{{padding:20px;background:#1b2130;border-radius:12px;margin:24px 0}}.images{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}img{{display:block;width:100%;height:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}.line{{font-size:21px;padding:12px;border-left:4px solid #90bafa}}.meta,small{{color:#b3bed3}}details{{margin-top:14px}}.fail{{color:#ff9d9d}}.pass{{color:#90dcba}}.pending{{color:#ffd187}}@media(max-width:700px){{.images{{grid-template-columns:repeat(2,minmax(0,1fr))}}main{{padding:12px}}article{{padding:12px}}}}</style>
    <main><h1>リゼ・ヘルエスタ：ストーリー・セリフ・画像Prompt検証</h1>
    <p>LLM: {e(llm_label)} / 画像: 実ComfyUI。検証用の創作であり、公式の物語・本人の実発言ではありません。</p>
    <p>ストーリー設計: {e(report['story_source'])} / <a href="results.json">全結果JSON</a> / <a href="https://www.nijisanji.jp/talents/l/lize-helesta">公式プロフィール（設定・外見の参照）</a></p>
    <ul>{checks}</ul>{''.join(sections)}<details><summary>LLMに渡した文脈・応答</summary><pre>{e(json.dumps(report.get('llm_calls', []), ensure_ascii=False, indent=2))}</pre></details></main></html>'''
    (run_dir / 'index.html').write_text(doc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/validation/rize')
    parser.add_argument('--comfy-url', default='http://127.0.0.1:8188')
    parser.add_argument('--llm-base-url')
    parser.add_argument('--llm-model')
    parser.add_argument('--allow-stub', action='store_true')
    parser.add_argument('--generate-story', action='store_true')
    parser.add_argument('--skip-images', action='store_true')
    parser.add_argument('--fixture', type=Path, default=ROOT / 'tests/fixtures/story/rize_patterns.json')
    parser.add_argument('--sampling-steps', type=int, default=24)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    if not 1 <= args.sampling_steps <= 100:
        raise ValueError('sampling steps must be between 1 and 100')
    user_container = Container(get_settings())
    user_settings = user_container.settings_service().get()
    real = bool(args.llm_base_url or user_settings['llm_provider'] == 'openai_compatible')
    if not real and not args.allow_stub:
        raise SystemExit('Real LLM is not configured. Set it in Settings, or explicitly use --allow-stub for a labelled offline baseline.')
    if args.generate_story and not real:
        raise SystemExit('--generate-story requires a real LLM')
    llm = OpenAICompatibleProvider(base_url=args.llm_base_url or user_settings['llm_base_url'], model=args.llm_model or user_settings['llm_model'], api_key=os.environ.get('SCENEWEAVER_LLM_API_KEY') or user_container.settings_service().llm_api_key()) if real else StubLLMProvider()
    gateway = RecordingGateway(llm)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_dir = args.output.resolve() / stamp
    runtime = run_dir / 'runtime'
    runtime.mkdir(parents=True)
    settings = Settings(runtime_dir=str(runtime), database_url=f'sqlite:///{runtime}/studio.db', image_backend='comfy', comfy_url=args.comfy_url)
    upgrade_head(settings.sqlalchemy_url())
    c = Container(settings)
    apply_plan(reconcile_idempotency(build_plan(args.source), c), c)
    with c.uow() as uow:
        imported = uow.legacy_imports.get(SOURCE, 'characters/rizehel.yaml', 'rizehel')
        if imported is None:
            raise ValueError('rizehel.yaml was not imported from the supplied archive')
        character_id = imported.entity_id
        presets = uow.prompt_presets.list_enabled()
    c.update_persona().execute(character_id, fixture['persona'])
    c.update_visual_identity().execute(character_id, fixture['visual_identity'])
    project = c.create_project().execute(CreateProjectCommand(title='リゼ・ヘルエスタ 複数場面の検証'))
    image = ComfyImageBackend(args.comfy_url, repo_root=ROOT, registry_path=ROOT / 'config/model_registry.yaml', asset_store=c.asset_store, poll_timeout_seconds=600)
    shot_pipeline = ShotPipeline(c.uow(), gateway, image, c.asset_store, c.prompts)
    dialogue_pipeline = DialoguePipeline(c.uow(), gateway, c.prompts, on_script_change=shot_pipeline.invalidate_for_script_change)
    report: dict[str, Any] = {'created_at': stamp, 'project_id': project.id, 'character_id': character_id,
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'llm': {'real': real, 'model': args.llm_model or user_settings['llm_model'] if real else 'stub'},
        'story_source': '実LLMの構成案' if args.generate_story else '創作台本（fixture）',
        'patterns': [], 'checks': [], 'llm_calls': gateway.calls}
    check = lambda name, passed, detail: report['checks'].append({'name': name, 'status': 'pass' if passed else 'fail', 'detail': detail})
    if not real:
        report['checks'].append({'name': '実LLMによるセリフ・展開の品質', 'status': 'pending', 'detail': 'API未設定。固定応答を品質の合格根拠には使用しない。'})
    all_candidate_groups: list[list[str]] = []
    try:
        for p_index, original in enumerate(fixture['patterns']):
            pattern = json.loads(json.dumps(original))
            if args.generate_story:
                beat_count = len(pattern['beats'])
                generated = gateway.complete_json(system='Return JSON only. You plan a short Japanese character-driven comic.', user=json.dumps({'persona': fixture['persona'], 'premise': {k: pattern[k] for k in ['title', 'objective', 'initial_state']}, 'requirements': f'{beat_count} beats: setup, turn, resolution. Preserve canon and scene state. Return a JSON object with objective and beats. Each beat has intent, subtext, emotion (name and intensity), action and state_delta. Do not write dialogue yet.'}, ensure_ascii=False))
                if not isinstance(generated, dict) or len(generated.get('beats', [])) != beat_count:
                    raise ValueError(f'story generator must return exactly {beat_count} beats')
                pattern['objective'] = generated['objective']
                for b, generated_beat in zip(pattern['beats'], generated['beats']):
                    b.update({k: generated_beat[k] for k in ['intent', 'subtext', 'emotion', 'action', 'state_delta']})
            initial = dict(pattern['initial_state'])
            initial.update({k: pattern[k] for k in ['background', 'outfit_tags'] if k in pattern})
            scene = c.create_scene().execute(project.id, pattern['title'], objective=pattern['objective'], initial_state=initial)
            p_result = {'id': pattern['id'], 'title': pattern['title'], 'objective': pattern['objective'], 'scene_id': scene.id, 'beats': []}
            report['patterns'].append(p_result)
            for b_index, b in enumerate(pattern['beats']):
                beat = c.create_beat().execute(scene.id, b['intent'], subtext=b['subtext'], emotion=b['emotion'], action=b['action'], speaker_id=character_id, state_delta=b['state_delta'])
                dialogue = dialogue_pipeline.generate_candidates(beat_id=beat.id, character_id=character_id)
                lines = [x.text for x in dialogue.candidates]
                all_candidate_groups.append(lines)
                check(f'{pattern["id"]}/{beat.seq}: セリフ候補の数と文字数', len(lines) == 3 and all(0 < len(t) <= fixture['persona']['max_chars'] for t in lines), f'{len(lines)}候補: {[len(t) for t in lines]}文字')
                if real:
                    selected = next((x for x in dialogue.candidates if not x.critic_scores.get('blocking_issues')), dialogue.candidates[0])
                    locked_text = selected.text
                    text_source = '実LLM候補を選択'
                else:
                    selected = dialogue.candidates[0]
                    locked_text = b['text']
                    text_source = '検証用の創作セリフを手修正・確定（stubの生成結果ではない）'
                locked = dialogue_pipeline.lock_script_event(selected.id, locked_text)
                shot = shot_pipeline.plan_shot(beat.id)
                selections = []
                for key in ['background_selection', 'outfit_selection', 'lighting_selection', 'pose_selection', 'expression_selection']:
                    ref = b.get(key) or pattern.get(key)
                    if ref:
                        preset = next((p for p in presets if (p.source_file, p.label) == tuple(ref)), None)
                        if not preset:
                            raise ValueError(f'library selection not found: {ref}')
                        selections.append(preset.id)
                patch: dict[str, Any] = {'prompt_profile_id': 'anima_story_panel', 'prompt_quality_profile_id': 'anima_legacy_v1', 'sampling_steps': args.sampling_steps, 'sampling_cfg': 4, 'prompt_preset_ids': selections}
                if not real:
                    patch.update({'camera': b['camera']})
                    if b.get('pose'): patch['pose'] = {'id': b['pose']}
                    if b.get('expression'): patch['expression'] = {'id': b['expression']}
                shot_pipeline.update_shot(shot.id, patch)
                draft = c.prompt_draft_service().ensure_for_shot(shot.id)
                check(f'{pattern["id"]}/{beat.seq}: 外見と選択素材の構築', 'lize helesta' in draft.edited_positive and 'purple eyes' in draft.edited_positive and all(any(ref.startswith(f'{pid}@') for ref in draft.assembly_metadata['component_refs']) for pid in selections), 'キャラクター外見・選択素材のID/内容ハッシュを最終Promptに反映')
                b_result = {'seq': beat.seq, 'beat_id': beat.id, 'shot_id': shot.id, 'intent': b['intent'], 'subtext': b['subtext'], 'state_delta': b['state_delta'], 'dialogue': asdict(dialogue), 'locked_text': locked_text, 'locked_text_source': text_source, 'draft': draft.to_dict(), 'assets': []}
                p_result['beats'].append(b_result)
                if not args.skip_images:
                    seed = 20261011 + p_index * 10 + b_index
                    print(f'[{pattern["id"]} beat {beat.seq}] real Comfy generation seed={seed}', flush=True)
                    rendered = shot_pipeline.render(shot.id, seed=seed)
                    b_result['seed'] = seed
                    b_result['generation'] = rendered
                    b_result['attempt'] = plain(asdict(shot_pipeline.get_attempt(rendered['generation_attempt_id'])))
                    for index, asset_id in enumerate(rendered['output_asset_ids']):
                        with c.uow() as uow:
                            asset = uow.assets.get(asset_id)
                        if asset is None: raise ValueError(f'asset missing: {asset_id}')
                        source = c.asset_store.path_for_uri(asset.uri)
                        raw = source.read_bytes()
                        if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Comfy output is not PNG')
                        width, height = struct.unpack('>II', raw[16:24])
                        dest = run_dir / 'images' / f'{pattern["id"]}-{beat.seq}-{index + 1}.png'
                        dest.parent.mkdir(exist_ok=True)
                        shutil.copyfile(source, dest)
                        b_result['assets'].append({'file': dest.relative_to(run_dir).as_posix(), 'width': width, 'height': height, **plain(asdict(asset))})
                    check(f'{pattern["id"]}/{beat.seq}: 実Comfy 4候補', len(b_result['assets']) == 4 and all(a['width'] > 100 and a['provenance']['provider'] == 'comfyui' for a in b_result['assets']), f'{len(b_result["assets"])}枚、seed={seed}、実PNGを保存')
                with c.uow() as uow:
                    stored = uow.script_events.get(locked.id)
                    check(f'{pattern["id"]}/{beat.seq}: 確定セリフの保持', bool(stored and stored.locked and stored.text == locked_text), 'ショット計画と画像生成後も同じ確定セリフ')
                write_report(run_dir, report)
        distinct = len({tuple(group) for group in all_candidate_groups})
        check('場面・ビートによるセリフの変化', distinct == len(all_candidate_groups), f'{len(all_candidate_groups)}ビート中、異なる候補集合は{distinct}組。固定応答では品質不適合。')
        if not real:
            check('Directorの場面適合性', False, 'stubは全場面で「もう少し一緒にいたい」を返すため、謎解き・注文・ファン対応の目的を反映しない。')
        # Validate the unsupported modifier boundary without submitting an incompatible LoRA to Comfy.
        last_shot = report['patterns'][-1]['beats'][-1]['shot_id']
        lora = next(p for p in presets if p.source_file == 'characters/rizehel.yaml' and p.label == 'lize12th_wht')
        shot_pipeline.update_shot(last_shot, {'prompt_preset_ids': [lora.id]})
        c.prompt_draft_service().rebuild(last_shot, confirm=True)
        try:
            shot_pipeline.render(last_shot, seed=20261099)
            check('非対応LoRAの境界', False, '未承認のLoRAが生成に送信された')
        except ValueError as exc:
            check('非対応LoRAの境界', 'approved modifier workflow' in str(exc), str(exc))
        shot_pipeline.update_shot(last_shot, {'prompt_preset_ids': selections})
        c.prompt_draft_service().rebuild(last_shot, confirm=True)
    except Exception as exc:
        report['checks'].append({'name': '検証実行', 'status': 'fail', 'detail': f'{type(exc).__name__}: {exc}'})
        write_report(run_dir, report)
        raise
    write_report(run_dir, report)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'latest.txt').write_text(run_dir.name + '\n')
    print(json.dumps({'report': str(run_dir / 'index.html'), 'images': sum(len(b['assets']) for p in report['patterns'] for b in p['beats']), 'checks': {state: sum(c['status'] == state for c in report['checks']) for state in ['pass', 'fail', 'pending']}}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
