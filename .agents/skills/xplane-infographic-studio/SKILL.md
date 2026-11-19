---
name: xplane-infographic-studio
description: >-
  Conversational XPLANE + Edward Tufte 4K infographic studio workflow. Use whenever
  the user asks to brainstorm, design, render, critique, or iterate on an
  infographic, conceptual diagram, process map, or architectural cutaway from
  materials in assets/.
---

# XPLANE + Tufte Conversational 4K Infographic Studio

Follow this 4-phase workflow whenever creating or iterating on infographics in this repository.

## Key References & Scripts

- **Style & Craft Guide:** [docs/STYLE_GUIDE.md](../../../docs/STYLE_GUIDE.md) (Zero-Slideware mandate, `3840 × 2160` 4K standard, `S1`–`S16` XPLANE style presets, spatial archetypes, Tufte rules, and anti-artifact rules)
- **Defect Ground Truth (`docs/anti-patterns/`):** `defect-01-border-clipped-by-text-bg.png` through `defect-05-text-bg-covers-signboard-border.png`
- **Canonical Agent Personas:**
  - Specialist: [.agents/agents/infographic-specialist.md](../../agents/infographic-specialist.md)
  - Judge: [.agents/agents/infographic-judge.md](../../agents/infographic-judge.md)
- **Source Asset Extractor:** [scripts/ingest_assets.py](./scripts/ingest_assets.py)
- **Native 4K Infographic Renderer (`3840 × 2160` default):** [scripts/render_infographic_4k.py](./scripts/render_infographic_4k.py)
- **1:1 4K Tile Slicer & 4K-Gated Deliverable Promoter:** [scripts/slice_render_for_judge.py](./scripts/slice_render_for_judge.py)

---

## Phase 1: Source Asset Intake (`assets/` Excluding `assets/XPLANE/`)

1. Run the deterministic multi-format extractor:
   ```bash
   python3 .agents/skills/xplane-infographic-studio/scripts/ingest_assets.py \
     --assets-dir assets \
     --out-dir .scratch/extracted-assets
   ```
2. Read `.scratch/extracted-assets/digest.md`.
3. For every source entry flagged `"needs_multimodal_view": true` (source images, screenshots, tables, or scanned PDFs—**never** `assets/XPLANE/`), inspect the file directly with `read_file` (or instruct `@specialist` to do so) so visual details and tables are captured accurately.
   - **Anti-Slideware Intake Rule:** If source files in `assets/` are presentation slides or box diagrams, extract *only* their facts, workflows, and metrics—**discard their flat slideware/card layout completely**.
4. If `assets/` contains zero non-XPLANE files, tell the user `assets/` currently has no source files outside `assets/XPLANE/` and ask what topic or documents they want to use.

---

## Phase 2: Cross-Model Worker Setup & Checkpoint 1 (Concept & Style Pitch)

### 2.1 Pin Specialist & Judge to a Cross-Model High-Reasoning Model
1. Call `swarm{action: "models", all: true}` to verify live model availability and quotas.
2. Select the worker model so it is **another high-reasoning model different from the active primary orchestrator** (such as a Flash or Pro model with high reasoning enabled) based on live availability and quota from `swarm{action: "models", all: true}`, and mention the chosen model in one line to the user.
3. Add two separate persistent workers on the swarm board (if not already active in `swarm{action: "status"}`):
   - `specialist` (`model: "<chosen-high-model>"`): Brief it to read `.agents/agents/infographic-specialist.md`, `docs/STYLE_GUIDE.md`, and `.scratch/extracted-assets/digest.md` (plus `needs_multimodal_view` source files and `assets/XPLANE/` anchors).
   - `judge` (`model: "<chosen-high-model>"`): Brief it to read `.agents/agents/infographic-judge.md`, `docs/STYLE_GUIDE.md`, view key `assets/XPLANE/` anchors, and view all 5 files in `docs/anti-patterns/` so it enforces `Gate 0` (Zero Slideware + 4K), `Gate A`, and `Gate B`.

### 2.2 Checkpoint 1 — Pitch XPLANE Spatial Concepts & Style Spectrum in Chat
Have `@specialist` synthesize the source material against `docs/STYLE_GUIDE.md` and `assets/XPLANE/`, then present to the user in chat:
1. **2–3 Distinct XPLANE Spatial Storytelling Directions** (zero slideware, zero flat box-and-card decks!), each specifying:
   - **XPLANE Archetype & Spatial Viewpoint** (30° Isometric Corridor/Campus Cutaway, Concentric 3D Bird's-Eye Ecosystem World, Elevated Transformation Causeway, Inhabited 3D Mission-Control Room with Human Operators at Consoles, or Kinetic Human-Operated Gear/Conveyor Machinery)
   - **Recommended Style Preset (`S1`–`S16`)** + exact `assets/XPLANE/` anchor file
   - **Tufte Macro/Micro Narrative Arc** (how illustrated people/workflows move from current-state pain through control gates to quantified outcomes, with frameless margin callouts)
2. **Default Resolution & Style Reminder:** Note the default **4K (`3840 × 2160` `16:9` PNG)** target unless the user requests another resolution or aspect ratio.

**Pause at Checkpoint 1** for the user to pick, remix, or steer the concept/style unless the user explicitly asked to skip straight to rendering.

---

## Phase 3: Native 4K Render (`3840 × 2160`) & 1:1 Zoom-Tile Judge Loop (Up to 3 Attempts)

> **CRITICAL:** Do **NOT** use the built-in `image-generator` subagent for deliverables—its internal tool outputs 1K (`1376 × 768`) JPEGs. Always render via `scripts/render_infographic_4k.py`, which calls `google-genai` with `image_size="4K"` and normalizes to exact **`3840 × 2160` PNG**!

Run up to **3 attempts** (`attempt = 1..3`):

1. **4K Prompt Compilation (`@specialist`):**
   - Ask `@specialist` for the complete, self-contained 4K XPLANE spatial render prompt (zero slideware, frameless margin callouts or unbroken badge borders, exact verbatim text strings, and—whenever `assets/logo.png` is present—a clean empty `top-right` masthead slot `x = 82%..98%, y = 0%..10.5%` with zero AI-drawn brand logos) and save it to `.scratch/prompts/attempt-<N>.txt`.
2. **Native 4K Render (`3840 × 2160` PNG + Automatic `assets/logo.png` Placement):**
   ```bash
   python3 .agents/skills/xplane-infographic-studio/scripts/render_infographic_4k.py \
     --prompt-file .scratch/prompts/attempt-<N>.txt \
     --out .scratch/renders/attempt-<N>.png \
     --aspect-ratio 16:9
   ```
   - When `assets/logo.png` exists, `render_infographic_4k.py` automatically alpha-composites `assets/logo.png` verbatim at balanced editorial scale into the reserved top-right masthead zone regardless of what image `logo.png` contains.
   - **Hard Ban:** Never run post-processing scripts that draw solid white/cream rectangles over artwork to patch text.
3. **1:1 Full-Resolution 4K Tile Slicing:**
   ```bash
   python3 .agents/skills/xplane-infographic-studio/scripts/slice_render_for_judge.py \
     slice .scratch/renders/attempt-<N>.png \
     --out-dir .scratch/judge-crops/attempt-<N>
   ```
4. **Independent Graphical & Anti-Slideware Audit (`@judge`):**
   - Wake `@judge` with `.scratch/renders/attempt-<N>.png`, `.scratch/judge-crops/attempt-<N>/manifest.json` (confirming `"width": 3840, "height": 2160, "is_4k": true`), `.scratch/extracted-assets/digest.md`, and the chosen Style Preset.
   - Require `@judge` to view the full image AND all 9 full-resolution 4K tiles (`row1-col1`..`row3-col3`) via `read_file` and return its structured verdict (`Gate 0` Anti-Slideware & 4K, `Gate A` Borders/Washes, `Gate B` Legibility, `Scores 1–3`, tile-by-tile findings, and `Repair Prescription`).
5. **Gate Decision:**
   - **PASS** (`Gate 0 == PASS`, `Gate A == PASS`, `Gate B == PASS`, all 3 scores `>= 4/5`): Promote the verified 4K render to `deliverables/` (which enforces `max(w, h) >= 3840` automatically):
     ```bash
     python3 .agents/skills/xplane-infographic-studio/scripts/slice_render_for_judge.py \
       promote .scratch/renders/attempt-<N>.png \
       --slug "<concise-topic-slug>"
     ```
   - **FAIL and `N < 3`:** Send `@judge`'s exact `Repair Prescription` back to `@specialist` to revise the spatial world/prompt and run a **fresh text-to-image 4K render** (`render_infographic_4k.py --prompt-file ...` *without* `--ref-image`, as image-to-image re-encoding degrades crisp 4K typography) for `attempt-(N+1)`.
   - **If `attempt-3` still has minor typography notes (while passing `Gate 0` 4K + Anti-Slideware):** Promote the highest-scoring 4K attempt via `slice_render_for_judge.py promote` and surface remaining Judge notes transparently in Phase 4. Never promote a slideware layout (`Gate 0 FAIL`) or sub-4K image.

---

## Phase 4: Checkpoint 2 — Art-Direction Presentation & Iteration

Present to the user:
1. Clickable `file://` link to the newly stamped 4K deliverable `deliverables/YYYYMMDD-HHMMSS-<slug>.png` (confirming `3840 × 2160` 4K dimensions and XPLANE style preset used).
2. Concise **Judge QA Scorecard** (`Gate 0` XPLANE Spatial Viewpoint & 4K check, `Gate A` border/wash cleanliness, `Gate B` verified 4K text legibility, Spatial/Style score, Tufte Clarity score, Source Grounding score, and passes run).
3. Invite conversational art-direction refinements—every subsequent render runs through Phase 3 at 4K and lands as a fresh timestamped deliverable in `deliverables/`.
