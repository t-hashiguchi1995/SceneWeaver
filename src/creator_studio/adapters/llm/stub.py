from __future__ import annotations

import json
import re
from typing import Any


class StubLLMProvider:
    """Deterministic dialogue pipeline responses for tests and offline MVP."""

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any] | list[Any]:
        joined = f"{system}\n{user}"
        if "dialogue director" in joined.lower() or "Do NOT write the final line" in joined:
            return {
                "speaker_id": _extract(joined, r'"speaker_id"\s*:\s*"([^"]+)"') or "char",
                "addressee_ids": ["partner"],
                "speech_act": "request",
                "intent": "もう少し一緒にいたい",
                "subtext": "直接寂しいとは言わない",
                "emotion": {"name": "shy", "intensity": 0.65},
                "delivery": {"volume": "soft", "pace": "slow", "pause_before": False},
                "action_hint": "look_over_shoulder",
                "information_to_convey": ["stay a bit longer"],
                "information_to_avoid_repeating": [],
            }
        if "Score each dialogue candidate" in joined:
            return {
                "scores": [
                    {
                        "index": 0,
                        "character_fidelity": 4.7,
                        "continuity": 4.5,
                        "subtext": 4.8,
                        "spoken_naturalness": 4.6,
                        "information_economy": 4.4,
                        "repetition": 4.9,
                        "bubble_fit": 4.5,
                        "visual_redundancy": 4.7,
                        "blocking_issues": [],
                        "evidence": "preserves subtext",
                    },
                    {
                        "index": 1,
                        "character_fidelity": 4.2,
                        "continuity": 4.1,
                        "subtext": 4.0,
                        "spoken_naturalness": 4.3,
                        "information_economy": 4.0,
                        "repetition": 4.5,
                        "bubble_fit": 4.2,
                        "visual_redundancy": 4.1,
                        "blocking_issues": [],
                        "evidence": "slightly more direct",
                    },
                    {
                        "index": 2,
                        "character_fidelity": 3.9,
                        "continuity": 4.0,
                        "subtext": 3.8,
                        "spoken_naturalness": 4.1,
                        "information_economy": 3.9,
                        "repetition": 4.2,
                        "bubble_fit": 4.0,
                        "visual_redundancy": 4.0,
                        "blocking_issues": [],
                        "evidence": "warmer variant",
                    },
                ]
            }
        if "spoken Japanese dialogue" in joined or "Return JSON array" in joined:
            return [
                {
                    "text": "……もう少しだけ、付き合ってくれません？",
                    "tone": "shy_indirect",
                    "fragment_hint": ["もう少しだけ"],
                },
                {
                    "text": "えへへ、まだ帰らなくてもいいですよ？",
                    "tone": "playful",
                    "fragment_hint": ["まだ帰らなくても"],
                },
                {
                    "text": "じゃあ、もうちょっとだけ、一緒に。",
                    "tone": "soft_request",
                    "fragment_hint": ["もうちょっとだけ"],
                },
            ]
        if "Convert the locked Beat" in joined or "shot specification" in joined.lower():
            return {
                "expression": {"id": "shy", "intensity": 0.65},
                "pose": {"id": "look_over_shoulder", "action": "turn back"},
                "gaze": "toward_viewer",
                "camera": {"shot": "medium", "angle": "eye_level"},
                "composition": {
                    "character_position": "center",
                    "reserved_lettering_region": "upper_right",
                },
                "scene_requirements": [],
                "reference_roles": ["identity", "outfit", "pose"],
                "required_capabilities": ["BaseRender", "PoseControlledRender"],
            }
        if schema_hint == "array":
            return []
        return {"ok": True, "echo": joined[:200]}


def _extract(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1) if m else None


class OpenAICompatibleProvider:
    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any] | list[Any]:
        import httpx

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        with httpx.Client(timeout=60.0) as client:
            r = client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        if schema_hint == "array" and isinstance(data, dict) and "items" in data:
            return data["items"]
        return data