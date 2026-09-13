import torch 
import pytest
from PIL import Image, UnidentifiedImageError

from engine.enhance import enhance_image

@pytest.fixture
def device():
    return torch.device("cpu")

def test_corrupted_file_raises(tmp_path, device):
    bad_file = tmp_path / "corrupted.jpg"
    bad_file.write_bytes(b"this is not a real image file")

    with pytest.raises(UnidentifiedImageError):
        enhance_image(
            str(bad_file), str(tmp_path / "out.png"),
            model_name="realesr-general-x4v3", device=device,
        )

def test_tiny_image_runs(tmp_path, device):
    input_path = tmp_path / "tiny.png"
    Image.new("RGB", (5, 5), color=(120, 60, 200)).save(input_path)

    result = enhance_image(
        str(input_path), str(tmp_path / "out.png"),
        model_name="realesr-general-x4v3", device=device,
    )

    assert result.size == (5, 5)

def test_grayscale_input_runs(tmp_path, device):
    input_path = tmp_path / "gray.png"
    Image.new("L", (16, 16), color=128).save(input_path)

    result = enhance_image(
        str(input_path), str(tmp_path / "out.png"),
        model_name="realesr-general-x4v3", device=device,
    )

    assert result.size == (16, 16)
    assert result.mode == "RGB"


def test_rgba_input_preserves_alpha(tmp_path, device):
    input_path = tmp_path / "alpha.png"
    Image.new("RGBA", (16, 16), color=(10, 20, 30, 128)).save(input_path)

    result = enhance_image(
        str(input_path), str(tmp_path / "out.png"),
        model_name="realesr-general-x4v3", device=device,
    )

    assert result.size == (16, 16)
    assert result.mode == "RGBA"

@pytest.mark.parametrize("size", [8, 9])
def test_tiling_boundary(tmp_path, device, size):
    input_path = tmp_path / f"boundary_{size}.png"
    Image.new("RGB", (size, size), color=(200, 200, 200)).save(input_path)

    result = enhance_image(
        str(input_path), str(tmp_path / "out.png"),
        model_name="realesr-general-x4v3", tile_size=4, device=device,
    )

    assert result.size == (size, size)