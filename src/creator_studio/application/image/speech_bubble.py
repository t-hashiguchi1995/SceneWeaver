"""Framework-independent Japanese speech-bubble compositing with Pillow."""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

BubblePosition = Literal["top-right", "top-left", "bottom-right", "bottom-left"]
POSITIONS = {"top-right", "top-left", "bottom-right", "bottom-left"}
FONT_ROOTS = (Path("/usr/share/fonts"), Path("/usr/local/share/fonts"))


def find_japanese_font() -> Path:
    """Search known Japanese-capable families rather than silently rendering tofu."""
    candidates = []
    for root in FONT_ROOTS:
        for path in root.rglob("*"):
            name = path.name.lower().replace("-", "").replace("_", "")
            if path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
                continue
            if "notosansjp" in name or "notosanscjk" in name:
                rank = 0
            elif name.startswith(("ipag.", "ipagp.")) or "ipagothic" in name:
                rank = 1
            elif "droidsansfallback" in name or "unifont" in name:
                rank = 2
            else:
                continue
            candidates.append((rank, str(path)))
    for _, filename in sorted(candidates):
        try:
            ImageFont.truetype(filename, 20)
            return Path(filename)
        except OSError:
            continue
    raise RuntimeError("No Japanese-capable font found. Install Noto Sans CJK or IPA Gothic.")


def wrap_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Wrap by Japanese character count, checking actual glyph widths as well."""
    count = max(1, int(width / max(1, font.getlength("あ"))))
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            if current and (len(current) >= count or font.getlength(current + char) > width):
                lines.append(current)
                current = ""
            current += char
        lines.append(current)
    return lines


def bubble_layout(
    text: str, font_path: Path, width: int, height: int
) -> tuple[ImageFont.FreeTypeFont, list[str], int, int, int, int, int]:
    max_width = math.floor(width * 0.55)
    max_height = math.floor(height * 0.30)
    for size in range(max(1, int(width / 28)), 0, -1):
        font = ImageFont.truetype(str(font_path), size)
        padding = max(2, round(size * 0.55))
        tail = max(2, round(size * 0.65))
        available = max_width - 2 * padding
        if available <= 0:
            continue
        lines = wrap_text(text, font, available)
        ascent, descent = font.getmetrics()
        advance = ascent + descent + max(1, round(size * 0.15))
        text_height = len(lines) * advance
        actual_width = math.ceil(max(font.getlength(s) for s in lines))
        body_height = text_height + padding * 2
        if actual_width <= available and body_height + tail <= max_height:
            return font, lines, actual_width + 2 * padding, body_height, padding, tail, advance
    raise ValueError("Text cannot fit the image's bubble limits.")


def _draw_bubble(image: Image.Image, text: str, position: str, font_path: Path) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    font, lines, bw, bh, pad, tail, advance = bubble_layout(text, font_path, width, height)
    stroke = max(1, round(width / 440))
    margin = max(stroke + 1, round(min(width, height) * 0.025))
    right = position.endswith("right")
    top = position.startswith("top")
    x = width - margin - bw if right else margin
    y = margin if top else height - margin - bh
    draw = ImageDraw.Draw(image)
    radius = min(round(font.size * 0.65), bw // 4, bh // 4)
    draw.rounded_rectangle(
        (x, y, x + bw, y + bh), radius=radius, fill="white", outline="black", width=stroke
    )
    center = x + bw * (0.32 if right else 0.68)
    half = min(tail * 0.65, bw * 0.12)
    edge = y + bh if top else y
    tip = (center + (tail * 0.3 if right else -tail * 0.3), edge + (tail if top else -tail))
    left, right_point = (center - half, edge), (center + half, edge)
    draw.polygon([left, tip, right_point], fill="white")
    draw.line([left, tip, right_point], fill="black", width=stroke, joint="curve")
    # Erase the rectangle's outline across the tail's base for a joined silhouette.
    inset = stroke / 2 + 1
    draw.line(
        [(center - half + inset, edge), (center + half - inset, edge)],
        fill="white",
        width=stroke + 1,
    )
    for index, line in enumerate(lines):
        draw.text((x + pad, y + pad + index * advance), line, font=font, fill="black", anchor="lt")
    return image


def composite_speech_bubble(
    source: bytes | str | Path, text: str, position: BubblePosition = "top-right"
) -> bytes:
    """Return a PNG of the same dimensions, shrinking text to fit the bubble.

    Raise ValueError if input is invalid or text cannot fit even at one pixel.
    Raise RuntimeError if no Japanese-capable font is installed.
    """
    if position not in POSITIONS:
        raise ValueError(f"Invalid bubble position: {position}")
    if not text.strip():
        raise ValueError("Speech-bubble text must not be empty")
    font_path = find_japanese_font()
    with Image.open(BytesIO(source) if isinstance(source, bytes) else source) as image:
        result = _draw_bubble(image, text, position, font_path)
    output = BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
