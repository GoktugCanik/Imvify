"""Model registry: which weight files exist, what architecture they load into,
and how to build/load a ready-to-run model from a name in MODEL_CONFIGS.
"""
import torch

from .srvgg_arch import SRVGGNetCompact
from .swinir_arch import SwinIR

from pathlib import Path

WEIGHTS_DIR = Path(__file__).parent / "weights"

MODEL_CONFIGS = {
    "realesr-general-x4v3": {
        "path": WEIGHTS_DIR / "realesr-general-x4v3.pth",
        "denoise_path": WEIGHTS_DIR / "realesr-general-wdn-x4v3.pth",
        "scale": 4,
        "arch": "srvgg",
    },
    # Real-world SR variant (BSRGAN degradation model, GAN-trained), from
    # https://github.com/JingyunLiang/SwinIR (Apache-2.0). Much heavier than
    # x4v3 - expect to need a smaller tile_size.
    "swinir-m": {
        "path": WEIGHTS_DIR / "SwinIR-M_x4_GAN.pth",
        "scale": 4,
        "arch": "swinir",
        "swinir_kwargs": dict(
            embed_dim=180, depths=[6, 6, 6, 6, 6, 6], num_heads=[6, 6, 6, 6, 6, 6],
            mlp_ratio=2, resi_connection="1conv",
        ),
    },
}


def _extract_state_dict(state):
    return state.get("params_ema") or state.get("params") or state


def _load_state_dict(config, denoise_strength):
    """Load the model's weights, optionally blended with its denoise ('wdn') variant.

    denoise_strength=1.0 is the plain model (max sharpness/detail); 0.0 is the
    fully denoised variant (smoother, less GAN-hallucinated texture); values
    in between linearly interpolate the two weight sets (the "dni" technique
    from the official Real-ESRGAN inference script). Only realesr-general-x4v3
    has a denoise_path, so this is a no-op for every other model.
    """
    state_dict = _extract_state_dict(torch.load(config["path"], map_location="cpu"))
    if "denoise_path" not in config or denoise_strength >= 1.0:
        return state_dict

    denoise_state_dict = _extract_state_dict(torch.load(config["denoise_path"], map_location="cpu"))
    denoise_strength = max(0.0, denoise_strength)
    return {
        k: denoise_strength * v + (1 - denoise_strength) * denoise_state_dict[k]
        for k, v in state_dict.items()
    }


def _build_model(config):
    arch = config["arch"]
    if arch == "srvgg":
        return SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=config["scale"], act_type="prelu")
    if arch == "swinir":
        return SwinIR(
            upscale=config["scale"], in_chans=3, img_size=64, window_size=8,
            img_range=1., upsampler="nearest+conv", **config["swinir_kwargs"],
        )
    raise ValueError(f"Unknown arch: {arch}")


def load_model(model_name, device, denoise_strength=1.0):
    config = MODEL_CONFIGS[model_name]
    model = _build_model(config)
    model.load_state_dict(_load_state_dict(config, denoise_strength))
    model.eval().to(device)
    return model, config["scale"]
