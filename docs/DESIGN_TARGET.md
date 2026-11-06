# Design contract — V0.71 FIRST SPARK

**Primary visual:** `../design/01_MASTER_MOCKUP_FIRST_SPARK.png` — the user-favorite ideal screenshot used to benchmark spacing, glow, textures, typography, contrast and layout.

**Secondary:** `../design/02_ORIGINAL_PERFEKT_FAVORIT_0.71.png` — originally approved white-logo version with version label.

**Current reality:** `../design/04_IST_ZUSTAND_ECHTES_FENSTER.png` — screenshot from actual app; structurally different from approved reference. `../design/05_VERGLEICH_SOLL_IST.png` is another comparison artifact. The screenshots are NOT evidence that the UI already matches the user’s vision.

## Latest overrides to mockup
Latest user clarification (05.11.2026): KEEP the dark metallic upper rail and its lowered/sloping red upper contour. Match the background to that contour: continue the brand texture ABOVE the edge and clip the metallic surface BELOW it, with no rectangular seam. Remove only the SET SCANNER / OFFLINE / MIX-ID / SHAZAM labels and the three red slashes. Preserve the textured HIER REINZIEHEN area. Keep the version in the full-width banner and the gear inset 40px and vertically centred.

## Pixel/layout checks (measurable, not aspirational handwaving)
- Use a wide desktop layout roughly proportional to the 1672×941 reference, with adaptive scaling above a safe minimum size. Do not distort a large banner by stretching non-proportionally.
- Header: white original gothic logo and glitch title, blood-red black smoky texture, settings gear in upper-right.
- Three major upper panels: left input zone, prerequisites card, optional local AI card. All align top; consistent vertical padding and rounded corners.
- Drop area: large dashed crimson border, strong centered text, secondary supported-format line.
- File path and online URL row: equal-height wide red action buttons; input fields align to the same width.
- Scanner workflow: six named stages, real state transitions and clear labels; no dead steps.
- Live results: table with at least Time, Track, Source; values only from engines, empty at rest.
- Progress/log: visible under results, explicit errors, no fake percentage values.
- Strong visual cohesion: anthracite base, subtle surface gradients, blood-red highlights, consistent 1px borders, large enough text.

## Required UI behavior for missing prerequisites
- FFmpeg missing -> "EINRICHTEN" triggers bundled setup action, then rechecks status.
- Musikdatenbank missing -> "ANLEGEN" brings user to database setup (or creates when music folder is configured).
- Offline engine missing -> "EINRICHTEN" downloads/copies the offline engine into the app's own folder.
- mix-id missing -> "EINRICHTEN" installs Node/mix-id locally and rechecks.
- ShazamIO missing -> "EINRICHTEN" installs local Python dependency and rechecks.
- Never mark a failed action as success.

## Visual comparison process
Open `design/01_MASTER_MOCKUP_FIRST_SPARK.png` next to a screenshot captured from **real application rendering** at approximately the same size. Identify differences section by section and revise until the result is demonstrably close. Show screenshot and report remaining differences honestly.
