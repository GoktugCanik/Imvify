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

## Milestone 4 — Packaging (not started)
- `QSettings` for last-used folder
- PyInstaller build
- Inno Setup installer, bundled model weights
- **Exit criteria**: a `.exe` installer that runs on a clean Windows machine with no Python installed

## Milestone 5 (V1.1) — Batch processing (not started)
- Folder-in → folder-out queue, per-file + overall progress, cancel-mid-batch, output filename collisions handled
- UI-only addition — the engine already processes one image at a time by design
- **Exit criteria**: point it at a folder of old photos and walk away

## V1 portfolio wrap-up (not started)
- Unit tests on `engine/` (corrupted file, tiny image, odd channel count, tiling boundary)
- README with demo GIF, architecture note (`engine`/`ui` separation), and an explicit "Known limitations" section

---

## V2 — Restoration pipeline
- **Face restoration** (GFPGAN as an optional pass, or RestoreFormer++ if a commercially-clean option is wanted without resolving GFPGAN's licensing question — see `PROJECT_OVERVIEW.md`'s "Model selection" section) — note both are general restoration models applied to a face-detected/aligned crop, a genuinely different pipeline shape than V1's whole-image restoration, not just another registry entry
- **Colorization** (DeOldify or DDColor) for B&W photos
- **Inpainting** (LaMa) for scratches/damage — completes the "restore an old photo" pipeline
- Minimal model-registry abstraction in `engine/` to support multiple optional stages cleanly

## V3+ — Not committed, revisit only once V1/V2 are real
- ONNX + DirectML for non-NVIDIA GPU support
- A hosted inference service (reusing `engine/` as-is) if a web or mobile client is actually decided on
- Any monetization mechanics, once the business model is actually chosen
