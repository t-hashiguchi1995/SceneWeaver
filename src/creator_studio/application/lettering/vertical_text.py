"""Vertical columns with simplified JIS kinsoku and bounded font fitting."""

import math
from dataclasses import dataclass

from creator_studio.application.image.speech_bubble import wrap_text

START_FORBIDDEN = set(
    "、。，．！？：；」』）】〕〉》ー・ぁぃぅぇぉゃゅょゎァィゥェォャュョヮっッ…‥ゝゞ々"
)
END_FORBIDDEN = set("「『（〔【〈《")


@dataclass
class VerticalLayout:
    columns: list[str]
    font_px: int
    feasible: bool


def _columns(text, capacity):
    columns = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            if len(current) >= capacity and char not in START_FORBIDDEN:
                pulled = ""
                while current and current[-1] in END_FORBIDDEN:
                    pulled = current[-1] + pulled
                    current = current[:-1]
                if current:
                    columns.append(current)
                current = pulled
            current += char
        columns.append(current)
    return columns


def layout_vertical(text, *, font_px, box_w_px, box_h_px, min_font_px=21):
    size = max(min_font_px, font_px)
    while True:
        advance = size * 1.12
        columns = _columns(text, max(1, math.floor(box_h_px / advance)))
        feasible = len(columns) * advance <= box_w_px
        # A box must accommodate at least one full cell, even for short text.
        feasible = feasible and box_h_px >= advance
        if feasible or size == min_font_px:
            return VerticalLayout(columns, size, feasible)
        size = max(min_font_px, size - 2)


def layout_horizontal(text, font, box_w_px):
    return wrap_text(text, font, max(1, box_w_px))
