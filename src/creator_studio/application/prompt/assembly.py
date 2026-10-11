from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from typing import Any

from creator_studio.domain.prompt.assembly import BuiltPrompt, PromptAssemblyProfile, PromptComponent

_LORA = re.compile(r"<lora:([^:>]+):(-?\d+(?:\.\d+)?)>")
_EXCLUSIVE = {"subject_count", "outfit", "pose", "camera", "background", "lighting"}

QUALITY_PROFILES = {
    'builder_basic_v1': {
        'style': 'anime illustration',
        'positive': 'masterpiece, best quality, highres',
        'negative': 'worst quality, low quality, bad anatomy, bad hands, text, watermark',
    },
    'anima_legacy_v1': {
        'style': '@fuzichoco, @rella',
        'positive': 'year 2025, newest, masterpiece, best quality, score_9, score_8, highres, safe',
        'negative': 'worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, signature, watermark, username, artist name',
    },
}


def build_default_prompt(components: list[PromptComponent], profile: PromptAssemblyProfile) -> BuiltPrompt:
    warnings: list[str] = []
    valid: list[PromptComponent] = []
    for component in components:
        if not component.enabled or component.model_scope not in {"any", profile.model}:
            continue
        if component.content_rating not in {"general", "adult"} or (profile.content_rating == "general" and component.content_rating != "general"):
            warnings.append(f"content policy excluded {component.ref}")
            continue
        valid.append(component)
    # Stable sorting also makes provenance independent of query order.
    valid.sort(key=lambda c: (-c.precedence, -c.priority, c.component_id, c.component_version, c.text))
    winners: list[PromptComponent] = []
    seen: set[tuple[str, str, bool]] = set()
    for component in valid:
        limited = component.kind == "expression"
        if limited and not component.subkind:
            warnings.append(f"expression missing subkind: {component.ref}")
            continue
        group = (component.kind, component.subkind if limited else "", component.negative)
        if component.kind in _EXCLUSIVE or limited:
            if group in seen:
                continue
            seen.add(group)
        winners.append(component)
    order = {kind: index for index, kind in enumerate(profile.positive_order)}
    winners.sort(key=lambda c: (c.negative, order.get(c.kind, 100), c.subkind, c.component_id, c.component_version))
    modifiers: list[dict[str, Any]] = []
    cleaned: list[PromptComponent] = []
    for component in winners:
        for match in _LORA.finditer(component.text):
            modifier = {"kind": "lora", "model": match[1], "strength": float(match[2])}
            if modifier not in modifiers:
                modifiers.append(modifier)
        cleaned.append(replace(component, text=_LORA.sub("", component.text).strip(" ,")))
    def assemble(negative: bool) -> str:
        tokens: list[str] = []
        for component in cleaned:
            if component.negative != negative:
                continue
            for token in component.text.split(','):
                token = token.strip()
                if token and token not in tokens:
                    tokens.append(token)
        return ', '.join(tokens)
    return BuiltPrompt(assemble(False), assemble(True), cleaned, modifiers, sorted(warnings))


def components_from_context(spec: dict[str, Any]) -> list[PromptComponent]:
    quality_id = spec.get('prompt_quality_profile_id', 'builder_basic_v1')
    if quality_id not in QUALITY_PROFILES:
        raise ValueError('unsupported prompt quality profile')
    quality = QUALITY_PROFILES[quality_id]
    def text(value: Any) -> str:
        return ', '.join(map(str, value)) if isinstance(value, list) else str(value or '')
    def component(kind: str, value: Any, precedence: int = 2, subkind: str = '') -> PromptComponent:
        fragment = text(value)
        digest = hashlib.sha256(fragment.encode()).hexdigest()[:16]
        return PromptComponent(f'{kind}:{digest}', kind, fragment, precedence=precedence, subkind=subkind)
    camera = spec.get('camera') or {}
    components = [
        component('subject_count', '1girl', 0),
        component('character_identity', spec.get('identity_tags', []), 1),
        component('character_traits', spec.get('character_traits', ''), 1),
        component('outfit', spec.get('outfit_tags', 'casual clothes')),
        component('expression', (spec.get('expression') or {}).get('id', 'neutral'), subkind='emotion'),
        component('pose', (spec.get('pose') or {}).get('id', 'standing')),
        component('camera', ', '.join([str(camera.get('shot', 'medium')), str(camera.get('angle', 'eye_level'))])),
        component('background', spec.get('background', '')),
        component('lighting', 'soft indoor lighting', 0),
        component('style', quality['style'], 0),
        component('quality', quality['positive'], 0),
        PromptComponent(f'quality:negative:{quality_id}', 'quality', quality['negative'], negative=True),
    ]
    if spec.get('lighting'):
        components.append(component('lighting', spec['lighting']))
    # Explicit components are versioned library selections; never execute legacy YAML.
    for entry in spec.get('prompt_components', []):
        components.append(PromptComponent(**entry))
    return components
