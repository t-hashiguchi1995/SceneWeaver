"""Manga font profiles and cached, auditable font evidence."""

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont

from creator_studio.application.image.speech_bubble import find_japanese_font

FONT_DIR = Path(__file__).resolve().parents[4] / "assets" / "fonts"
KIND_DEFAULTS = {
    "speech_bubble": "manga_dialogue",
    "inner_voice": "manga_inner",
    "narration": "narration",
    "sfx": "manga_sfx",
}
PROFILE_FILES = {
    "manga_dialogue": ("GenEiAntiqueNv6-M.ttf", "GenEiAntiquePv6-M.ttf"),
    "manga_inner": ("GenEiKoburiMin*.ttf", "GenEiKoburiMin*.otf"),
    "manga_shout": ("GenEiMGo*.ttf",),
    "manga_sfx": ("GenEiPople*.ttf",),
    "narration": (),
}


@dataclass(frozen=True)
class FontResolution:
    profile: str
    font_path: str
    font_file: str
    font_name: str
    font_version: str
    fallback: bool

    def to_dict(self):
        return asdict(self)


def canonical_profile(profile):
    return "manga_dialogue" if profile == "jp_manga_sans" else profile


@lru_cache(maxsize=32)
def _resolve(profile):
    candidates = [
        p
        for pattern in PROFILE_FILES.get(profile, ())
        for p in sorted(FONT_DIR.glob(pattern))
        if p.is_file()
    ]
    path = candidates[0] if candidates else find_japanese_font()
    with TTFont(path, fontNumber=0) as font:
        name = font["name"].getDebugName(1) or path.stem
        version = font["name"].getDebugName(5) or "unknown"
    return FontResolution(profile, str(path), path.name, name, version, not candidates)


def resolve_font(layer):
    return _resolve(canonical_profile(layer.font_profile or KIND_DEFAULTS[layer.kind]))


@lru_cache(maxsize=64)
def font_cmap(path):
    with TTFont(path, fontNumber=0) as font:
        return frozenset(font.getBestCmap() or {})
