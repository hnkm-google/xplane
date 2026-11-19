#!/usr/bin/env python3
"""Deterministic 4K infographic renderer backed by google-genai (default: 3840x2160 PNG)
with automatic brand logo compositing whenever assets/logo.png is present.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_LOGO_PATH = REPO_ROOT / "assets" / "logo.png"
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
FALLBACK_MODEL = "gemini-3-pro-image-preview"

# Default exact 4K target dimensions by aspect ratio (long edge = 3840 unless overridden)
ASPECT_TO_4K_SIZE: dict[str, tuple[int, int]] = {
    "16:9": (3840, 2160),
    "9:16": (2160, 3840),
    "4:3": (3840, 2880),
    "3:4": (2880, 3840),
    "3:2": (3840, 2560),
    "2:3": (2560, 3840),
    "1:1": (3840, 3840),
    "21:9": (3840, 1646),
}


def compute_target_dimensions(
    aspect_ratio: str = "16:9",
    width: int | None = None,
    height: int | None = None,
) -> tuple[int, int]:
    if width is not None and height is not None:
        if width <= 0 or height <= 0:
            raise ValueError(f"Target dimensions must be positive, got {width}x{height}")
        return width, height
    if aspect_ratio in ASPECT_TO_4K_SIZE:
        return ASPECT_TO_4K_SIZE[aspect_ratio]
    raise ValueError(
        f"Unsupported aspect ratio {aspect_ratio!r}. Choose from {sorted(ASPECT_TO_4K_SIZE)} or pass --width and --height."
    )


def _prepare_logo_rgba(logo_img: Image.Image) -> Image.Image:
    rgba = logo_img.convert("RGBA")
    w, h = rgba.size
    if w <= 0 or h <= 0:
        raise ValueError("Logo image has invalid zero dimensions.")

    alpha = rgba.getchannel("A")
    min_a, _ = alpha.getextrema()
    if min_a < 250:
        mask = alpha.point(lambda a: 255 if a > 4 else 0)
        bbox = mask.getbbox()
        return rgba.crop(bbox) if bbox else rgba

    # Opaque logo fallback: if all 4 corners are uniform near-white, smoothly key background to alpha
    corners = [rgba.getpixel((0, 0)), rgba.getpixel((w - 1, 0)), rgba.getpixel((0, h - 1)), rgba.getpixel((w - 1, h - 1))]
    is_light_bg = all(min(px[:3]) >= 242 and (max(px[:3]) - min(px[:3])) <= 14 for px in corners)
    if not is_light_bg:
        return rgba

    bg_r = sum(px[0] for px in corners) // 4
    bg_g = sum(px[1] for px in corners) // 4
    bg_b = sum(px[2] for px in corners) // 4
    get_pixels = getattr(rgba, "get_flattened_data", rgba.getdata)
    pixels = list(get_pixels())
    keyed: list[tuple[int, int, int, int]] = []
    for r, g, b, _ in pixels:
        dist = max(abs(r - bg_r), abs(g - bg_g), abs(b - bg_b))
        if dist <= 8:
            new_a = 0
        elif dist >= 28:
            new_a = 255
        else:
            new_a = round((dist - 8) * 255 / 20)
        keyed.append((r, g, b, new_a))

    out = Image.new("RGBA", (w, h))
    out.putdata(keyed)
    mask = out.getchannel("A").point(lambda a: 255 if a > 4 else 0)
    bbox = mask.getbbox()
    return out.crop(bbox) if bbox else out


def apply_brand_logo(
    canvas_img: Image.Image,
    logo_path: Path,
    *,
    position: str = "top-right",
) -> tuple[Image.Image, dict[str, Any]]:
    logo_path = Path(logo_path).resolve()
    canvas_w, canvas_h = canvas_img.size

    with Image.open(logo_path) as raw_logo:
        prepared = _prepare_logo_rgba(raw_logo)

    trim_w, trim_h = prepared.size
    aspect = trim_w / max(1, trim_h)
    if aspect >= 1.8:
        max_w = round(canvas_w * 0.115)
        max_h = round(canvas_h * 0.056)
    else:
        max_w = round(canvas_w * 0.090)
        max_h = round(canvas_h * 0.068)

    scale = min(max_w / max(1, trim_w), max_h / max(1, trim_h))
    new_w = max(1, round(trim_w * scale))
    new_h = max(1, round(trim_h * scale))
    resized_logo = prepared.resize((new_w, new_h), Image.Resampling.LANCZOS)

    margin_x = round(canvas_w * 0.025)
    masthead_band_h = round(canvas_h * 0.098)
    min_top = round(canvas_h * 0.020)
    y0 = max(min_top, (masthead_band_h - new_h) // 2)
    if position == "top-left":
        x0 = margin_x
    elif position == "top-right":
        x0 = canvas_w - margin_x - new_w
    else:
        raise ValueError(f"Unsupported logo position {position!r}; choose 'top-right' or 'top-left'.")

    composited = canvas_img.convert("RGBA")
    composited.alpha_composite(resized_logo, dest=(x0, y0))
    info = {
        "logo_applied": True,
        "logo_path": str(logo_path),
        "logo_position": position,
        "logo_box": [x0, y0, x0 + new_w, y0 + new_h],
        "logo_width": new_w,
        "logo_height": new_h,
    }
    return composited.convert("RGB"), info


def normalize_to_target_png(
    raw_image_bytes: bytes,
    target_size: tuple[int, int],
    out_path: Path,
    *,
    logo_path: Path | None = None,
    logo_position: str = "top-right",
) -> dict[str, Any]:
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(raw_image_bytes)) as img:
        raw_w, raw_h = img.size
        rgb = img.convert("RGB")
        if (raw_w, raw_h) != target_size:
            rgb = rgb.resize(target_size, Image.Resampling.LANCZOS)

    logo_meta: dict[str, Any] = {"logo_applied": False, "logo_path": None}
    if logo_path is not None and Path(logo_path).is_file():
        rgb, logo_meta = apply_brand_logo(rgb, Path(logo_path), position=logo_position)

    rgb.save(out_path, format="PNG", optimize=False)

    return {
        "output_path": str(out_path),
        "raw_width": raw_w,
        "raw_height": raw_h,
        "width": target_size[0],
        "height": target_size[1],
        "file_size_bytes": out_path.stat().st_size,
        **logo_meta,
    }


def resolve_default_logo_path(explicit_logo: Path | None = None, disable_logo: bool = False) -> Path | None:
    if disable_logo:
        return None
    if explicit_logo is not None:
        resolved = Path(explicit_logo).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Explicit --logo file does not exist: {resolved}")
        return resolved
    if DEFAULT_LOGO_PATH.is_file():
        return DEFAULT_LOGO_PATH.resolve()
    return None


def render_4k_infographic(
    prompt: str,
    out_path: Path,
    *,
    aspect_ratio: str = "16:9",
    width: int | None = None,
    height: int | None = None,
    model: str = DEFAULT_MODEL,
    ref_images: list[Path] | None = None,
    logo_path: Path | None = None,
    disable_logo: bool = False,
    logo_position: str = "top-right",
    max_retries: int = 3,
) -> dict[str, Any]:
    if not prompt or not prompt.strip():
        raise ValueError("Render prompt must not be empty.")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise RuntimeError("Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set in the environment.")

    from google import genai
    from google.genai import types

    target_size = compute_target_dimensions(aspect_ratio=aspect_ratio, width=width, height=height)
    effective_logo = resolve_default_logo_path(explicit_logo=logo_path, disable_logo=disable_logo)
    client = genai.Client()

    contents: list[Any] = []
    for ref in ref_images or []:
        ref_path = Path(ref).resolve()
        with Image.open(ref_path) as pil_ref:
            contents.append(pil_ref.copy())
    contents.append(prompt.strip())

    models_to_try = [model]
    if model != FALLBACK_MODEL:
        models_to_try.append(FALLBACK_MODEL)

    last_err: Exception | None = None
    for active_model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.models.generate_content(
                    model=active_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size="4K",
                        ),
                    ),
                )
                for candidate in resp.candidates or []:
                    if not candidate.content:
                        continue
                    for part in candidate.content.parts or []:
                        if part.inline_data and part.inline_data.data:
                            meta = normalize_to_target_png(
                                part.inline_data.data,
                                target_size,
                                out_path,
                                logo_path=effective_logo,
                                logo_position=logo_position,
                            )
                            meta["model"] = active_model
                            meta["aspect_ratio"] = aspect_ratio
                            return meta
                raise RuntimeError(f"Model {active_model} returned no inline image bytes.")
            except Exception as exc:  # pragma: no cover - network/rate-limit retry path
                last_err = exc
                if attempt < max_retries:
                    time.sleep(4 * attempt)
                else:
                    break

    raise RuntimeError(f"Failed to render 4K infographic after retries: {last_err}") from last_err


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a native 4K XPLANE infographic via google-genai (default: 3840x2160 PNG + auto assets/logo.png)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", type=str, help="Inline text prompt")
    group.add_argument("--prompt-file", type=Path, help="UTF-8 file containing the render prompt")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path (e.g., .scratch/renders/attempt-1.png)")
    parser.add_argument("--aspect-ratio", type=str, default="16:9", help="Aspect ratio (default: 16:9 -> 3840x2160)")
    parser.add_argument("--width", type=int, default=None, help="Optional custom output width override")
    parser.add_argument("--height", type=int, default=None, help="Optional custom output height override")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Gemini image model (default: {DEFAULT_MODEL})")
    parser.add_argument("--ref-image", type=Path, action="append", default=[], help="Optional reference image(s)")
    parser.add_argument("--logo", type=Path, default=None, help="Explicit logo file override (defaults to assets/logo.png if present)")
    parser.add_argument("--logo-position", choices=["top-right", "top-left"], default="top-right", help="Masthead corner for logo placement")
    parser.add_argument("--no-logo", action="store_true", help="Disable automatic assets/logo.png compositing")

    args = parser.parse_args()
    prompt_text = args.prompt if args.prompt is not None else args.prompt_file.read_text(encoding="utf-8")
    result = render_4k_infographic(
        prompt=prompt_text,
        out_path=args.out,
        aspect_ratio=args.aspect_ratio,
        width=args.width,
        height=args.height,
        model=args.model,
        ref_images=args.ref_image,
        logo_path=args.logo,
        disable_logo=args.no_logo,
        logo_position=args.logo_position,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(json.dumps({"error": str(err)}), file=sys.stderr)
        sys.exit(1)
