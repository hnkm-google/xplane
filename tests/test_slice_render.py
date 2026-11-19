import datetime as dt
import importlib.util
import io
import subprocess
import sys
from pathlib import Path
import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".agents/skills/xplane-infographic-studio/scripts/slice_render_for_judge.py"
RENDER_SCRIPT_PATH = REPO_ROOT / ".agents/skills/xplane-infographic-studio/scripts/render_infographic_4k.py"


def load_module(path: Path = SCRIPT_PATH, name: str = "slice_render_for_judge"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_slice_image_creates_9_overlapping_1to1_tiles_covering_entire_canvas(tmp_path: Path):
    mod = load_module()
    src = tmp_path / "render.png"
    img = Image.new("RGB", (3840, 2160), (240, 245, 250))
    # Plant a distinct 1px marker near an interior seam to verify overlap & 1:1 crop fidelity
    img.putpixel((1550, 880), (255, 0, 128))
    img.save(src)

    manifest = mod.slice_image(src, tmp_path / "tiles")
    assert manifest["width"] == 3840
    assert manifest["height"] == 2160
    assert manifest["is_4k"] is True
    assert manifest["is_default_4k_uhd"] is True
    assert len(manifest["tiles"]) == 9

    # Verify full X and Y span coverage and positive overlap between adjacent tiles
    xs = sorted({tuple(t["box"][::2]) for t in manifest["tiles"]})
    ys = sorted({tuple(t["box"][1::2]) for t in manifest["tiles"]})
    assert xs[0][0] == 0 and xs[-1][1] == 3840
    assert ys[0][0] == 0 and ys[-1][1] == 2160
    assert xs[0][1] - xs[1][0] >= 350  # >= ~10% horizontal overlap at 4K
    assert ys[0][1] - ys[1][0] >= 200  # >= ~10% vertical overlap at 4K

    # Verify 1:1 native pixel preservation (no downscaling)
    marker_hits = 0
    for tile in manifest["tiles"]:
        x0, y0, x1, y1 = tile["box"]
        with Image.open(tile["path"]) as cropped:
            assert cropped.size == (x1 - x0, y1 - y0)
            if x0 <= 1550 < x1 and y0 <= 880 < y1:
                assert cropped.getpixel((1550 - x0, 880 - y0)) == (255, 0, 128)
                marker_hits += 1
    assert marker_hits >= 1


def test_promote_deliverable_sanitizes_slug_and_avoids_overwrite(tmp_path: Path):
    mod = load_module()
    src = tmp_path / "clean.png"
    Image.new("RGB", (100, 100), "white").save(src)
    deliv = tmp_path / "deliverables"
    fixed_now = dt.datetime(2026, 11, 17, 15, 30, 45)

    p1 = mod.promote_deliverable(src, deliv, "Aether / Cloud: 60-Day Journey!", now=fixed_now)
    p2 = mod.promote_deliverable(src, deliv, "Aether / Cloud: 60-Day Journey!", now=fixed_now)

    assert p1.name == "20261117-153045-aether-cloud-60-day-journey.png"
    assert p2.name == "20261117-153045-aether-cloud-60-day-journey-2.png"
    assert p1.is_file() and p2.is_file()


def test_promote_cli_rejects_sub_4k_by_default_and_accepts_3840x2160(tmp_path: Path):
    mod = load_module()
    sub_4k = tmp_path / "sub4k.png"
    Image.new("RGB", (1376, 768), "white").save(sub_4k)

    with pytest.raises(ValueError, match="Refusing to promote sub-4K image"):
        mod.promote_deliverable(sub_4k, tmp_path / "deliverables", "too-small", require_4k=True)

    cli_fail = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "promote", str(sub_4k), "--slug", "too-small", "--deliverables-dir", str(tmp_path / "d1")],
        capture_output=True,
        text=True,
    )
    assert cli_fail.returncode != 0
    assert "sub-4K" in cli_fail.stderr or "sub-4K" in cli_fail.stdout

    full_4k = tmp_path / "uhd4k.png"
    Image.new("RGB", (3840, 2160), "white").save(full_4k)
    cli_ok = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "promote", str(full_4k), "--slug", "uhd-ok", "--deliverables-dir", str(tmp_path / "d2")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"width": 3840' in cli_ok.stdout
    assert '"height": 2160' in cli_ok.stdout


def test_render_infographic_4k_normalizes_to_default_3840x2160_png(tmp_path: Path):
    rmod = load_module(RENDER_SCRIPT_PATH, "render_infographic_4k")
    assert rmod.compute_target_dimensions("16:9") == (3840, 2160)
    assert rmod.compute_target_dimensions("4:3") == (3840, 2880)
    assert rmod.compute_target_dimensions("16:9", width=4128, height=2304) == (4128, 2304)

    buf = io.BytesIO()
    Image.new("RGB", (5504, 3072), (12, 34, 56)).save(buf, format="JPEG")
    out_png = tmp_path / "normalized-4k.png"
    meta = rmod.normalize_to_target_png(buf.getvalue(), (3840, 2160), out_png)
    assert meta["raw_width"] == 5504 and meta["raw_height"] == 3072
    assert meta["width"] == 3840 and meta["height"] == 2160
    assert meta["logo_applied"] is False
    assert out_png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(out_png) as saved:
        assert saved.size == (3840, 2160)


def test_render_infographic_4k_applies_any_logo_png_proportionally_without_whiteout(tmp_path: Path):
    rmod = load_module(RENDER_SCRIPT_PATH, "render_infographic_4k")

    # 1. Transparent wide wordmark logo
    wide_logo = tmp_path / "wide_logo.png"
    logo_rgba = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
    for x in range(50, 550):
        for y in range(30, 170):
            logo_rgba.putpixel((x, y), (45, 26, 107, 255))
    logo_rgba.save(wide_logo)

    buf = io.BytesIO()
    Image.new("RGB", (3840, 2160), (251, 249, 244)).save(buf, format="PNG")
    out_wide = tmp_path / "with_wide_logo.png"
    meta_wide = rmod.normalize_to_target_png(buf.getvalue(), (3840, 2160), out_wide, logo_path=wide_logo)
    assert meta_wide["logo_applied"] is True
    assert 250 <= meta_wide["logo_width"] <= 460
    assert 80 <= meta_wide["logo_height"] <= 140

    # 2. Opaque white-ground square emblem onto warm cream paper (must key white corners seamlessly)
    sq_logo = tmp_path / "square_opaque_logo.png"
    sq_rgb = Image.new("RGB", (400, 400), (255, 255, 255))
    for x in range(100, 300):
        for y in range(100, 300):
            sq_rgb.putpixel((x, y), (200, 40, 60))
    sq_rgb.save(sq_logo)

    out_sq = tmp_path / "with_sq_logo.png"
    meta_sq = rmod.normalize_to_target_png(buf.getvalue(), (3840, 2160), out_sq, logo_path=sq_logo)
    assert meta_sq["logo_applied"] is True
    assert 120 <= meta_sq["logo_width"] <= 160
    assert meta_sq["logo_width"] == meta_sq["logo_height"]
    with Image.open(out_sq) as composited:
        x0, y0, x1, y1 = meta_sq["logo_box"]
        # Center of emblem is crimson; just outside box remains warm cream (#FBF9F4), never pure white (#FFFFFF)
        assert composited.getpixel(((x0 + x1) // 2, (y0 + y1) // 2)) == (200, 40, 60)
        assert composited.getpixel((x0 - 5, y0 + 5)) == (251, 249, 244)


def test_promote_converts_mislabeled_jpeg_to_png_and_sips_fallback_works(tmp_path: Path, monkeypatch):
    mod = load_module()
    mislabeled = tmp_path / "attempt-1.png"
    # Save JPEG bytes under a .png filename (common image-tool artifact)
    Image.new("RGB", (600, 400), (20, 40, 80)).save(mislabeled, format="JPEG")
    assert not mislabeled.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    promoted = mod.promote_deliverable(mislabeled, tmp_path / "deliverables", "format-check")
    assert promoted.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    # Verify manifest includes file_size_bytes and works via macOS sips when PIL.Image is absent
    monkeypatch.setattr(mod, "Image", None)
    manifest = mod.slice_image(promoted, tmp_path / "sips-tiles")
    assert manifest["width"] == 600
    assert manifest["height"] == 400
    assert manifest["is_4k"] is False
    assert manifest["file_size_bytes"] == promoted.stat().st_size
    assert len(manifest["tiles"]) == 9
    for t in manifest["tiles"]:
        p = Path(t["path"])
        assert p.is_file() and p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
