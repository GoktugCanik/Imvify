import time
import torch
import numpy as np
from PIL import Image, ImageOps
from .models import load_model

class EnhanceCancelled(Exception):
    """Raised inside enhance_image when cancel_check() returns True."""

def enhance_image(input_path, output_path, model_name="swinir-m", tile_size=200, padding=16, 
                    device=None, denoise_strength=1.0, progress_callback=None, cancel_check=None):
    start_time = time.perf_counter()
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, scale = load_model(model_name, device, denoise_strength)

    img = ImageOps.exif_transpose(Image.open(input_path))
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    if has_alpha:
        rgba = img.convert("RGBA")
        alpha = rgba.split()[-1]
        img = rgba.convert("RGB")
    else:
        alpha = None
        img = img.convert("RGB")

    arr = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)

    _, _, h, w = tensor.shape
    output = torch.zeros((1, 3, h * scale, w * scale), device=device)

    tiles_y = list(range(0, h, tile_size))
    tiles_x = list(range(0, w, tile_size))
    total_tiles = len(tiles_y) * len(tiles_x)
    tiles_done = 0

    with torch.no_grad():
        for y in range(0, h, tile_size):
            for x in range(0, w, tile_size):
                tile_h = min(tile_size, h - y)
                tile_w = min(tile_size, w - x)

                y0 = max (y - padding, 0)
                x0 = max (x- padding, 0)
                y1= min(y + tile_h + padding, h)
                x1= min(x + tile_w + padding, w)

                tile = tensor[:, :, y0:y1, x0:x1]
                out_tile = model(tile)

                top_pad = (y- y0) * scale
                left_pad = (x- x0) * scale
                out_tile_h = tile_h * scale
                out_tile_w = tile_w * scale

                cropped = out_tile[:, :, top_pad:top_pad + out_tile_h, left_pad:left_pad + out_tile_w]

                output[:, :, y*scale:(y+tile_h)*scale, x*scale:(x+tile_w)*scale] = cropped
                tiles_done += 1
                
                if progress_callback:
                    progress_callback(tiles_done, total_tiles)
                if cancel_check and cancel_check():
                    raise EnhanceCancelled

    out = output.clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    out_img = Image.fromarray((out * 255.0).round().astype(np.uint8))

    out_img = out_img.resize((w, h), Image.LANCZOS)

    if alpha is not None:
        alpha_resized = alpha.resize(out_img.size, Image.LANCZOS)
        out_img.putalpha(alpha_resized)

    out_img.save(output_path)
    print(f"{output_path}: enhanced in {time.perf_counter() - start_time:.2f}s")
    return out_img

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhance an image with Real-ESRGAN/SwinIR.")
    parser.add_argument("input", help="Path to the input image")
    parser.add_argument("output", help="Path to write the enhanced output image")
    parser.add_argument("--model", choices=["realesr-general-x4v3", "swinir-m"], default="swinir-m", help="Which model to run")
    parser.add_argument("--tile-size", type=int, default=200, help="Tile size for tiled inference")
    parser.add_argument("--padding", type=int, default=16, help="Padding added around each tile")
    args = parser.parse_args()

    enhance_image(args.input, args.output, model_name=args.model, tile_size=args.tile_size, padding=args.padding)
