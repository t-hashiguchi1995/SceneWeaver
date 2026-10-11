#!/usr/bin/env python3
"""Same-seed real Comfy comparison of basic tags, exact user prompt and sampling steps."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from creator_studio.adapters.image import ComfyImageBackend
from creator_studio.adapters.llm import StubLLMProvider
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.application.shots.pipeline import ShotPipeline
from creator_studio.infrastructure.container import Container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/validation/rize-quality')
    parser.add_argument('--comfy-url', default='http://127.0.0.1:8188')
    parser.add_argument('--seed', type=int, default=20261011)
    args = parser.parse_args()
    positive = (ROOT / 'tests/fixtures/story/rize_user_prompt.txt').read_text().rstrip('\n')
    remove = {'year 2025', 'newest', 'score_9', 'score_8', '@fuzichoco', '@rella'}
    basic = ', '.join(token.strip() for token in positive.split(',') if token.strip() not in remove) + ', anime illustration'
    negative = PromptRenderer().render_anima({}).negative
    run_dir = args.output.resolve() / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    runtime = run_dir / 'runtime'
    runtime.mkdir(parents=True)
    settings = Settings(runtime_dir=str(runtime), database_url=f'sqlite:///{runtime}/studio.db', image_backend='comfy', comfy_url=args.comfy_url)
    upgrade_head(settings.sqlalchemy_url())
    c = Container(settings)
    image = ComfyImageBackend(args.comfy_url, repo_root=ROOT, registry_path=ROOT / 'config/model_registry.yaml', asset_store=c.asset_store, poll_timeout_seconds=600)
    pipeline = ShotPipeline(c.uow(), StubLLMProvider(), image, c.asset_store, c.prompts)
    project = c.create_project().execute(CreateProjectCommand(title='リゼ 同一seed 品質比較', content_rating='adult'))
    character = c.create_character().execute('リゼ・ヘルエスタ（品質比較）')
    scene = c.create_scene().execute(project.id, '品質タグとstepsの比較')
    graph = json.loads((ROOT / 'workflows/comfy/anima_base.api.json').read_text())
    cases = [('basic_8', '簡易タグ・8 steps', basic, 8), ('user_8', 'ご提示Promptそのまま・8 steps', positive, 8), ('user_24', 'ご提示Promptそのまま・24 steps', positive, 24)]
    report = {'seed': args.seed, 'width': graph['28']['inputs']['width'], 'height': graph['28']['inputs']['height'], 'cfg': 4,
              'sampler': graph['12']['inputs']['sampler_name'], 'scheduler': graph['12']['inputs']['scheduler'],
              'negative': negative, 'user_prompt_sha256': hashlib.sha256(positive.encode()).hexdigest(), 'cases': []}
    for case_id, label, prompt, steps in cases:
        beat = c.create_beat().execute(scene.id, intent=label, speaker_id=character.id)
        shot = pipeline.plan_shot(beat.id)
        pipeline.update_shot(shot.id, {'sampling_steps': steps, 'sampling_cfg': 4})
        c.prompt_draft_service().ensure_for_shot(shot.id)
        c.prompt_draft_service().update_edits(shot.id, prompt, negative)
        print(f'{case_id}: seed={args.seed}, steps={steps}, cfg=4', flush=True)
        result = pipeline.render(shot.id, seed=args.seed)
        attempt = pipeline.get_attempt(result['generation_attempt_id'])
        assert attempt.payload['final_positive_prompt'] == prompt, 'Prompt was changed before submit'
        assert attempt.payload['render_snapshot']['slots']['sampling_steps'] == steps
        outputs = []
        for index, asset_id in enumerate(result['output_asset_ids']):
            with c.uow() as uow:
                asset = uow.assets.get(asset_id)
            source = c.asset_store.path_for_uri(asset.uri)
            raw = source.read_bytes()
            assert raw.startswith(b'\x89PNG\r\n\x1a\n')
            width, height = struct.unpack('>II', raw[16:24])
            destination = run_dir / 'images' / f'{case_id}-{index + 1}.png'
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, destination)
            outputs.append({'file': destination.relative_to(run_dir).as_posix(), 'asset_id': asset.id, 'sha256': asset.sha256, 'width': width, 'height': height, 'provenance': asset.provenance})
        assert len(outputs) == 4
        report['cases'].append({'id': case_id, 'label': label, 'positive': prompt, 'steps': steps, 'generation': result, 'snapshot': attempt.payload['render_snapshot'], 'assets': outputs})
        (run_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    e = lambda value: html.escape(str(value))
    sections = []
    for case in report['cases']:
        imgs = ''.join(f'<a href="{e(a["file"])}"><img src="{e(a["file"])}" alt="{e(case["label"])} 候補{i + 1}"></a>' for i, a in enumerate(case['assets']))
        sections.append(f'<section><h2>{e(case["label"])}</h2><div class="images">{imgs}</div><details><summary>送信したPromptと条件</summary><pre>{e(case["positive"])}</pre><p>steps={case["steps"]}, seed={report["seed"]}, CFG=4</p></details></section>')
    body = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>リゼ Prompt品質比較</title><style>body{{margin:0;background:#111722;color:#eef4ff;font:16px/1.6 system-ui}}main{{max-width:1440px;padding:24px;margin:auto}}section{{margin:32px 0}}.images{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}img{{width:100%;display:block}}a{{color:#91cfff}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}@media(max-width:700px){{.images{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}</style><main><h1>リゼ・ヘルエスタ：既存タグとstepsの品質比較</h1><p>実ComfyUI、Anima。seed={report['seed']}、{report['width']}×{report['height']}、CFG=4、{e(report['sampler'])}/{e(report['scheduler'])}、negative固定、各4候補。</p><p>①と②は品質・画風タグだけを変更。②と③はstepsだけを変更。②③のpositiveはご提示のPromptと文字列一致を検証しています。生成成功は画質の合格を意味しません。線・塗り・表情・手指・衣装の再現を並べて評価します。</p><p><a href="results.json">全条件・provenance JSON</a></p>{''.join(sections)}</main></html>'''
    (run_dir / 'index.html').write_text(body)
    (args.output / 'latest.txt').write_text(run_dir.name + '\n')
    print(json.dumps({'report': str(run_dir / 'index.html'), 'images': sum(len(c['assets']) for c in report['cases'])}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
