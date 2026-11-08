from __future__ import annotations

import json
import re
from typing import Any

import httpx

from creator_studio.ports.llm import LLMResponseError


class StubLLMProvider:
    """Deterministic dialogue pipeline responses for tests and offline MVP."""

    model_name = property(lambda self: "stub")
    provider_name = property(lambda self: "stub")

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


def _normalize(data: Any, schema_hint: str | None) -> dict[str, Any] | list[Any]:
    if schema_hint == "array":
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("candidates", "items", "lines", "results", "data"):
                if isinstance(data.get(key), list):
                    return data[key]
        raise LLMResponseError("expected array or list wrapper")
    if isinstance(data, dict):
        return data
    raise LLMResponseError("expected object")


def _parse_json(content: str) -> Any:
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        starts = [i for i in (content.find("{"), content.find("[")) if i >= 0]
        if not starts:
            raise
        start = min(starts)
        end = content.rfind("}" if content[start] == "{" else "]")
        return json.loads(content[start : end + 1])


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.4,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._timeout = timeout
        self._max_retries = max(0, max_retries)

    model_name = property(lambda self: self._model)
    provider_name = property(lambda self: "openai_compatible")

    def complete_json(
        self, *, system: str, user: str, schema_hint: str | None = None
    ) -> dict[str, Any] | list[Any]:
        raw = ""
        reason = "invalid response"
        with httpx.Client(timeout=self._timeout) as client:
            for attempt in range(self._max_retries + 1):
                instruction = user
                if schema_hint == "array":
                    instruction += '\nReturn a JSON object with a "candidates" array.'
                if attempt:
                    instruction += "\nReturn ONLY valid JSON matching the requested shape."
                try:
                    response = client.post(
                        f"{self._base_url}/chat/completions",
                        json={
                            "model": self._model,
                            "temperature": self._temperature,
                            "response_format": {"type": "json_object"},
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": instruction},
                            ],
                        },
                        headers={"Authorization": f"Bearer {self._api_key}"},
                    )
                    raw = response.text
                    response.raise_for_status()
                    raw = response.json()["choices"][0]["message"]["content"]
                    if not isinstance(raw, str):
                        raise LLMResponseError("expected textual JSON content")
                    return _normalize(_parse_json(raw), schema_hint)
                except (
                    httpx.HTTPError,
                    ValueError,
                    KeyError,
                    IndexError,
                    TypeError,
                    LLMResponseError,
                ) as exc:
                    reason = str(exc)
        raise LLMResponseError(reason, str(raw))
