#!/usr/bin/env python3
"""1:1 high-resolution Judge tile slicer and 4K-enforced deliverable promoter."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised via monkeypatch & system python
    Image = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[4]
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DEFAULT_4K_LONG_EDGE = 3840
DEFAULT_4K_UHD_SIZE = (3840, 2160)


def _three_overlapping_spans(length: int, span_ratio: float = 0.44) -> list[tuple[int, int]]:
    if length <= 0:
        raise ValueError(f"Image dimension must be positive, got {length}")
    span = max(1, min(length, round(length * span_ratio)))
    mid_start = (length - span) // 2
    return [
        (0, span),
        (mid_start, mid_start + span),
        (length - span, length),
    ]


def _sips_dimensions(image_path: Path) -> tuple[int, int]:
    proc = subprocess.run(
        ["/usr/bin/sips", "-g", "pixelWidth", "-g", "pixelHeight", str(image_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    w_match = re.search(r"pixelWidth:\s*(\d+)", proc.stdout)
    h_match = re.search(r"pixelHeight:\s*(\d+)", proc.stdout)
    if not w_match or not h_match:
        raise ValueError(f"Could not read image dimensions via sips for {image_path}")
    return int(w_match.group(1)), int(h_match.group(1))


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    if Image is not None:
        with Image.open(image_path) as img:
            return img.size
    return _sips_dimensions(image_path)


def slice_image(image_path: Path, out_dir: Path) -> dict[str, Any]:
    image_path = Path(image_path).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    file_size_bytes = image_path.stat().st_size

    tiles: list[dict[str, Any]] = []
    if Image is not None:
        with Image.open(image_path) as img:
            width, height = img.size
            x_spans = _three_overlapping_spans(width)
            y_spans = _three_overlapping_spans(height)
            for r_idx, (y0, y1) in enumerate(y_spans, start=1):
                for c_idx, (x0, x1) in enumerate(x_spans, start=1):
                    tile_id = f"row{r_idx}-col{c_idx}"
                    tile_path = out_dir / f"{tile_id}.png"
                    img.crop((x0, y0, x1, y1)).save(tile_path, format="PNG")
                    tiles.append(
                        {
                            "id": tile_id,
                            "box": [x0, y0, x1, y1],
                            "width": x1 - x0,
                            "height": y1 - y0,
                            "path": str(tile_path),
                        }
                    )
    else:
        width, height = _sips_dimensions(image_path)
        x_spans = _three_overlapping_spans(width)
        y_spans = _three_overlapping_spans(height)
        for r_idx, (y0, y1) in enumerate(y_spans, start=1):
            for c_idx, (x0, x1) in enumerate(x_spans, start=1):
                tile_id = f"row{r_idx}-col{c_idx}"
                tile_path = out_dir / f"{tile_id}.png"
                crop_w = x1 - x0
                crop_h = y1 - y0
                subprocess.run(
                    [
                        "/usr/bin/sips",
                        "-s",
                        "format",
                        "png",
                        "--cropOffset",
                        str(y0),
                        str(x0),
                        "-c",
                        str(crop_h),
                        str(crop_w),
                        str(image_path),
                        "--out",
                        str(tile_path),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                tiles.append(
                    {
                        "id": tile_id,
                        "box": [x0, y0, x1, y1],
                        "width": crop_w,
                        "height": crop_h,
                        "path": str(tile_path),
                    }
                )

    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = {
        "source_image": str(image_path),
        "width": width,
        "height": height,
        "is_4k": max(width, height) >= DEFAULT_4K_LONG_EDGE,
        "is_default_4k_uhd": (width, height) == DEFAULT_4K_UHD_SIZE,
        "aspect_ratio": round(width / height, 4),
        "file_size_bytes": file_size_bytes,
        "tiles": tiles,
        "manifest_path": str(manifest_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def sanitize_slug(slug: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    return cleaned[:80].strip("-") or "infographic"


def _is_true_png(path: Path) -> bool:
    with path.open("rb") as fp:
        return fp.read(8) == PNG_MAGIC


def promote_deliverable(
    src_image: Path,
    deliverables_dir: Path,
    slug: str,
    now: dt.datetime | None = None,
    *,
    require_4k: bool = False,
    min_long_edge: int = DEFAULT_4K_LONG_EDGE,
) -> Path:
    src_image = Path(src_image).resolve()
    width, height = get_image_dimensions(src_image)
    if require_4k and max(width, height) < min_long_edge:
        raise ValueError(
            f"Refusing to promote sub-4K image ({width}x{height}): expected long edge >= {min_long_edge} "
            f"(default 4K is 3840x2160). Render via render_infographic_4k.py first, or pass --allow-sub-4k "
            f"only if the user explicitly requested a lower resolution."
        )

    deliverables_dir = Path(deliverables_dir).resolve()
    deliverables_dir.mkdir(parents=True, exist_ok=True)

    ts = (now or dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
    clean_slug = sanitize_slug(slug)
    stem = f"{ts}-{clean_slug}"
    dest = deliverables_dir / f"{stem}.png"
    counter = 2
    while dest.exists():
        dest = deliverables_dir / f"{stem}-{counter}.png"
        counter += 1

    if _is_true_png(src_image):
        shutil.copy2(src_image, dest)
    elif Image is not None:
        with Image.open(src_image) as img:
            img.save(dest, format="PNG")
    else:
        subprocess.run(
            ["/usr/bin/sips", "-s", "format", "png", str(src_image), "--out", str(dest)],
            check=True,
            capture_output=True,
            timeout=30,
        )
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slice candidate renders into 9 overlapping 1:1 tiles or promote approved 4K renders to deliverables/."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_slice = sub.add_parser("slice", help="Slice a 4K render into 9 overlapping 1:1 PNG tiles.")
    p_slice.add_argument("image_path", type=Path, help="Candidate render image path")
    p_slice.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / ".scratch" / "judge-crops" / "latest",
        help="Output directory for 1:1 PNG tiles and manifest.json",
    )

    p_promote = sub.add_parser("promote", help="Copy an approved 4K render to deliverables/YYYYMMDD-HHMMSS-<slug>.png.")
    p_promote.add_argument("image_path", type=Path, help="Approved render image path")
    p_promote.add_argument("--slug", required=True, help="Short descriptive topic slug")
    p_promote.add_argument(
        "--deliverables-dir",
        type=Path,
        default=REPO_ROOT / "deliverables",
        help="Destination deliverables directory (default: <repo>/deliverables)",
    )
    p_promote.add_argument(
        "--allow-sub-4k",
        action="store_true",
        help="Allow promoting an image smaller than 4K (ONLY when explicitly requested by the user).",
    )

    args = parser.parse_args()
    if args.cmd == "slice":
        manifest = slice_image(args.image_path, args.out_dir)
        print(json.dumps(manifest, indent=2))
    elif args.cmd == "promote":
        dest = promote_deliverable(
            args.image_path,
            args.deliverables_dir,
            args.slug,
            require_4k=not args.allow_sub_4k,
        )
        w, h = get_image_dimensions(dest)
        print(json.dumps({"deliverable_path": str(dest), "width": w, "height": h}, indent=2))


if __name__ == "__main__":
    main()
