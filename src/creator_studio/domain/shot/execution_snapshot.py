"""Immutable enqueue-time execution specification and pure policy decisions.

This contract has no dependency on generation services or execution state.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, fields
from enum import StrEnum
from numbers import Real
from typing import Any


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _hash(value: object, name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def _integer(value: object, name: str, minimum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, not bool")  # noqa: TRY004
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def _real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number, not bool")  # noqa: TRY004
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


def _instance(value: object, cls: type, name: str) -> None:
    if not isinstance(value, cls):
        raise ValueError(f"{name} must be a {cls.__name__}")  # noqa: TRY004


@dataclass(frozen=True)
class AssetRef:
    asset_id: str
    sha256: str

    def __post_init__(self) -> None:
        _text(self.asset_id, "asset_id")
        _hash(self.sha256, "sha256")


@dataclass(frozen=True)
class ControlPass:
    kind: str
    strength: float

    def __post_init__(self) -> None:
        _text(self.kind, "kind")
        object.__setattr__(self, "strength", _real(self.strength, "strength"))


@dataclass(frozen=True)
class GenerationParams:
    positive: str
    negative: str
    seed: int
    steps: int
    cfg: float
    denoise: float
    sampler: str
    scheduler: str

    def __post_init__(self) -> None:
        for name in ("positive", "negative"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be a string")  # noqa: TRY004
        _integer(self.seed, "seed")
        _integer(self.steps, "steps", 1)
        cfg = _real(self.cfg, "cfg")
        denoise = _real(self.denoise, "denoise")
        if cfg <= 0:
            raise ValueError("cfg must be > 0")
        if not 0 <= denoise <= 1:
            raise ValueError("denoise must be between 0 and 1")
        object.__setattr__(self, "cfg", cfg)
        object.__setattr__(self, "denoise", denoise)
        _text(self.sampler, "sampler")
        _text(self.scheduler, "scheduler")


@dataclass(frozen=True)
class CandidateSpec:
    candidate_count: int
    batch_mode: str

    def __post_init__(self) -> None:
        _integer(self.candidate_count, "candidate_count", 1)
        if self.candidate_count > 8:
            raise ValueError("candidate_count must be <= 8")
        _text(self.batch_mode, "batch_mode")


@dataclass(frozen=True)
class ModelArtifactRef:
    """Content identity only; mutable names and file paths are not identities."""

    content_hash: str | None = None
    immutable_revision: str | None = None

    def __post_init__(self) -> None:
        if self.content_hash is None and self.immutable_revision is None:
            raise ValueError("content_hash or immutable_revision is required")
        if self.content_hash is not None:
            _hash(self.content_hash, "content_hash")
        if self.immutable_revision is not None:
            _text(self.immutable_revision, "immutable_revision")
            revision = self.immutable_revision.strip().lower()
            if "/" in revision or "\\" in revision or revision.endswith(
                (".safetensors", ".ckpt", ".pt", ".pth", ".bin")
            ):
                raise ValueError("immutable_revision must not be a filename or path")


@dataclass(frozen=True)
class EnvironmentSpec:
    template_id: str
    template_hash: str
    checkpoint: ModelArtifactRef
    clip: ModelArtifactRef
    vae: ModelArtifactRef
    depth_patch: ModelArtifactRef | None = None
    pose_patch: ModelArtifactRef | None = None

    def __post_init__(self) -> None:
        _text(self.template_id, "template_id")
        _hash(self.template_hash, "template_hash")
        for name in ("checkpoint", "clip", "vae", "depth_patch", "pose_patch"):
            value = getattr(self, name)
            if value is None and name in ("depth_patch", "pose_patch"):
                continue
            _instance(value, ModelArtifactRef, name)


@dataclass(frozen=True, kw_only=True)
class ExecutionSnapshot:
    shot_id: str
    shot_revision: int
    source: AssetRef
    depth: AssetRef
    control_passes: tuple[ControlPass, ...]
    generation: GenerationParams
    candidates: CandidateSpec
    environment: EnvironmentSpec
    pose: AssetRef | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        _integer(self.schema_version, "schema_version")
        if self.schema_version != 1:
            raise ValueError("unsupported schema_version; expected 1")
        _text(self.shot_id, "shot_id")
        _integer(self.shot_revision, "shot_revision", 1)
        for name, cls in (
            ("source", AssetRef), ("depth", AssetRef), ("generation", GenerationParams),
            ("candidates", CandidateSpec), ("environment", EnvironmentSpec),
        ):
            _instance(getattr(self, name), cls, name)
        if self.pose is not None:
            _instance(self.pose, AssetRef, "pose")
        if not isinstance(self.control_passes, (list, tuple)):
            raise ValueError("control_passes must be a list or tuple")  # noqa: TRY004
        for control in self.control_passes:
            _instance(control, ControlPass, "control_passes entry")
        object.__setattr__(self, "control_passes", tuple(self.control_passes))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["control_passes"] = list(result["control_passes"])
        return result

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def snapshot_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionSnapshot:
        """Reject unknown keys at every level before constructing validated values."""
        def build(model: type, value: object) -> Any:
            if not isinstance(value, dict):
                raise ValueError(f"{model.__name__} must be a dict")  # noqa: TRY004
            unknown = value.keys() - {field.name for field in fields(model)}
            if unknown:
                raise ValueError(f"unknown {model.__name__} keys: {sorted(map(str, unknown))}")
            values = dict(value)
            nested = {
                ExecutionSnapshot: {
                    "source": AssetRef, "depth": AssetRef, "pose": AssetRef,
                    "generation": GenerationParams, "candidates": CandidateSpec,
                    "environment": EnvironmentSpec,
                },
                EnvironmentSpec: dict.fromkeys(
                    ("checkpoint", "clip", "vae", "depth_patch", "pose_patch"), ModelArtifactRef
                ),
            }.get(model, {})
            for name, child in nested.items():
                if name in values and values[name] is not None:
                    values[name] = build(child, values[name])
            if model is ExecutionSnapshot and "control_passes" in values:
                controls = values["control_passes"]
                if not isinstance(controls, (list, tuple)):
                    raise ValueError("control_passes must be a list or tuple")
                values["control_passes"] = tuple(build(ControlPass, item) for item in controls)
            try:
                return model(**values)
            except TypeError as exc:
                raise ValueError(f"invalid {model.__name__}: {exc}") from exc

        return build(cls, data)


class IdempotencyAction(StrEnum):
    """Create a job, reuse the matching job, or reject a mismatched specification."""

    CREATE_NEW = "create_new"
    REUSE_EXISTING = "reuse_existing"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class IdempotencyDecision:
    """Only conflicts prescribe an HTTP status (409); other decisions use None."""

    action: IdempotencyAction
    http_status: int | None
    existing_job_id: str | None
    reason: str


def decide_idempotency(
    existing_job_id: str | None,
    existing_snapshot: ExecutionSnapshot | None,
    incoming_snapshot: ExecutionSnapshot,
) -> IdempotencyDecision:
    if existing_job_id is None or existing_snapshot is None:
        return IdempotencyDecision(IdempotencyAction.CREATE_NEW, None, None, "No existing job")
    if existing_snapshot.snapshot_hash == incoming_snapshot.snapshot_hash:
        return IdempotencyDecision(
            IdempotencyAction.REUSE_EXISTING, None, existing_job_id, "Snapshot hashes match"
        )
    return IdempotencyDecision(
        IdempotencyAction.CONFLICT, 409, existing_job_id, "Snapshot hashes differ"
    )


@dataclass(frozen=True)
class RevisionDecision:
    allowed: bool
    is_stale: bool
    treat_as_latest: bool
    reason: str


def decide_revision_policy(
    snapshot: ExecutionSnapshot, current_shot_revision: int, *, is_replay: bool = False
) -> RevisionDecision:
    _integer(current_shot_revision, "current_shot_revision", 1)
    if not isinstance(is_replay, bool):
        raise ValueError("is_replay must be a bool")  # noqa: TRY004
    if current_shot_revision == snapshot.shot_revision:
        return RevisionDecision(True, False, True, "Enqueue-time revision is current")
    if is_replay:
        return RevisionDecision(
            True, True, False, "Replay uses frozen revision; result is stale and not latest"
        )
    return RevisionDecision(
        False, True, False, "Enqueue-time revision mismatch; execution refused"
    )
