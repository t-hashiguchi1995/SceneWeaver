from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageFilter

DEFAULT_FEATHER_PX = 8


def _open(data: bytes, mode: str) -> Image.Image:
    with Image.open(io.BytesIO(data)) as image:
        return image.convert(mode)


def _mask(data: bytes) -> Image.Image:
    return _open(data, "L").point(lambda v: 255 if v >= 128 else 0)


def _png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _dilate(mask: Image.Image, pixels: int) -> Image.Image:
    return mask.filter(ImageFilter.MaxFilter(2 * pixels + 1)) if pixels > 0 else mask


def composite_protected_background(
    anchor_bytes: bytes,
    generated_bytes: bytes,
    mask_bytes: bytes,
    *,
    feather_px: int = DEFAULT_FEATHER_PX,
) -> bytes:
    anchor = _open(anchor_bytes, "RGB")
    generated = _open(generated_bytes, "RGB")
    mask = _mask(mask_bytes)
    if anchor.size != generated.size or anchor.size != mask.size:
        raise ValueError("image size mismatch")
    alpha = mask
    if feather_px > 0:
        dil = _dilate(mask, feather_px)
        ero = mask.filter(ImageFilter.MinFilter(2 * feather_px + 1))
        blur = mask.filter(ImageFilter.GaussianBlur(feather_px))
        ramp = blur.point(
            lambda v: 0 if v <= 10 else 255 if v >= 245 else (v - 10) * 255 // 235
        )
        alpha = ImageChops.multiply(ramp, dil)
        alpha = ImageChops.lighter(alpha, ero)
    return _png(Image.composite(generated, anchor, alpha))


def build_edit_mask(subject_mask_bytes: bytes, *, dilation_px: int) -> bytes:
    return _png(_dilate(_mask(subject_mask_bytes), dilation_px))


def measure_protected_change(
    anchor_bytes: bytes,
    result_bytes: bytes,
    mask_bytes: bytes,
    *,
    feather_px: int = DEFAULT_FEATHER_PX,
) -> float:
    anchor = _open(anchor_bytes, "RGB")
    result = _open(result_bytes, "RGB")
    mask = _mask(mask_bytes)
    if anchor.size != result.size or anchor.size != mask.size:
        raise ValueError("image size mismatch")
    import numpy as np

    outside = np.asarray(_dilate(mask, feather_px)) == 0
    changed = np.any(np.asarray(anchor) != np.asarray(result), axis=2) & outside
    count = np.count_nonzero(outside)
    return float(np.count_nonzero(changed) / count) if count else 0.0
