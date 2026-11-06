# Work backlog — handoff to Codex

## P0: Actual UI fidelity (user's primary unresolved task)
- [x] Latest user clarification (05.11.2026): KEEP the dark metallic upper rail and its lowered/sloping red upper contour. Match the background to that contour: continue the brand texture ABOVE the edge and clip the metallic surface BELOW it, with no rectangular seam. Remove only the SET SCANNER / OFFLINE / MIX-ID / SHAZAM labels and the three red slashes. Preserve the textured HIER REINZIEHEN area. Keep the version in the full-width banner and the gear inset 40px and vertically centred.
- [ ] Preserve white logo + glitch title, improve their proportion relative to approved mockup.
- [ ] Replace current rough Tkinter visual hierarchy with genuinely close rounded/gradient UI panels, matched spacing/typography, without screenshot-as-UI hacks.
- [ ] Match file & link fields and matching button sizes. Real drag/drop, browse, link load.
- [ ] Render prerequisite status as interactive, and fix each missing-component action.
- [ ] Place optional local AI right beside prerequisites; label optional.
- [ ] Show six scan stages, real live hits, true progress/error display, no fake samples.
- [ ] Produce screenshot from running program and compare against `design/01_MASTER_MOCKUP_FIRST_SPARK.png` before claiming completion.

## P1: Runtime / scanner robustness
- [ ] End-to-end local index for sample tracks with audfprint and true offline scan.
- [ ] Tempo variation matching: re-test on actual DJ set; resist false positives. The original +6% test fell from 1235 to 8 common hashes and recovered to 331 after reverse correction. One sample is not proof of real-world reliability.
- [ ] Verify mix-id, ShazamIO, caching / duplicate work and offline-only path.
- [ ] Clearly identify Shazam use as online; avoid uploading when disabled.
- [ ] SoundCloud, Mixcloud and YouTube URL handling with allowed/accessible links.
- [ ] TXT with timestamps + engine provenance + confidence caveats; no fake track names.

## P2: Self-contained user experience
- [ ] Packaging should not require searching for audfprint/FFmpeg. Have a single install flow with environment detection and clear repair actions.
- [ ] Keep user data (music, fingerprints, configs, previous results) intact on update.
- [ ] Optional LM Studio / Ollama model selection & connection test only for metadata validation, no promise of local universal song ID.
- [ ] Test on Windows 11 + Python 3.15 with current dependencies and report actual findings.
