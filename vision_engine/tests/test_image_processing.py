
from PIL import Image
import pytest

from vision_engine.image_processing import crop_screenshot
from vision_engine.models import BoundingBox


@pytest.fixture
def screenshot(tmp_path):
    path = tmp_path / "screenshot.png"
    Image.new("RGB", (200, 150), "white").save(path)
    return path


def test_crop_screenshot_returns_expected_size(screenshot):
    box = BoundingBox(x=50, y=40, width=60, height=30)

    result = crop_screenshot(str(screenshot), box, padding=10)

    assert result.size == (80, 50)


def test_crop_screenshot_clamps_padding_at_image_edges(screenshot):
    box = BoundingBox(x=0, y=0, width=30, height=20)

    result = crop_screenshot(str(screenshot), box, padding=20)

    assert result.size == (50, 40)


def test_crop_screenshot_does_not_modify_original(screenshot):
    original_size = Image.open(screenshot).size

    crop_screenshot(
        str(screenshot),
        BoundingBox(x=50, y=40, width=60, height=30),
    )

    assert Image.open(screenshot).size == original_size


def test_crop_screenshot_rejects_negative_padding(screenshot):
    box = BoundingBox(x=50, y=40, width=60, height=30)

    with pytest.raises(ValueError, match="Padding"):
        crop_screenshot(str(screenshot), box, padding=-1)


def test_crop_screenshot_rejects_box_outside_image(screenshot):
    box = BoundingBox(x=180, y=130, width=50, height=30)

    with pytest.raises(ValueError, match="boundaries"):
        crop_screenshot(str(screenshot), box)


def test_crop_screenshot_rejects_missing_file(tmp_path):
    box = BoundingBox(x=10, y=10, width=20, height=20)

    with pytest.raises(ValueError, match="does not exist"):
        crop_screenshot(str(tmp_path / "missing.png"), box)


def test_crop_screenshot_rejects_invalid_image(tmp_path):
    path = tmp_path / "invalid.png"
    path.write_text("not an image", encoding="utf-8")
    box = BoundingBox(x=10, y=10, width=20, height=20)

    with pytest.raises(ValueError, match="valid readable image"):
        crop_screenshot(str(path), box)
