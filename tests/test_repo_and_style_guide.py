from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DEFECTS = [
    "defect-01-border-clipped-by-text-bg.png",
    "defect-02-text-bg-cuts-path-shadow.jpg",
    "defect-03-text-bg-cuts-bridge-wash.jpg",
    "defect-04-text-bg-erases-card-border.png",
    "defect-05-text-bg-covers-signboard-border.png",
]


def test_gitignore_excludes_scratch_and_pytest_cache():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".scratch/" in gitignore
    assert ".pytest_cache/" in gitignore


def test_anti_pattern_crops_exist_and_open_cleanly():
    anti_dir = REPO_ROOT / "docs" / "anti-patterns"
    for name in EXPECTED_DEFECTS:
        path = anti_dir / name
        assert path.is_file(), f"Missing {path}"
        with Image.open(path) as img:
            w, h = img.size
            assert w > 20 and h > 20


def test_style_guide_covers_presets_anchors_and_guardrails():
    guide = (REPO_ROOT / "docs" / "STYLE_GUIDE.md").read_text(encoding="utf-8")
    for preset in tuple(f"S{i}" for i in range(1, 17)):
        assert preset in guide, f"Missing preset {preset} in STYLE_GUIDE.md"
    assert "S17" not in guide
    assert "ukiyo-e" not in guide.lower()
    assert "miyazaki" not in guide.lower()
    assert "ghibli" not in guide.lower()
    assert "tatami" in guide.lower()
    for xplane_file in (REPO_ROOT / "assets" / "XPLANE").iterdir():
        if not xplane_file.name.startswith("."):
            assert xplane_file.name in guide, f"Unmapped XPLANE reference: {xplane_file.name}"
    for defect in EXPECTED_DEFECTS:
        assert defect in guide
    assert "watermark" in guide.lower()
    assert "3d pie" in guide.lower()
