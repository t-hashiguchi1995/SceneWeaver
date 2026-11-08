"""JSON-compatible editable lettering records."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field


@dataclass
class LetteringLayer:
    kind: str
    block_id: str
    text: str
    speaker_id: str | None = None
    bbox_xyxy_norm: tuple[float, float, float, float] | None = None
    anchor_xy_norm: tuple[float, float] | None = None
    writing_mode: str | None = None
    shape: str | None = None
    reading_order: int = 0
    font_profile: str = "jp_manga_sans"
    min_font_px: int = 21

    font_px: int | None = None
    fit_feasible: bool | None = None
    text_overflow: bool = False

    tail_mode: str = "auto"
    tail_tip_xy_norm: tuple[float, float] | None = None

    def __post_init__(self):
        if self.tail_mode not in {"auto", "none"}:
            raise ValueError("Invalid tail mode")
        if self.kind not in {"speech_bubble", "inner_voice", "narration", "sfx"}:
            raise ValueError("Invalid lettering kind")
        if self.writing_mode is None:
            self.writing_mode = (
                "vertical-rl" if self.kind in {"speech_bubble", "inner_voice"} else "horizontal"
            )
        if self.shape is None:
            self.shape = {"speech_bubble": "oval", "narration": "rect"}.get(self.kind, "none")
        if self.writing_mode not in {"vertical-rl", "horizontal"}:
            raise ValueError("Invalid writing mode")
        if self.shape not in {"oval", "cloud", "jagged", "rect", "none"}:
            raise ValueError("Invalid shape")
        if self.min_font_px < 1:
            raise ValueError("min_font_px must be positive")
        for name, length in (("bbox_xyxy_norm", 4), ("anchor_xy_norm", 2), ("tail_tip_xy_norm", 2)):
            value = getattr(self, name)
            if value is not None:
                if len(value) != length or any(
                    not math.isfinite(v) or not 0 <= v <= 1 for v in value
                ):
                    raise ValueError(f"Invalid {name}")
                setattr(self, name, tuple(value))
        if self.bbox_xyxy_norm is not None:
            x1, y1, x2, y2 = self.bbox_xyxy_norm
            if x1 >= x2 or y1 >= y2:
                raise ValueError("bbox must have positive area")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class LetteringLayout:
    layout_id: str
    image_asset_id: str
    canvas: dict[str, int]
    layers: list[LetteringLayer] = field(default_factory=list)
    style_profile: str = "jp_manga_classic"
    warnings: list[str] = field(default_factory=list)
    render_mode: str = "pillow_png"
    revision: int = 1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**{**data, "layers": [LetteringLayer.from_dict(v) for v in data["layers"]]})
