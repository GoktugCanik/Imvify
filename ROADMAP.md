# Roadmap

Milestones are sequenced so there is always a genuinely working, testable artifact at the end of each one — no long stretch where nothing runnable exists. See `PROJECT_OVERVIEW.md` for the reasoning behind each scope decision.

## Milestone 0 — Environment & skeleton
- Git repo initialized, `.gitignore` for Python/Qt/model weights
- Virtual environment, dependency list pinned (`torch`, `PySide6`, Real-ESRGAN deps)
- Empty `engine/` and `ui/` packages wired through a trivial `main.py` that opens a blank window
- **Exit criteria**: app launches to an empty window from a fresh clone + install

## Milestone 1 — Engine core, headless (no UI)
- `engine/enhance.py`: load an image, run a ×4 restoration model (Real-ESRGAN/SwinIR), resize the result back to the input's original dimensions, save it — as a plain function callable from a script/CLI, no Qt involved
- CUDA-if-available / CPU-fallback device selection
- Tiled inference for large images (this is the technically riskiest piece — de-risk it here, before any UI complexity is layered on)
- Handle non-RGB inputs (alpha, grayscale, CMYK) and EXIF orientation correctly
- **Exit criteria**: `python -m engine.enhance input.jpg output.png --model swinir-m` works correctly on a range of real test images, including a large one that would OOM without tiling

## Milestone 2 — Minimal UI around the engine
- Open image (file dialog + drag & drop), preview pane
- Model/quality preset selection, if more than one weight set is bundled
- Run button → background-thread inference → progress indication
- Cancel, honored between tiles
- GPU/CPU indicator
- Save/export with format + quality choice
- Specific error handling: corrupted file, unsupported format, oversized-image warning before running
- **Exit criteria**: a complete, crash-resistant single-image workflow — this is the first genuinely usable version of the app

## Milestone 3 — Before/after polish
- Zoom/pan to 100%, synchronized between before and after
- Draggable comparison slider
- Stat line (processing time, device used)
- Quick-flicker keyboard toggle
- **Exit criteria**: the comparison experience is the thing you'd put in a demo GIF

## Milestone 4 — Packaging
- `QSettings` for last-used folder
- PyInstaller build
- Inno Setup installer, bundled model weights
- **Exit criteria**: a `.exe` installer that runs on a clean Windows machine with no Python installed

## Milestone 5 (V1.1) — Batch processing
- Folder-in → folder-out queue, per-file + overall progress, cancel-mid-batch, output filename collisions handled
- UI-only addition — the engine already processes one image at a time by design
- **Exit criteria**: point it at a folder of old photos and walk away

## V1 portfolio wrap-up (before calling it done)
- Unit tests on `engine/` (corrupted file, tiny image, odd channel count, tiling boundary)
- README with demo GIF, architecture note (`engine`/`ui` separation), and an explicit "Known limitations" section

---

## V2 — Restoration pipeline
- **Face restoration** (GFPGAN as an optional pass) — gate on resolving the StyleGAN2 commercial-licensing question from `PROJECT_OVERVIEW.md` if the project is going commercial by this point; otherwise proceed for non-commercial use
- **Colorization** (DeOldify or DDColor) for B&W photos
- **Inpainting** (LaMa) for scratches/damage — completes the "restore an old photo" pipeline
- Minimal model-registry abstraction in `engine/` to support multiple optional stages cleanly

## V3+ — Not committed, revisit only once V1/V2 are real
- ONNX + DirectML for non-NVIDIA GPU support
- A hosted inference service (reusing `engine/` as-is) if a web or mobile client is actually decided on
- Any monetization mechanics, once the business model is actually chosen
