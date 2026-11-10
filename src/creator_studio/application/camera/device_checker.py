import base64
import json
import math
from typing import Protocol

import httpx

from .qc_profile import (
    OLLAMA_BASE_URL,
    VLM_CONFIDENCE_FAIL,
    VLM_MODEL,
    VLM_TIMEOUT_SECONDS,
)

_NEGATIVE_AVAILABILITY: dict[tuple[str, str], dict] = {}
FIXED_QUESTIONS = """Return JSON only with these fields:
{"camera_device_visible": bool, "lcd_frame_visible": bool,
 "monitor_in_frame_view": bool, "confidence": number}.
Is a physical camera body visible in the foreground? Is an external LCD/monitor
bezel framing the scene (a photo of a screen)? Is this a third-person view
showing a monitor displaying the scene? Confidence must be between 0 and 1."""


class CameraDeviceChecker(Protocol):
    def check(self, image_bytes: bytes) -> tuple[str, dict]: ...


class OllamaCameraDeviceChecker:
    def __init__(self, base_url=OLLAMA_BASE_URL, model=VLM_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def check(self, image_bytes):
        key = (self.base_url, self.model)
        if key in _NEGATIVE_AVAILABILITY:
            return "unavailable", dict(_NEGATIVE_AVAILABILITY[key])
        try:
            with httpx.Client(timeout=VLM_TIMEOUT_SECONDS) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                model = next(
                    (m for m in models if self.model in (m.get("name"), m.get("model"))), None
                )
                if model is None or (
                    "capabilities" in model and not set(model["capabilities"]) & {"vision", "image"}
                ):
                    detail = {
                        "reason": "VLM_UNAVAILABLE",
                        "model": self.model,
                        "error": "model absent or lacks image capability",
                    }
                    _NEGATIVE_AVAILABILITY[key] = detail
                    return "unavailable", dict(detail)
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "stream": False,
                        "format": "json",
                        "messages": [
                            {
                                "role": "user",
                                "content": FIXED_QUESTIONS,
                                "images": [base64.b64encode(image_bytes).decode("ascii")],
                            }
                        ],
                    },
                )
                response.raise_for_status()
                result = json.loads(response.json()["message"]["content"])
                flags = [
                    result[name]
                    for name in (
                        "camera_device_visible",
                        "lcd_frame_visible",
                        "monitor_in_frame_view",
                    )
                ]
                confidence = result["confidence"]
                if (
                    any(type(flag) is not bool for flag in flags)
                    or type(confidence) not in (int, float)
                    or not math.isfinite(confidence)
                    or not 0 <= confidence <= 1
                ):
                    raise ValueError("invalid response fields")
                outcome = (
                    ("violation" if confidence >= VLM_CONFIDENCE_FAIL else "suspected")
                    if any(flags)
                    else "clear"
                )
                return outcome, result
        except httpx.HTTPError as exc:
            return "unavailable", {"reason": "VLM_UNAVAILABLE", "error": str(exc)}
        except (ValueError, KeyError, TypeError) as exc:
            return "unavailable", {"reason": "VLM_RESPONSE_INVALID", "error": str(exc)}
