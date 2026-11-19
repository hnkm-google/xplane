# XPLANE + Tufte Conversational Infographic Studio — Workspace Rules

Whenever the user asks to design, generate, critique, or iterate on an infographic, diagram, process map, or visual explanation in this repository, you MUST read and follow [SKILL.md](.agents/skills/xplane-infographic-studio/SKILL.md) (`xplane-infographic-studio`).

## Non-Negotiable Studio Invariants

1. **Strict `assets/` vs. `assets/XPLANE/` Firewall:**
   - Everything inside `assets/` *except* `assets/XPLANE/` is factual source material for the infographic being created (emails, PDFs, Word docs, spreadsheets, slide decks, notes, screenshots).
   - `assets/XPLANE/` is a permanent, read-only visual style canon. NEVER treat text, company names, or data inside `assets/XPLANE/` as factual topic content, and never delete or overwrite files in `assets/` or `assets/XPLANE/` unless explicitly asked.
2. **Mandatory XPLANE Spatial Viewpoint & Visual Storytelling — ZERO SLIDEWARE:**
   - Every output MUST use genuine **XPLANE visual-thinking storytelling**: an inhabited spatial world, architectural/system cutaway, bird's-eye ecosystem terrain, physical journey causeway, inhabited 3D mission-control room, or kinetic physical machinery operated by illustrated people/actors.
   - **Hard Ban on Slideware:** NEVER generate flat PowerPoint/Google Slides layouts, corporate box-and-arrow block diagrams, dark/light UI dashboard card grids, or 3-column slide templates—even when the factual input files inside `assets/` are flat slides or tables. Always translate flat input slides into a spatial XPLANE visual metaphor.
3. **Mandatory `assets/logo.png` Brand Logo Integration:**
   - Whenever `assets/logo.png` exists, ALWAYS use `assets/logo.png` verbatim as the sole brand logo on the generated infographic **regardless of what image `assets/logo.png` actually contains**, sized proportionally in the masthead.
   - Never draw or hallucinate competing AI-invented brand logos in the render prompt; reserve the top-right masthead zone (`x = 82%..98%, y = 0%..10.5%`, keeping title/subtitle left-aligned within `x = 2.5%..78%`) completely empty so `render_infographic_4k.py` composites `assets/logo.png` cleanly before 1:1 Judge tile slicing.
4. **Mandatory 4K Default Resolution (`3840 × 2160`):**
   - Unless the user explicitly requests a different pixel size or aspect ratio, EVERY infographic MUST be rendered at native 4K via `render_infographic_4k.py` (`google-genai` `image_size="4K"`) and output as a lossless **`3840 × 2160` PNG**. Never use 1K (`1376 × 768`) subagent renders for deliverables, and `slice_render_for_judge.py promote` enforces 4K resolution by default.
5. **Conversational Studio Flow (Two Checkpoints):**
   - Treat infographic creation as an art-direction conversation rather than a silent batch job: pitch 2–3 visual concepts across the `S1`–`S16` style spectrum in `docs/STYLE_GUIDE.md` first (**Checkpoint 1**), then run 4K rendering + zoom-level Judge QA behind the scenes before presenting the clean deliverable (**Checkpoint 2**).
6. **Cross-Model High-Reasoning Subagents:**
   - Spawn the Specialist and the independent LLM Judge via `swarm` on **another high-reasoning model different from the active primary orchestrator** (such as a Flash or Pro model with high reasoning enabled) based on live `swarm{action: "models", all: true}` availability and quota.
7. **Zero "Whiteout Patch" Artifacts & Mandatory 1:1 Tile QA:**
   - Never run PIL/Canvas/HTML scripts that paint opaque solid-color rectangles over rendered borders, drop shadows, washes, or signboards to patch text (`docs/anti-patterns/defect-01..05`).
   - Every 4K candidate render MUST be sliced into 9 overlapping 1:1 full-resolution tiles via `slice_render_for_judge.py` and audited by the independent Judge (`Gate 0` Anti-Slideware, 4K & `logo.png` + `Gate A` Borders/Washes + `Gate B` Legibility) before promotion.
8. **Timestamped Deliverables:**
   - Keep intermediate drafts and Judge tiles in `.scratch/`. Promote approved 4K renders into `deliverables/` named `YYYYMMDD-HHMMSS-<topic-slug>.png` so renders never overwrite prior outputs.
