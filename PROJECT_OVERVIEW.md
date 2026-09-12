# Imvify — Project Overview

## Vision
Imvify is a Windows desktop application that restores old, low-quality photos using AI — removing noise, blur, and compression artifacts, and reconstructing detail, while always preserving the photo's original dimensions. V1 focuses purely on this restoration step. Internally, the models used to do this work by super-resolving the image and then downsampling the result back to its source size — that's an implementation detail of how these models reconstruct detail, not a user-facing resize/upscale feature. Later phases add face restoration, colorization, and inpainting as additional, optional processing stages on top of the same foundation.

This is primarily a **Python/AI portfolio project**: the goal is a genuinely finished, well-engineered desktop application, not a research demo or a notebook wrapped in a window.

## Status of open decisions
- **Monetization**: undecided. Architecture is kept commercial-neutral (no code/license choices that would block going commercial later), but nothing is built speculatively for a hypothetical paid/web/mobile version.
- **Platform**: Windows-first. A future web or mobile version is a possibility, not a commitment — see "Explicitly out of scope" below.

## Tech stack (V1)
| Layer | Choice | Why |
|---|---|---|
| Language | Python | Single stack across UI and AI code; matches the portfolio's purpose |
| GUI | PySide6 (Qt) | LGPLv3 — safe for closed-source commercial use via normal dynamic linking; no cross-language IPC layer to build/debug |
| Inference | PyTorch + Real-ESRGAN (SRVGG), SwinIR, and BSRGAN (RRDBNet) | Well-supported real-world super-resolution models, used as an internal ×4 restoration step; output is always resized back to the input's original dimensions. Chosen from a wider set of candidates (SCUNet, Restormer, NAFNet, HAT, DRCT) benchmarked directly against real photos — see `benchmark/` |
| GPU acceleration | CUDA when available, CPU fallback | Simplest path for V1; broader GPU-vendor support (ONNX + DirectML) is a deliberate later addition, not a V1 requirement |
| Packaging | PyInstaller → Inno Setup installer | Ships as a real installable Windows app, not "clone and pip install" |

### Explicitly rejected for V1 (and why)
- **FastAPI / local HTTP service** — only pays off with multiple concurrent clients or process isolation needs; for a single desktop app it's a network boundary, serialization, and process-lifecycle cost with no present benefit.
- **ONNX + DirectML** — real and useful eventually (Real-ESRGAN converts cleanly, DirectML support is solid), but is extra conversion/validation work that only matters once broad non-NVIDIA GPU support is actually needed.
- **Designing for a future web/mobile client** — the only future-proofing kept is free: the inference engine is a plain Python package with zero UI imports, so it could be wrapped by a service later without a rewrite. No infrastructure or cross-platform UI framework is adopted speculatively.

## Architecture
```
engine/     - pure Python, no Qt imports. Image I/O, tiling, model inference.
ui/         - PySide6 widgets/windows. Calls into engine/, never the reverse.
main.py     - wires engine + ui together.
benchmark/  - standalone research/evaluation tool, not part of the shipped app.
              Used to decide which restoration models are actually worth
              shipping, by running them against real test photos and
              inspecting output quality directly rather than trusting
              benchmark-paper metrics. See "Model selection" below.
```
This separation is the one deliberate concession to the future: if the engine is ever reused behind a service or in a different UI, it doesn't need to be rewritten — only wrapped.

## Model selection

V1 ships three restoration models: `realesr-general-x4v3`, `swinir-m`, and `bsrgan`. This set was arrived at empirically, not by picking papers with the best benchmark numbers. Several other candidates — SCUNet, Restormer, NAFNet, HAT, and DRCT — were vendored, downloaded, and run through `benchmark/benchmark.py` against a small set of real test photos (a mix of genuinely degraded old photos and normal phone photos), then judged by eye (detail, sharpness, artifacts, naturalness) and by measured speed/VRAM on the target hardware (a 4GB laptop GPU), not by PSNR/SSIM.

Findings that led to the current set:
- **SCUNet, Restormer, NAFNet** — all three are native-resolution (1×) models trained on real-camera-noise benchmarks (SIDD/DND), which turned out to produce little to no visible enhancement on genuinely degraded photos — a mismatch between what they were trained for (mild sensor-noise cleanup) and what this product needs (visible restoration of real degradation). NAFNet additionally produced severe corruption artifacts on large uniform-color regions (e.g. a clear sky), which would have been disqualifying on its own.
- **HAT** — comparable quality to SwinIR-M once its own bugs were fixed, but 4-6× slower and needs a workaround to avoid exhausting 4GB of VRAM. Not a good speed/quality tradeoff.
- **DRCT** — also comparable quality to SwinIR-M, but consistently ~30% slower with no visible quality edge to justify it.

Two real integration bugs were found and fixed for HAT and DRCT along the way (both share a SwinIR-derived window-attention architecture that needs input padded to a multiple of its window size before tiled inference, which the reference implementations don't handle in `forward()` — see `engine/swinir_arch.py`'s `check_image_size` for the pattern). Both models were still cut on the merits above.

Two commercially-viable candidates for V2's face-restoration phase were also identified during this same research pass, in case they're relevant later: **RestoreFormer++** and **VQFR** (both Apache-2.0, unlike GFPGAN's licensing-risk StyleGAN2 dependency or CodeFormer's non-commercial license — see the licensing table below). Diffusion-based restoration models (DiffBIR, HYPIR) were investigated and deliberately not pursued for V1 — both require a full Stable Diffusion backbone (5GB+, a fundamentally different multi-step inference pipeline, and much heavier VRAM/time cost), a poor fit for a lightweight desktop tool on modest hardware.

## Licensing notes (verified against primary sources, not assumed)
Distinguish three separate things per model: the **code license**, the **pretrained weights' license**, and any **third-party components the weights depend on** — these can differ.

| Model | Code license | Commercial use | Notes |
|---|---|---|---|
| Real-ESRGAN | BSD-3-Clause | ✅ Permitted | Used in V1. No issues found. |
| SwinIR | Apache 2.0 | ✅ Permitted | Used in V1. No issues found. |
| BSRGAN | Apache 2.0 | ✅ Permitted | Used in V1. No issues found. |
| DeOldify | MIT | ✅ Permitted | Colorization, planned for later phase |
| LaMa | Apache 2.0 | ✅ Permitted | Inpainting, planned for later phase |
| DDColor | Apache 2.0 | ✅ Permitted | Colorization alternative |
| RestoreFormer++ | Apache 2.0 | ✅ Permitted | Face restoration candidate for V2 — no StyleGAN2-prior entanglement like GFPGAN |
| VQFR | Apache 2.0 (code) | ✅ Likely permitted | Face restoration candidate for V2 — uses a vector-quantized codebook, not a restricted GAN prior; weight-specific provenance not independently verified |
| CodeFormer | S-Lab License 1.0 | ❌ Non-commercial only | Explicitly requires contacting authors for commercial use. Avoid unless project stays non-commercial. |
| GFPGAN | Apache 2.0 (code) | ⚠️ Unresolved | Code is Apache 2.0, but relies on a pretrained StyleGAN2 prior whose own license restricts commercial use. TencentARC/GFPGAN discussion #616 ("Is commercial use allowed?") is open and unanswered by maintainers as of April 2025. Treat as commercial-risk until independently resolved or replaced. |
| MAT | CC BY-NC 4.0 | ❌ Non-commercial only | Inpainting alternative to LaMa — explicitly non-commercial, avoid. |

**Practical impact**: V1 (Real-ESRGAN, SwinIR, BSRGAN) carries no known licensing risk for either non-commercial or commercial distribution. The GFPGAN question only needs resolving if it's still the chosen face-restoration model when V2 ships commercially — RestoreFormer++ is a commercially-clean alternative already identified, see "Model selection" above.

## Product scope — V1

**Essential**
- Open image via file dialog + drag & drop
- Image preview with zoom/pan to 100%
- Automatic quality enhancement — output is always restored at the input's original dimensions, with no manual scale/resize selection
- Run with progress indication; cancel mid-run (honored between tiles)
- GPU/CPU indication
- Tiled inference so large images don't crash on limited VRAM/RAM
- Save/export output (format + quality choice)
- Before/after comparison (at minimum a toggle; slider is a near-essential polish item — see below)
- Clear, specific error messages for corrupted files, unsupported formats, and oversized inputs (with a pre-run size/memory warning)
- Correct EXIF-orientation and alpha/grayscale/CMYK input handling

**Nice-to-have for V1**
- ✅ Draggable before/after comparison slider (high portfolio value relative to cost) — done
- Remembered last-used folder via `QSettings` — not done yet
- ✅ Model-variant picker (SwinIR-M / Real-ESRGAN x4v3 / BSRGAN), a quality/speed choice — not a scale choice — done

**Deferred to V1.1**
- Batch processing (folder in → folder out, per-file + overall progress). Deferred specifically so its edge cases (partial failure, cancel-mid-batch, filename collisions) don't complicate the single-image core first — but the engine is designed so this is a UI-only addition, not a redesign.

**Deferred to V2+**
- Face restoration (GFPGAN or RestoreFormer++, see "Model selection" above), colorization (DeOldify/DDColor), inpainting (LaMa)
- In-app model manager / on-demand model downloads
- Advanced settings (manual tile size, denoise strength, etc.)

**Explicitly out of scope for now**
- Web or mobile clients, hosted/cloud inference, user accounts, telemetry, plugin architecture
- Manual scale/resize selection (output dimensions always match the input) — a possible V2+ add-on if a genuine "enlarge" use case shows up, not forgotten, just deliberately cut from an enhancer-focused V1

See `ROADMAP.md` for how this scope is sequenced into concrete milestones.
