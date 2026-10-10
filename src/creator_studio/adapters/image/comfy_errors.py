from __future__ import annotations

from enum import StrEnum


class ComfyErrorCode(StrEnum):
    COMFY_UNREACHABLE = "COMFY_UNREACHABLE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    CUSTOM_NODE_MISSING = "CUSTOM_NODE_MISSING"
    WORKFLOW_INVALID = "WORKFLOW_INVALID"
    SUBMIT_FAILED = "SUBMIT_FAILED"
    GENERATION_FAILED = "GENERATION_FAILED"
    OUTPUT_NOT_FOUND = "OUTPUT_NOT_FOUND"
    TIMEOUT = "TIMEOUT"


class ComfyError(RuntimeError):
    def __init__(self, code: ComfyErrorCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {message}")


def classify_comfy_message(raw: str) -> ComfyErrorCode:
    text = raw.lower()
    if any(
        token in text
        for token in (
            "connection refused",
            "connecterror",
            "unreachable",
            "name or service not known",
        )
    ):
        return ComfyErrorCode.COMFY_UNREACHABLE
    if "timed out" in text or "timeout" in text:
        return ComfyErrorCode.TIMEOUT
    if (
        "custom node" in text
        or "missing_node_type" in text
        or "node type" in text
        or ("not found" in text and "node" in text)
    ):
        return ComfyErrorCode.CUSTOM_NODE_MISSING
    if "model" in text and any(token in text for token in ("not found", "missing", "no such file")):
        return ComfyErrorCode.MODEL_NOT_FOUND
    if "prompt_outputs_failed_validation" in text or (
        "workflow" in text and "invalid" in text
    ):
        return ComfyErrorCode.WORKFLOW_INVALID
    if "validation" in text and ("failed" in text or "invalid" in text):
        return ComfyErrorCode.WORKFLOW_INVALID
    if "output" in text and ("not found" in text or "empty" in text):
        return ComfyErrorCode.OUTPUT_NOT_FOUND
    if "execution_error" in text or "exception_message" in text:
        return ComfyErrorCode.GENERATION_FAILED
    if "submit" in text or "prompt submit" in text:
        return ComfyErrorCode.SUBMIT_FAILED
    return ComfyErrorCode.GENERATION_FAILED
