# Roadmap

Milestones are sequenced so there is always a genuinely working, testable artifact at the end of each one — no long stretch where nothing runnable exists. See `PROJECT_OVERVIEW.md` for the reasoning behind each scope decision.

## Milestone 0 — Environment & skeleton ✅ Done
- Git repo initialized, `.gitignore` for Python/Qt/model weights
- Virtual environment, dependency list pinned (`torch`, `PySide6`, Real-ESRGAN deps)
- Empty `engine/` and `ui/` packages wired through a trivial `main.py` that opens a blank window
- **Exit criteria**: app launches to an empty window from a fresh clone + install

## Milestone 1 — Engine core, headless (no UI) ✅ Done
- `engine/enhance.py`: load an image, run a ×4 restoration model (Real-ESRGAN/SwinIR/BSRGAN), resize the result back to the input's original dimensions, save it — as a plain function callable from a script/CLI, no Qt involved
- CUDA-if-available / CPU-fallback device selection
- Tiled inference for large images (this is the technically riskiest piece — de-risk it here, before any UI complexity is layered on)
- Handle non-RGB inputs (alpha, grayscale, CMYK) and EXIF orientation correctly
- **Exit criteria**: `python -m engine.enhance input.jpg output.png --model swinir-m` works correctly on a range of real test images, including a large one that would OOM without tiling

## Milestone 2 — Minimal UI around the engine ✅ Done
- Open image (file dialog + drag & drop), preview pane
- Model/quality preset selection, if more than one weight set is bundled
- Run button → background-thread inference → progress indication
- Cancel, honored between tiles
- GPU/CPU indicator
- Save/export with format + quality choice
- Specific error handling: corrupted file, unsupported format, oversized-image warning before running
- **Exit criteria**: a complete, crash-resistant single-image workflow — this is the first genuinely usable version of the app

## Milestone 2.5 — Model selection (benchmarked) ✅ Done
- Not originally planned as its own milestone, but became substantial enough to call out: built `benchmark/` as a standalone research/evaluation tool (separate from the shipped app) to compare candidate restoration models against real test photos rather than picking by benchmark-paper metrics
- Vendored, downloaded, and evaluated SCUNet, Restormer, NAFNet, HAT, and DRCT in addition to the original Real-ESRGAN/SwinIR pair; added BSRGAN as a third keeper
- Judged by eye (detail, sharpness, artifacts, naturalness) plus measured speed/VRAM on the target 4GB GPU, not automated metrics — see `PROJECT_OVERVIEW.md`'s "Model selection" section for what was found and why each rejected candidate was cut
- **Exit criteria**: a final, evidence-based V1 model set — `realesr-general-x4v3`, `swinir-m`, `bsrgan` — met

## Milestone 3 — Before/after polish ✅ Done
- Zoom/pan to 100%, synchronized between before and after
- Draggable comparison slider
- Stat line (processing time, device used)
- Quick-flicker keyboard toggle
- **Exit criteria**: the comparison experience is the thing you'd put in a demo GIF

## Milestone 4 (V1.1) — Batch processing ✅ Done
- Multi-select images via file dialog (ctrl/shift-click) or drag-and-drop — not folder-only
- Scrollable horizontal thumbnail filmstrip docked at the bottom of the window (~10 visible at once); each thumbnail always shows the **original** image, never the enhanced result
- Clicking a thumbnail loads that image into the existing before/after view above, which is otherwise unchanged
- Thumbnails are individually removable from the batch without clearing the whole set
- Per-image enhanced results persist in memory keyed to their thumbnail — switching away and back shows the already-computed result instead of re-running
- Two run modes: a global "Run" processes every image in the batch in sequence (per-thumbnail progress indicator + overall progress bar); a per-image re-run re-processes just the selected thumbnail (e.g. after changing model/preset) without touching the rest
- Cancel stops after the image currently being processed finishes — earlier results are kept, later images are left untouched
- "Save All" exports every enhanced result to a chosen output folder in one go, with output filename collisions handled; the existing single-image Save still works on whichever thumbnail is selected
- UI-only addition — the engine already processes one image at a time by design
- **Exit criteria**: select 50 images, run the batch, scrub through the filmstrip inspecting before/after per image, cancel partway through and confirm completed ones are kept, then Save All

## V1 portfolio wrap-up (not started)
- Unit tests on `engine/` (corrupted file, tiny image, odd channel count, tiling boundary)
- README with demo GIF, architecture note (`engine`/`ui` separation), and an explicit "Known limitations" section

---

## V2 — Restoration pipeline
- **Face restoration** (GFPGAN as an optional pass, or RestoreFormer++ if a commercially-clean option is wanted without resolving GFPGAN's licensing question — see `PROJECT_OVERVIEW.md`'s "Model selection" section) — note both are general restoration models applied to a face-detected/aligned crop, a genuinely different pipeline shape than V1's whole-image restoration, not just another registry entry
- **Colorization** (DeOldify or DDColor) for B&W photos
- **Inpainting** (LaMa) for scratches/damage — completes the "restore an old photo" pipeline
- Minimal model-registry abstraction in `engine/` to support multiple optional stages cleanly

## Packaging (not started) — moved here from V1; do once V2 (face restoration, colorization, inpainting) is done, so the packaged app reflects real quality, not just the whole-image V1 pipeline
- `QSettings` for last-used folder
- PyInstaller build
- Windows installer/distribution: tool choice deferred until this milestone starts. Options: NSIS (free for commercial use at any version), Inno Setup ≤6.4.3 (last version free for commercial use — 6.5+ requires a paid license if used commercially), or skip a formal installer and just zip the PyInstaller output as a portable distribution
- Bundled model weights (covering the full V1+V2 model set by this point)
- **Exit criteria**: a Windows installer or portable package that runs on a clean machine with no Python installed

## V3+ — Not committed, revisit only once V1/V2 are real
- ONNX + DirectML for non-NVIDIA GPU support
- A hosted inference service (reusing `engine/` as-is) if a web or mobile client is actually decided on
- Any monetization mechanics, once the business model is actually chosen
