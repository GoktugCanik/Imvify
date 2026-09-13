# Imvify

An AI photo enhancer for Windows that restores old, low-quality photos — removing noise, blur, and compression artifacts, and reconstructing details.

## Status

**Single-image and batch workflows complete.** Both the restoration engine (`engine/`) and the PySide6 desktop UI (`ui/`) are functional: open one or many images, run them through one of three restoration models, compare before/after, save the result(s). Packaging as a standalone Windows installer is not built yet. See `ROADMAP.md` for the full milestone breakdown and `PROJECT_OVERVIEW.md` for the architecture and scope decisions behind them.

## How it works

- Open one or many images via file dialog (multi-select) or drag & drop; EXIF orientation and alpha/grayscale/CMYK input are handled correctly
- Loaded images appear as a thumbnail filmstrip (always showing the original); click a thumbnail to load it into the before/after view above
- Pick a model, then either **Run** the currently selected image or **Run All** to process every not-yet-run image in the batch in sequence — inference happens on a background thread, tiled so large images don't exhaust limited VRAM/RAM, with per-image and overall progress shown
- Cancel is honored between tiles for a single run; during a batch run, Cancel lets the in-flight image finish and stops before starting the next one — completed results are kept, later images are left untouched and can be resumed with Run All later
- Per-image results are cached in memory, so switching between thumbnails shows the already-computed result instead of re-running
- Compare the result against the original with a draggable before/after slider, zoom/pan to 100%, and a quick-flicker keyboard toggle
- Save the selected result with a format and quality choice, or **Save All** to export every completed result in the batch to a chosen folder in one go (filename collisions are handled automatically)

## Models

| Model | Architecture | Notes |
|---|---|---|
| `realesr-general-x4v3` | SRVGG (Real-ESRGAN) | Fastest of the three; supports blending with a denoise variant |
| `bsrgan` | RRDBNet (BSRGAN) | Same architecture family as the original ESRGAN; mid-speed |
| `swinir-m` | SwinIR | Heaviest of the three; needs a smaller tile size |

All three are real-world super-resolution models chosen for restoring genuinely degraded (not just downscaled) photos, rather than classic bicubic-degradation SR models. They were picked from a wider set of candidates (including SCUNet, Restormer, NAFNet, HAT, and DRCT) benchmarked directly against real test photos — see `benchmark/` below.

## Usage

Run the desktop app:

```bash
python main.py
```

The engine is also directly callable from the CLI, useful for scripting or testing without the UI:

```bash
python -m engine.enhance input.jpg output.png --model swinir-m
```

Options:
- `--model` — `realesr-general-x4v3`, `bsrgan`, or `swinir-m` (default: `swinir-m`)
- `--tile-size` — tile size for tiled inference (default: `200`)
- `--padding` — padding added around each tile to avoid seams (default: `16`)

## Setup

```bash
python -m venv venv
venv\Scripts\activate

# torch/torchvision need PyTorch's own package index for CUDA builds:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
# CPU-only machines can skip that and just:
# pip install torch torchvision

pip install -r requirements.txt
```

Model weights are not included in this repository (see `.gitignore`) and must be placed in `engine/weights/`:
- `realesr-general-x4v3.pth` and `realesr-general-wdn-x4v3.pth` from [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- `SwinIR-M_x4_GAN.pth` from [SwinIR](https://github.com/JingyunLiang/SwinIR)
- `BSRGAN.pth` from [BSRGAN](https://github.com/cszn/BSRGAN)

## Architecture

```
engine/     - pure Python, no Qt imports. Image I/O, tiling, model inference.
ui/         - PySide6 widgets/windows. Calls into engine/, never the reverse.
main.py     - wires engine + ui together; the actual app entry point.
benchmark/  - standalone research/evaluation tool, not part of the shipped app.
              Runs every model in engine/models.py against a folder of test
              images and logs timing/VRAM, so model choices are decided from
              real output on real photos, not spec sheets. See benchmark/benchmark.py.
```

The `engine`/`ui` separation is deliberate: if the engine is ever reused behind a service or a different UI, it doesn't need to be rewritten — only wrapped.

## Roadmap

See `ROADMAP.md` for the full milestone sequence — minimal UI, before/after comparison, packaging as a Windows installer, and batch processing.

Later phases (V2+) add face restoration, colorization, and inpainting as additional, optional processing stages on top of the same restoration foundation. See `PROJECT_OVERVIEW.md` for scope and licensing details on those.

## Credits

The `SRVGGNetCompact`, `SwinIR`, and `RRDBNet` model architectures are vendored (not installed as dependencies) from their original repositories, with minimal changes to drop the `basicsr`/`realesrgan`/`timm` dependencies:
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) (BSD-3-Clause) — `realesr-general-x4v3` architecture and weights
- [SwinIR](https://github.com/JingyunLiang/SwinIR) (Apache-2.0) — `swinir-m` architecture and weights
- [BSRGAN](https://github.com/cszn/BSRGAN) (Apache-2.0) — `bsrgan` architecture and weights

## Known limitations

- No standalone Windows installer yet — must be run from a Python environment (`python main.py`)
- Batch mode is file-select/drag-and-drop only, not folder-in/folder-out — pick individual files (or select many at once) rather than pointing at a folder
- No unit tests yet
- GPU acceleration is CUDA-only; no DirectML/non-NVIDIA GPU support yet
