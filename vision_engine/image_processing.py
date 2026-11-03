
"""Screenshot cropping and optimization utilities for OmniSight."""

from pathlib import Path

from PIL import Image, ImageOps

from vision_engine.models import BoundingBox


def crop_screenshot(
    screenshot_path: str,
    bounding_box: BoundingBox,
    padding: int = 20,
) -> Image.Image:
    """
    Crop a screenshot around a detected bounding box.

    Adds padding around the target region and clamps coordinates
    to the image boundaries.

    Raises ValueError if the screenshot or bounding box is invalid.
    The original screenshot file is never modified.
    """
    if padding < 0:
        raise ValueError("Padding cannot be negative.")

    path = Path(screenshot_path)

    if not path.is_file():
        raise ValueError(f"Screenshot file does not exist: {screenshot_path}")

    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (OSError, ValueError) as exc:
        raise ValueError("Screenshot is not a valid readable image.") from exc

    image_width, image_height = image.size

    x1 = bounding_box.x
    y1 = bounding_box.y
    x2 = x1 + bounding_box.width
    y2 = y1 + bounding_box.height

    if (
        bounding_box.width <= 0
        or bounding_box.height <= 0
        or x1 < 0
        or y1 < 0
        or x2 > image_width
        or y2 > image_height
    ):
        raise ValueError("Bounding box is outside the screenshot boundaries.")

    left = max(0, int(x1) - padding)
    top = max(0, int(y1) - padding)
    right = min(image_width, int(x2 + padding + 0.999999))
    bottom = min(image_height, int(y2 + padding + 0.999999))

    if right <= left or bottom <= top:
        raise ValueError("Calculated crop area is invalid.")

    return image.crop((left, top, right, bottom))
