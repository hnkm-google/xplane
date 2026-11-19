import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_frontmatter(md_path: Path) -> tuple[dict[str, str], str]:
    text = md_path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"Missing frontmatter in {md_path}"
    _, fm_block, body = text.split("---", 2)
    keys = {}
    for line in fm_block.strip().splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            keys[k.strip()] = v.strip()
    return keys, body


def test_agents_md_and_readme_enforce_4k_and_zero_slideware():
    agents_md = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "xplane-infographic-studio" in agents_md
    assert "assets/XPLANE" in agents_md
    assert "another high-reasoning model" in agents_md.lower()
    assert "3840 × 2160" in agents_md
    assert "SLIDEWARE" in agents_md.upper()
    assert "render_infographic_4k.py" in agents_md
    assert "logo.png" in agents_md

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/" in readme and "deliverables/" in readme
    for i in range(1, 17):
        assert f"S{i}" in readme, f"Missing S{i} in README.md"
    assert "S17" not in readme
    assert "ukiyo-e" not in readme.lower()
    assert "miyazaki" not in readme.lower()
    assert "ghibli" not in readme.lower()
    assert "miyazaki" not in agents_md.lower()
    assert "ghibli" not in agents_md.lower()
    expected_samples = (
        "s1-isometric-cutaway-governance.png",
        "s2-concentric-ecosystem-governance.png",
        "s3-mission-control-governance.png",
        "s4-kinetic-machinery-governance.png",
        "s5-watercolor-journey-governance.png",
        "s6-vellum-blueprint-governance.png",
        "s7-tatami-pop-governance.png",
        "s8-ligne-claire-governance.png",
        "s9-encyclopedia-cutaway-governance.png",
        "s10-dollhouse-elevation-governance.png",
        "s11-midcentury-screenprint-governance.png",
        "s12-apollo-cutaway-governance.png",
        "s13-risograph-zine-governance.png",
        "s14-steampunk-clockwork-governance.png",
        "s15-botanical-watershed-governance.png",
        "s16-wimmelbilder-intricate-governance.png",
    )
    for sample_name in expected_samples:
        assert f"%28sample%20you%20can%20delete%29%20{sample_name}" in readme
        assert (REPO_ROOT / "deliverables" / f"(sample you can delete) {sample_name}").is_file()
    assert "YYYYMMDD-HHMMSS-<topic-slug>.png" in readme
    assert "3840 × 2160" in readme
    assert "SLIDEWARE" in readme.upper()

    assert "S16" in agents_md and "S17" not in agents_md


def test_skill_and_agent_definitions_enforce_4k_and_anti_slideware_gate():
    skill_fm, skill_body = _parse_frontmatter(
        REPO_ROOT / ".agents/skills/xplane-infographic-studio/SKILL.md"
    )
    assert skill_fm["name"] == "xplane-infographic-studio"
    assert skill_fm.get("description")
    assert "another high-reasoning model" in skill_body.lower()
    for required in (
        "ingest_assets.py",
        "render_infographic_4k.py",
        "slice_render_for_judge.py",
        "docs/STYLE_GUIDE.md",
        "3840 × 2160",
        "Gate 0",
        "Checkpoint 1",
        "Checkpoint 2",
        "S16",
    ):
        assert required in skill_body
    assert "S17" not in skill_body
    assert "miyazaki" not in skill_body.lower() and "ghibli" not in skill_body.lower()

    spec_fm, spec_body = _parse_frontmatter(REPO_ROOT / ".agents/agents/infographic-specialist.md")
    judge_fm, judge_body = _parse_frontmatter(REPO_ROOT / ".agents/agents/infographic-judge.md")
    assert spec_fm["name"] == "infographic-specialist"
    assert "SLIDEWARE" in spec_body.upper()
    assert "3840 × 2160" in spec_body
    assert "S16" in spec_body and "S17" not in spec_body and "ukiyo-e" not in spec_body.lower()
    assert "miyazaki" not in spec_body.lower() and "ghibli" not in spec_body.lower()

    assert judge_fm["name"] == "infographic-judge"
    assert "S16" in judge_body and "S17" not in judge_body and "woodblock" not in judge_body.lower()
    assert "miyazaki" not in judge_body.lower() and "ghibli" not in judge_body.lower()
    for gate in (
        "Gate 0",
        "Gate A",
        "Gate B",
        "SLIDEWARE",
        "defect-01-border-clipped-by-text-bg.png",
        "row1-col1",
    ):
        assert gate in judge_body or gate in judge_body.upper()


def test_end_to_end_cli_smoke_against_real_workspace_assets(tmp_path: Path):
    ingest = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / ".agents/skills/xplane-infographic-studio/scripts/ingest_assets.py"),
            "--assets-dir",
            str(REPO_ROOT / "assets"),
            "--out-dir",
            str(tmp_path / "extracted"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(ingest.stdout)
    rels = {f["rel_path"] for f in summary["files"]}
    assert not any(r.lower().startswith("xplane/") for r in rels)
    if (REPO_ROOT / "assets" / "logo.png").is_file():
        assert summary["logo_path"] == str((REPO_ROOT / "assets" / "logo.png").resolve())
        logo_entries = [f for f in summary["files"] if f["rel_path"] == "logo.png"]
        assert len(logo_entries) == 1 and logo_entries[0]["role"] == "brand_logo"

    candidates = [
        p
        for p in sorted((REPO_ROOT / "deliverables").rglob("*"))
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    sample_img = candidates[0] if candidates else (REPO_ROOT / "assets/XPLANE/Example 1.png")

    slice_run = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / ".agents/skills/xplane-infographic-studio/scripts/slice_render_for_judge.py"),
            "slice",
            str(sample_img),
            "--out-dir",
            str(tmp_path / "crops"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    crop_manifest = json.loads(slice_run.stdout)
    assert len(crop_manifest["tiles"]) == 9


def test_public_docs_and_agents_have_no_private_paths_or_retired_models():
    import os
    import re

    skip_dirs = {".git", ".scratch", ".swarm", ".pytest_cache", "__pycache__", ".venv", "venv"}
    binary_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pyc"}
    allowed_gemini_models = {
        "gemini-3.1-flash-image-preview",
        "gemini-3-pro-image-preview",
    }
    forbidden_patterns = (
        re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+"),
        re.compile(r"[A-Za-z]:\\\\Users\\\\"),
        re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
        re.compile(r"ghp_[0-9A-Za-z]{20,}|github_pat_[0-9A-Za-z_]{20,}"),
        re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
        re.compile(r"(?:googlesource|corp\.google)\.com", re.IGNORECASE),
    )
    gemini_id_pattern = re.compile(r"\bgemini-[a-z0-9][a-z0-9.-]*\b", re.IGNORECASE)

    for root_str, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            if fname.startswith(".DS_Store") or fname == ".gitkeep":
                continue
            fpath = Path(root_str) / fname
            if fpath.suffix.lower() in binary_exts:
                continue
            text = fpath.read_text(encoding="utf-8")
            rel = fpath.relative_to(REPO_ROOT).as_posix()
            for pat in forbidden_patterns:
                match = pat.search(text)
                assert match is None, f"Forbidden pattern {match.group(0)!r} found in {rel}"
            for m in gemini_id_pattern.finditer(text):
                model_id = m.group(0).lower()
                if model_id == "gemini-api-key":
                    continue
                assert model_id in allowed_gemini_models, (
                    f"Unapproved model identifier {model_id!r} found in {rel}"
                )

