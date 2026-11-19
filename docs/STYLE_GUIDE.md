# XPLANE + Edward Tufte Infographic Style & Craft Guide

This document is the canonical visual design, spatial projection, typography, and quality-assurance reference for the XPLANE Infographic Studio. Both the **Infographics Specialist** (`@specialist`) and the **LLM Judge** (`@judge`) MUST ground every concept pitch, 4K render prompt, and post-generation graphical audit on this guide and on the read-only reference library in `assets/XPLANE/`.

> **Source vs. Style Firewall:** Files inside `assets/XPLANE/` are strictly **visual and structural style references**. Never copy company names, domain claims, or metrics from `assets/XPLANE/` into a new deliverable. Factual content comes exclusively from user files placed outside `assets/XPLANE/`.

---

## 0. Foundational Mandate: XPLANE Visual Storytelling (ZERO SLIDEWARE) & 4K Resolution

As XPLANE's own visual-thinking canon states (`462f0a3da21c1ca15eb979ad5d782260.jpg`):
> *"Pages of detailed documents with boxes and arrows are usually confusing. If you want people to understand a new process, show it to them. Make it visual so they know what to do."*

1. **NO SLIDEWARE — Ever:**
   - **Strictly forbidden:** Flat PowerPoint/Google Slides layouts, corporate architecture box-and-arrow diagrams, dark/light UI dashboard card grids, 3-column "Challenge Cards | Center Boxes | KPI Cards" slide templates, or rounded UI rectangles pretending to be an infographic.
   - **Input-Slide Translation Rule:** User source files in `assets/` will frequently be flat presentation slides, tables, or org boxes. NEVER re-skin a source slide's box layout. Translate its content into a **cohesive, inhabited spatial world, cutaway facility, journey terrain, inhabited 3D room, or physical/kinetic machine** where illustrated people and workflows bring the system to life.
2. **Default 4K Output (`3840 × 2160`):**
   - Unless the user explicitly asks for another pixel dimension or aspect ratio, every render MUST be generated natively at 4K via `render_infographic_4k.py` (`google-genai` `image_size="4K"`) and normalized to exact **`3840 × 2160` (`16:9` 4K UHD PNG)**.
3. **Mandatory `assets/logo.png` Brand Logo Integration:**
   - Whenever `assets/logo.png` exists in `assets/`, ALWAYS use `assets/logo.png` verbatim as the sole brand logo on the infographic **regardless of what image `assets/logo.png` contains**, sized proportionally in the masthead (`~11.5%` max width / `~5.6–6.8%` max height).
   - Never ask the image model to draw or invent a brand logo icon in the masthead. Instead, `@specialist` MUST confine the masthead headline/subtitle to the left `78%` (`x = 2.5%..78%`) and keep the top-right masthead zone (`x = 82%..98%, y = 0%..10.5%`) completely blank background paper/wall so `render_infographic_4k.py` alpha-composites `assets/logo.png` cleanly with zero background box before 1:1 Judge tile inspection.

---

## 1. XPLANE Spatial Storytelling Archetypes

Every single-canvas infographic must inhabit an unmistakable XPLANE visual-thinking archetype:

1. **Bird's-Eye Ecosystem World (`Example 1.png`, `XPL_ICAN1403_Internet-Governance-Map_011.png`):** Maps multi-actor systems as an elevated concentric island, city, or ringed world populated with buildings, workshops, vehicles, and actors, flanked by clean open-margin editorial commentary.
2. **Process / Transformation Journey Landscape (`Example 2.webp`, `xplane-infographic.jpg`, `462f0a3da21c1ca15eb979ad5d782260.jpg`, `root-zone-demystifying-3350x2168-09jul14-en.png`):** Follows a physical chronological or causal spine—isometric corridor, arched stone/steel causeway, ascending 3D stage platforms, or flowing landscape ribbon—from current-state friction through human decision gates to target-state value realization.
3. **Architectural / System Cutaway (`xplane-infographic.jpg`, `740f05d7f3fb56daa2c6ef62dceb653e.jpg`, `2275ee4bb5978fc852ee7351fb126a54.jpg`):** Slices open the outer walls, roofs, floors, and subterranean bedrock of a facility, tower, or campus to show engineers, architects, and workflows operating inside interconnected rooms—integrating callouts directly onto clean white negative space or isometric floor planes rather than slideware sidebars.
4. **Inhabited 3D Mission-Control Room & Launch Stage (`Example 4.jpeg`):** Places illustrated human operators at physical 3D consoles in the foreground watching a giant panoramic wall-mounted trajectory/launch screen that visualizes system stages as physical vehicles, signals, or orbital stations—never a flat 2D box-and-card UI dashboard.
5. **Kinetic Physical Machinery & Workshop (`Example 3.jpeg`):** Turns abstract processes or software pipelines into interlocking gears, pulleys, conveyor belts, telescopes, sorting funnels, and assembly stations actively operated by stylized people across open negative space.

---

## 2. Spatial Geometry, Viewpoints & Cutaways

- **Isometric / Axonometric Projection (`30°/30°`):** Parallel projection keeping scale constant from foreground to background so every room, operator desk, corridor branch, and floor-plane metric carries equal visual clarity (`xplane-infographic.jpg`, `462f0a3da21c1ca15eb979ad5d782260.jpg`, `2275ee4bb5978fc852ee7351fb126a54.jpg`).
- **Bird's-Eye (High-Angle) Panoramic World:** Elevated 3/4 vantage turning sprawling multi-actor ecosystems or end-to-end journeys into a single navigable physical terrain (`Example 1.png`, `Example 2.webp`).
- **Cross-Section / Cutaway Anatomy:** Slice open walls, roofs, bridges, subterranean vaults, or machine housings to reveal people, handoffs, and conduits inside (`xplane-infographic.jpg`, `740f05d7f3fb56daa2c6ef62dceb653e.jpg`).
- **Inhabited Theatrical Elevation & Kinetic Vignettes:** Combine dimensional human operator vignettes and physical machinery with clean editorial margin typography (`Example 3.jpeg`, `Example 4.jpeg`, `root-zone-demystifying-3350x2168-09jul14-en.png`, `XPL_ICAN1403_Internet-Governance-Map_011.png`). Never flatten into box-and-arrow slideware.

---

## 3. Information-Design Principles (Edward Tufte)

Every XPLANE graphic—whether ultra-clean vector or hand-inked watercolor—must uphold Edward Tufte's analytical rigor:

1. **Macro / Micro Readings:** At 3-foot distance, the headline, spatial spine/world, and color hierarchy immediately convey the core transformation story; up close at 4K zoom, individual rooms, human interactions, callouts, and metrics reward inspection without clutter.
2. **High Data-to-Ink Ratio & Zero Chartjunk:** Every drawn gear, room, bridge pier, operator station, or conduit encodes real meaning from `assets/`. Eliminate gratuitous lens flares, meaningless UI chrome, slideware boxes, and **extruded 3D pie charts**.
3. **Frameless Visual-Verbal Integration:** Like `xplane-infographic.jpg`, `740f05d7f3fb56daa2c6ef62dceb653e.jpg`, and `462f0a3da21c1ca15eb979ad5d782260.jpg`, place callout paragraphs directly on clean open paper margins connected by crisp leader lines or numbered medallions—avoid wrapping every text block in slideware rectangles.
4. **Spatial Small Multiples:** When comparing 3–5 parallel use cases or cohorts, render them as 5 parallel cutaway bays, 5 ascending isometric workshop platforms (`462f0a3da21c1ca15eb979ad5d782260.jpg`), 5 bridge stations (`Example 2.webp`), or 5 interconnected mechanical assemblies (`Example 3.jpeg`)—never as 5 flat PowerPoint UI cards.

---

## 4. Sixteen Curated XPLANE Style Presets (`S1`–`S16`)

Offer 2–3 genuinely distinct XPLANE spatial storytelling directions across this spectrum from **ultra-clean pixel-perfect vector** and **Wimmelbilder horological micro-detail** to **finished hand-drawn editorial, botanical watercolor, steampunk, screenprint, and Risograph**:

### `S1` — Precision Isometric Cutaway Corridor & Stepped Platforms *(Ultra-Clean / Pixel-Perfect Vector)*
- **Visual Look:** Razor-sharp 30° vector axonometric campus, branching workflow corridor, or ascending stepped 3D room platforms on pure white ground, with stylized flat-vector people operating inside open cutaway rooms, isometric floor-plane KPI typography, and unboxed Swiss editorial callouts in clean white margins connected by hairline circle-tipped leader lines.
- **Canonical Anchors in `assets/XPLANE/`:**
  - `xplane-infographic.jpg` (*Weatherford Employee CONNECT* — open-top isometric corridor cutaway with branching green/red rooms and frameless margin callouts)
  - `462f0a3da21c1ca15eb979ad5d782260.jpg` (*XPLANE Visual Process Innovation* — 5 ascending isometric workshop platforms with frameless numbered editorial callouts)
  - `740f05d7f3fb56daa2c6ef62dceb653e.jpg` (*The High-Rise Zoo* — vertical exploded cross-section tower with horizontal circle-tipped leader lines into open white margins)
  - `2275ee4bb5978fc852ee7351fb126a54.jpg` (*Cork Chamber / Dynamite Studio* — crisp isometric city block integrating bold isometric floor-plane KPI typography and hairline brackets)
  - `02e5ec93ead5fe1175bfa9964cf1d83a.jpg` *(Layout-only reference: cascading vertical S-ribbon connecting isometric platforms — see Section 4.1 Stock Guardrail)*

### `S2` — Concentric Bird's-Eye Ecosystem World & Ring Map *(Clean Spatial Ecosystem Poster)*
- **Visual Look:** Elevated 3D bird's-eye concentric island/city ecosystem (`Example 1.png`) or multi-ring collaborative ecosystem map (`XPL_ICAN1403_Internet-Governance-Map_011.png`) populated with architectural landmarks, workshops, vehicles, and actors across concentric zones of influence, flanked by clean editorial magazine columns on open light paper.
- **Canonical Anchors in `assets/XPLANE/`:**
  - `Example 1.png` (*The Corporate Innovation Ecosystem* — concentric tiered 3D bird's-eye city/landscape world flanked by editorial columns)
  - `XPL_ICAN1403_Internet-Governance-Map_011.png` (*ICANN Collaborative Internet Governance Ecosystem* — concentric ecosystem rings + sample ring multiples + bottom principles strip)
  - `root-zone-demystifying-3350x2168-09jul14-en.png` (*ICANN Root Zone Demystified* — flowing process ribbon + circular zoom vignettes)

### `S3` — Inhabited 3D Mission-Control Room & Panoramic Telemetry Stage *(Spatial Command Storytelling)*
- **Visual Look:** Dimensional XPLANE Mission-Control theater (`Example 4.jpeg`): illustrated teams and architects seated at physical 3D isometric operator consoles and war-room tables in the foreground, looking up at a panoramic wall-mounted visual-metaphor launch/trajectory screen where system workflows fly from raw launchpad to governed orbit, paired with clean editorial metric columns on light architectural ground. **Never** flatten `S3` into a 2D dark-mode UI card dashboard.
- **Canonical Anchors in `assets/XPLANE/`:**
  - `Example 4.jpeg` (*XPLANATIONS: Measuring Innovation* — panoramic 5-stage spacecraft launch screen + Activity vs. Impact editorial columns + 4 inhabited 3D operator console vignettes)

### `S4` — Kinetic Flat-Vector Machinery, Gears & Refinery Ribbons *(Visual Mechanical Metaphor)*
- **Visual Look:** Lively flat-vector mechanical factory/refinery (`Example 3.jpeg`) made of interlocking gears, pulleys, sorting funnels, conveyor belts, radar dishes, and directional ribbons on crisp white space, actively operated by stylized people with numbered circular badges and clean color-coded callouts.
- **Canonical Anchors in `assets/XPLANE/`:**
  - `Example 3.jpeg` (*XPLANATIONS: Plug in to the Startup Ecosystem* — 7 numbered flat-vector human-operated mechanical vignettes feeding a central gear-and-pulley assembly)

### `S5` — Editorial Ink & Watercolor Transformation Journey *(Organic / Hand-Drawn & Finished)*
- **Visual Look:** Expressive black fountain-pen ink outlines with warm hand-painted watercolor/marker washes on archival paper: current-state storm-cloud swamp on the left, sweeping elevated stone/timber causeway with human collaboration stations across the center, and sunlit value-realization honeycomb/pavilion on the right.
- **Canonical Anchors in `assets/XPLANE/`:**
  - `Example 2.webp` (*Alvaria Customer Success Journey Map* — curved orange causeway from storm-cloud pain through decision-point arrow to golden value-realization honeycomb)

### `S6` — Architect's Vellum Cross-Section & Spot-Marker Blueprint *(Tactile Draftsman Cutaway)*
- **Visual Look:** Tactile architectural fine-liner and graphite cross-section cutaway on warm cream vellum paper using 2 bold spot-color marker accents (e.g., vermilion + cyan) to trace workflow paths, bottlenecks, and HITL gates through open rooms and subterranean vaults, with crisp architectural margin lettering.
- **Canonical Anchors in `assets/XPLANE/`:** Combines the cutaway anatomy of `xplane-infographic.jpg` and `740f05d7f3fb56daa2c6ef62dceb653e.jpg` with the hand-drawn warmth of `Example 2.webp`.

### `S7` — Kinetic Pop-Line & Cascading Tatami-Room Cutaway *(Vibrant Flat-Pop Architectural Collage)*
- **Visual Look:** Yusuke Nakamura & Masaaki Yuasa–inspired sleek, razor-sharp black India-ink contours paired with hyper-vibrant, unshaded flat pop-color blocks (electric vermilion, cobalt ultramarine, marigold yellow, mint turquoise, plum) and crisp graphic geometric accents on warm cream paper (`#FCF9F2`); a kinetic, playfully tilted 3D cascade of open-top *tatami* rooms, rooftop studio clubhouses, and sweeping ribbon conduits inhabited by expressive contemporary architects and engineers.
- **Guardrail:** Float the vibrant flat-pop room cascade cleanly inside wide, completely uniform `#FCF9F2` cream margins and top band (`y = 0%..12%`) with zero shaded masthead strip and zero tiny pseudo-text inside room props so frameless black callouts, circle-tipped leader lines, and top-right `assets/logo.png` remain 100% crisp.
- **Canonical Anchors in `assets/XPLANE/`:** `462f0a3da21c1ca15eb979ad5d782260.jpg`, `xplane-infographic.jpg`, `Example 2.webp`

### `S8` — Ligne Claire Architectural Comic *(Uniform Ink Line & Luminous Flat Cel Color)*
- **Visual Look:** Hergé / Joost Swarte / Chris Ware uniform-weight black ink contours with zero hatching, zero muddy gradients, and flat cel colors on warm off-white paper; 30° isometric cutaway campus/bureau with expressive clear-line people and hairline circle-tipped leader lines in open margins.
- **Canonical Anchors in `assets/XPLANE/`:** `xplane-infographic.jpg`, `2275ee4bb5978fc852ee7351fb126a54.jpg`

### `S9` — Illustrated Encyclopedia Cross-Section *(Detailed Pen-and-Ink Cutaway Anatomy)*
- **Visual Look:** David Macaulay / Stephen Biesty intricate pen-and-ink cross-section with subtle muted watercolor washes on open ivory encyclopedia pages; sliced stone/steel governance citadel, pulleys, chutes, and subterranean vaults populated by tiny focused engineers, surrounded by wide ivory book margins for frameless numbered annotations.
- **Canonical Anchors in `assets/XPLANE/`:** `740f05d7f3fb56daa2c6ef62dceb653e.jpg`, `Example 3.jpeg`

### `S10` — Symmetrical Dollhouse Elevation *(Orthographic Frontal Cutaway)*
- **Visual Look:** Wes Anderson deadpan 100% orthographic frontal cross-section elevation (Belafonte / Grand Budapest room-by-room cutaway) in curated mid-century pastels (warm ochre, dusty rose, pistachio sage, slate blue) over a subterranean vault, framed by wide cream margins with crisp geometric sans-serif labels.
- **Canonical Anchors in `assets/XPLANE/`:** `740f05d7f3fb56daa2c6ef62dceb653e.jpg`, `462f0a3da21c1ca15eb979ad5d782260.jpg`

### `S11` — Mid-Century Modern Minimal Realism *(Geometric Screenprint Ecosystem)*
- **Visual Look:** Charley Harper / Saul Bass disciplined flat geometric shapes, cardinal & 45° trajectories, subtle serigraph ink texture on warm cream stock (terracotta, mustard gold, peacock teal, charcoal, olive) with zero perspective clutter and maximum Tufte data-to-ink ratio.
- **Canonical Anchors in `assets/XPLANE/`:** `Example 3.jpeg`, `XPL_ICAN1403_Internet-Governance-Map_011.png`

### `S12` — 1960s Apollo Technical Cutaway Manual *(Retro-Futuristic Engineering Gouache)*
- **Visual Look:** Cold War NASA / JPL / Popular Science sliced titanium-and-enamel command module & subterranean launch bay cutaway with color-coded telemetry conduits and engineers at physical consoles, floating cleanly on stark white engineering-manual paper with crisp technical callout ticks.
- **Canonical Anchors in `assets/XPLANE/`:** `Example 4.jpeg`, `xplane-infographic.jpg`

### `S13` — Isometric Risograph Editorial Zine *(Spot-Ink Overprint Isometric World)*
- **Visual Look:** Crisp 30° isometric workshop & stepped causeway printed in 3 high-contrast spot soy inks (deep navy, fluorescent coral, bright teal) with subtle tactile Risograph grain on warm off-white stock, using coral solely for bottlenecks/HITL gates and teal for automated flows/impact metrics.
- **Canonical Anchors in `assets/XPLANE/`:** `462f0a3da21c1ca15eb979ad5d782260.jpg`, `2275ee4bb5978fc852ee7351fb126a54.jpg`

### `S14` — Victorian Steampunk Clockwork & Pneumatic Cutaway *(Industrial Brass & Copper Engine-House)*
- **Visual Look:** 19th-century Jules Verne / Babbage Difference Engine architectural cutaway with fine-liner etching lines and warm burnished brass, oxidized verdigris copper, riveted cast-iron, and amber vacuum-tube washes on clean warm parchment paper; brass gear-trains, steam pressure gauges, and copper pneumatic dispatch tubes operated by Victorian engineers and Senior Architects.
- **Guardrail:** Float the cutaway cleanly inside wide unadorned parchment margins and top masthead band (`y = 0%..12%`) with zero pseudo-text on dials/pipes and clean top-right `assets/logo.png` placement.
- **Canonical Anchors in `assets/XPLANE/`:** `Example 3.jpeg`, `740f05d7f3fb56daa2c6ef62dceb653e.jpg`

### `S15` — Botanical Watershed & Living Permaculture Ecosystem *(Naturalist Field-Guide Cross-Section)*
- **Visual Look:** Alexander von Humboldt *Naturgemälde* & botanical field-guide pen-and-ink + watercolor ecological cross-section on natural cotton paper; upstream silted runoff pools flow through terraced reed-bed bio-filters, stone aqueducts, living bridges, and sunlit canopy observatories rooted in a sliced limestone aquifer & root-network foundation into a thriving orchard harvest, surrounded by clean unpainted cotton-paper sky and field-guide margins.
- **Canonical Anchors in `assets/XPLANE/`:** `Example 1.png`, `Example 2.webp`

### `S16` — Clean-Line Wimmelbilder & Horological Micro-Detail Cutaway *(Ultra-Intricate Macro-Clean Isometric World)*
- **Visual Look:** Combines clean-line *Wimmelbilder* isometric illustration (IC4DESIGN / Hirofumi Kamigaki teeming architectural micro-worlds) with Swiss horological / industrial-design precision cutaway on pure gallery-white paper (`#FFFFFF`). Disciplined geometric 30° isometric architectural islands float inside expansive (`35%+`) pure-white negative space for effortless macro cleanliness, while 4K zoom reveals dozens of razor-sharp 0.25pt cutaway mezzanines, spiral stairs, micro-conduits, watchmaker differentials, and tiny focused specialists (using 100% non-verbal geometric interior micro-detail and crisp full-size Swiss margin typography).
- **Canonical Anchors in `assets/XPLANE/`:** `740f05d7f3fb56daa2c6ef62dceb653e.jpg`, `2275ee4bb5978fc852ee7351fb126a54.jpg`

### 4.1 Guardrail for Stock-Preview Layout References
Two files in `assets/XPLANE/` were added strictly as minor **macro-grouping references** and carry strict guardrails:
- `02e5ec93ead5fe1175bfa9964cf1d83a.jpg` (*Oil Industry* cascading vertical isometric S-ribbon) contains a stock watermark (`#411978483`) and dummy copy.
- `92ef53d04930593d71eb7075d0c45044.jpg` (statistical grid) contains faint stock watermarks, generic `OPTION` / lorem-ipsum labels, an extruded **3D pie** cylinder, and flat dashboard panels.

**Mandatory Rule:** Never reproduce any watermark, stock ID number, `OPTION`/lorem-ipsum placeholder text, extruded 3D pie chart, or flat dashboard slideware panels. Every deliverable must remain a true spatial/metaphorical XPLANE infographic.

---

## 5. Strict Anti-Artifact Graphical & Typography Rules

Both `@specialist` (when composing 4K render prompts) and `@judge` (during 1:1 4K tile inspection) MUST enforce zero tolerance for these five defect classes in `docs/anti-patterns/`:

1. **No Text Background Clipping Container Borders (`defect-01-border-clipped-by-text-bg.png` & `defect-04-text-bg-erases-card-border.png`):**
   - *Rule:* Prefer frameless XPLANE margin typography on clean paper; whenever a callout badge, hexagon, or plaque has a border, its perimeter stroke must be **100% continuous and unbroken** on all sides with generous padding and a single uniform fill.
2. **No Opaque Text Boxes Cutting Shadows, Gradients, or Washes (`defect-02-text-bg-cuts-path-shadow.jpg` & `defect-03-text-bg-cuts-bridge-wash.jpg`):**
   - *Rule:* Place multi-line stage descriptions in **clean open canvas zones** completely outside drop shadows and washes, with **transparent text ground** (never white rectangular patches).
3. **No Pasted Patches Obliterating Signboard Outlines (`defect-05-text-bg-covers-signboard-border.png`):**
   - *Rule:* Keep in-scene signboard/banner text to **1–3 short words** rendered natively inside the drawn sign frame with generous inner margin.
4. **Ban Post-Hoc "Whiteout Rectangle" Scripts:**
   - Never run PIL, Canvas, or HTML overlay scripts that paint solid-color rectangles over artwork to patch text. All repairs happen through clean 4K `render_infographic_4k.py` regeneration verified at 1:1 zoom.
5. **100% Character-Level Text Legibility at 4K (`3840 × 2160`):**
   - Every word, acronym, number, and symbol on the 4K canvas must be crisp, spelled accurately, properly oriented, and readable at 1:1 zoom.
