# Imvify

An AI photo enhancer for Windows that restores old, low-quality photos — removing noise, blur, and compression artifacts, and reconstructing detail — while always preserving the photo's original dimensions.

Under the hood it runs the image through a ×4 super-resolution model and resizes the result back down to the source size; that's an implementation detail of how these models reconstruct detail, not a user-facing resize/upscale feature. This is a Python/AI portfolio project: the goal is a genuinely finished, well-engineered desktop application, not a research demo or a notebook wrapped in a window.

## Status

**Work in progress — headless engine only.** The restoration engine (`engine/`) is functional and callable from the CLI; the PySide6 desktop UI has not been built yet. See `ROADMAP.md` for the full milestone breakdown and `PROJECT_OVERVIEW.md` for the architecture and scope decisions behind them.

## How it works

- Loads an image, EXIF-corrects orientation, and handles alpha/grayscale/CMYK input
- Runs inference through a ×4 restoration model, tiled so large images don't exhaust limited VRAM/RAM
- Resizes the restored output back to the input's exact original dimensions
- Preserves the input's alpha channel, if any

## Models

| Model | Architecture | Notes |
|---|---|---|
| `realesr-general-x4v3` | SRVGG (Real-ESRGAN) | Fast, general-purpose real-world restoration; supports blending with a denoise variant |
| `swinir-m` | SwinIR | Real-world SR variant (BSRGAN degradation, GAN-trained); heavier, needs a smaller tile size |

Both are real-world super-resolution models chosen for restoring genuinely degraded (not just downscaled) photos, rather than classic bicubic-degradation SR models.

## Usage (CLI, current)

```bash
python -m engine.enhance input.jpg output.png --model swinir-m
```

Options:
- `--model` — `realesr-general-x4v3` or `swinir-m` (default: `swinir-m`)
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

## Architecture

```
engine/   - pure Python, no Qt imports. Image I/O, tiling, model inference.
ui/       - PySide6 widgets/windows (not yet built). Calls into engine/, never the reverse.
main.py   - wires engine + ui together (not yet built).
```

The `engine`/`ui` separation is deliberate: if the engine is ever reused behind a service or a different UI, it doesn't need to be rewritten — only wrapped.

## Roadmap

See `ROADMAP.md` for the full milestone sequence — minimal UI, before/after comparison, packaging as a Windows installer, and batch processing.

Later phases (V2+) add face restoration, colorization, and inpainting as additional, optional processing stages on top of the same restoration foundation. See `PROJECT_OVERVIEW.md` for scope and licensing details on those.

## Credits

The `SRVGGNetCompact` and `SwinIR` model architectures are vendored (not installed as dependencies) from their original repositories, with minimal changes to drop the `basicsr`/`realesrgan`/`timm` dependencies:
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) (BSD-3-Clause) — `realesr-general-x4v3` architecture and weights
- [SwinIR](https://github.com/JingyunLiang/SwinIR) (Apache-2.0) — `swinir-m` architecture and weights

## Known limitations

- No UI yet — CLI-only for now
- No unit tests yet
- GPU acceleration is CUDA-only; no DirectML/non-NVIDIA GPU support yet
