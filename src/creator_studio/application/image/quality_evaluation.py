"""Framework-independent Phase 0 image QA; UNKNOWN metrics are never invented.

Persistence lives in quality_evaluation_store: one JSON record per evaluation in
settings.runtime_path()/quality_evaluations, beside the filesystem asset store.
There is no generic JSON record repository; this avoids a database migration.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

WEIGHTS = {
    "pose": 0.25,
    "anatomy": 0.20,
    "hands": 0.10,
    "identity": 0.15,
    "contact": 0.10,
    "visual": 0.10,
    "semantic": 0.05,
    "composition": 0.05,
}
AXES = tuple(WEIGHTS)
KEY_AXES = ("pose", "anatomy", "identity", "contact")


@dataclass
class Finding:
    category: str
    severity: int
    state: Literal["suspected", "confirmed"] = "suspected"
    bbox_norm_xyxy: tuple[float, float, float, float] | None = None
    evidence: str = ""
    evaluators: list[str] = field(default_factory=list)
    confirmed: bool = False

    def __post_init__(self) -> None:
        if self.severity not in range(4):
            raise ValueError("severity must be between 0 and 3")
        if self.state not in ("suspected", "confirmed"):
            raise ValueError("invalid finding state")


@dataclass
class QualityEvaluation:
    quality_evaluation_id: str = field(default_factory=lambda: str(uuid4()))
    generation_attempt_id: str | None = None
    image_sha256: str = ""
    image_is_original: bool = True
    evaluation_protocol: str = "image-qa-v0.1-draft"
    evaluator_versions: dict = field(default_factory=dict)
    reference_ids: dict[str, str | None] = field(
        default_factory=lambda: dict.fromkeys(("target_pose", "character", "scene_spec"))
    )
    scores: dict[str, float | None] = field(default_factory=lambda: dict.fromkeys(AXES))
    unavailable_metrics: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    score_interval: list[float] = field(default_factory=lambda: [0.0, 100.0])
    gate: Literal["PASS", "REVIEW", "FAIL", "BLOCKED"] = "REVIEW"
    gate_reasons: list[str] = field(default_factory=list)
    reviewer_id: str | None = None
    reviewed_at: str | None = None
    human_verdict: str | None = None

    def __post_init__(self) -> None:
        self.scores = {axis: self.scores.get(axis) for axis in AXES}
        self.reference_ids = {
            key: self.reference_ids.get(key) for key in ("target_pose", "character", "scene_spec")
        }
        self.unavailable_metrics = [axis for axis in AXES if self.scores[axis] is None]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["unavailable_metrics"] = [a for a in AXES if self.scores[a] is None]
        for finding in result["findings"]:
            if finding["bbox_norm_xyxy"] is not None:
                finding["bbox_norm_xyxy"] = list(finding["bbox_norm_xyxy"])
        return result

    @classmethod
    def from_dict(cls, data: dict) -> QualityEvaluation:
        values = dict(data)
        values["findings"] = []
        for item in data.get("findings", []):
            item = dict(item)
            if item.get("bbox_norm_xyxy") is not None:
                item["bbox_norm_xyxy"] = tuple(item["bbox_norm_xyxy"])
            values["findings"].append(Finding(**item))
        return cls(**values)


def compute_gate(
    scores: Mapping[str, float | None],
    findings: Iterable[Finding],
    blocked_reasons: Iterable[str] = (),
) -> tuple[str, list[str], list[float]]:
    """Apply defect overrides before the score and reference availability gates."""
    findings = list(findings)
    blocked_reasons = list(blocked_reasons)
    available = {a: scores.get(a) for a in AXES if scores.get(a) is not None}
    for value in available.values():
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("scores must be finite numbers between 0 and 100")
    weight = math.fsum(WEIGHTS[a] for a in available)
    lo = math.fsum(WEIGHTS[a] * value for a, value in available.items())
    interval = [lo, lo + sum(100 * WEIGHTS[a] for a in AXES if a not in available)]
    if blocked_reasons:
        return "BLOCKED", list(blocked_reasons), interval
    reasons = []
    if any(f.confirmed and f.severity == 3 for f in findings):
        reasons.append("critical_defect_confirmed")
    if any(f.confirmed and f.category == "pose_violation" for f in findings):
        reasons.append("pose_violation_confirmed")
    reasons.extend(f"{a}_below_60" for a in KEY_AXES if a in available and available[a] < 60)
    total = lo / weight if weight else None
    if total is not None and total < 70 and weight >= 0.6 - 1e-12:
        reasons.append("total_below_70")
    if reasons:
        return "FAIL", reasons, interval
    missing_keys = any(a not in available for a in KEY_AXES)
    if (
        total is not None
        and total >= 85
        and not missing_keys
        and all(available[a] >= 75 for a in KEY_AXES)
    ):
        return "PASS", [], interval
    if missing_keys:
        reasons.append("insufficient_reference_data")
    if len(available) < len(AXES):
        reasons.append("unavailable_axes")
    if weight < 0.6 - 1e-12:
        reasons.append("insufficient_evidence")
    if total is not None and total < 85:
        reasons.append("score_below_85" if total >= 70 else "low_score_insufficient_evidence")
    reasons.extend(
        f"{a}_boundary_60_75" for a in KEY_AXES if a in available and 60 <= available[a] < 75
    )
    return "REVIEW", reasons, interval


class ImageUnreadableError(ValueError):
    """The source could not be fully decoded as an image."""


def sha256_of_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def basic_image_info(path) -> dict:
    try:
        with Image.open(path) as image:
            image.load()
            return {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
            }
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ImageUnreadableError(str(exc)) from exc


def average_hash(path, hash_size=8) -> int:
    if hash_size < 1:
        raise ValueError("hash_size must be positive")
    with Image.open(path) as image:
        pixels = list(
            image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS).tobytes()
        )
    mean = sum(pixels) / len(pixels)
    result = 0
    for pixel in pixels:
        result = (result << 1) | int(pixel > mean)
    return result


def hamming_distance(a, b) -> int:
    return (a ^ b).bit_count()


class ScoreProvider(Protocol):
    def score(self, image_path, context: dict) -> dict[str, float | None]: ...


class NullScoreProvider:
    def score(self, image_path, context: dict) -> dict[str, float | None]:
        return dict.fromkeys(AXES)


def evaluate_image(
    image_path,
    *,
    attempt_id=None,
    reference_ids=None,
    provider=None,
    is_original=True,
    known_hashes: dict[str, int] | None = None,
) -> QualityEvaluation:
    record = QualityEvaluation(
        generation_attempt_id=attempt_id,
        reference_ids=reference_ids or {},
        image_is_original=is_original,
    )
    blocked = []
    try:
        record.image_sha256 = sha256_of_file(image_path)
        info = basic_image_info(image_path)
    except (ImageUnreadableError, OSError):
        blocked.append("image_unreadable")
    else:
        scorer = provider if provider is not None else NullScoreProvider()
        record.evaluator_versions = {"score_provider": type(scorer).__name__}
        supplied = scorer.score(
            image_path,
            {
                "reference_ids": record.reference_ids,
                "generation_attempt_id": attempt_id,
                "image_info": info,
            },
        )
        record.scores = {axis: supplied.get(axis) for axis in AXES}
        if known_hashes:
            image_hash = average_hash(image_path)
            for evaluation_id, known_hash in known_hashes.items():
                if hamming_distance(image_hash, known_hash) <= 5:
                    record.findings.append(
                        Finding(
                            category="duplicate",
                            severity=1,
                            evidence=f"Near duplicate of {evaluation_id}",
                            evaluators=["average_hash-v1"],
                        )
                    )
    record.unavailable_metrics = [a for a in AXES if record.scores[a] is None]
    record.gate, record.gate_reasons, record.score_interval = compute_gate(
        record.scores, record.findings, blocked
    )
    return record
