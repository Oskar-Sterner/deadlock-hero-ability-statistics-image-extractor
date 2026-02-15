import numpy as np
from PIL import Image

from deadlock_hero_ability_statistics_image_extractor.tooltip_detector import (
    TooltipDetector,
)


def test_build_tooltip_image_uses_opaque_rectangular_crop_when_polygon_present():
    screenshot = Image.new("RGB", (16, 16), color=(20, 30, 40))
    bbox_xywh = (4, 4, 8, 8)
    polygon = np.array([[6, 6], [10, 6], [10, 10], [6, 10]], dtype=float)

    tooltip_image = TooltipDetector._build_tooltip_image(screenshot, bbox_xywh, polygon)

    assert tooltip_image.mode == "RGB"
    assert tooltip_image.size == (8, 8)
    assert tooltip_image.getpixel((0, 0)) == (20, 30, 40)
    assert tooltip_image.getpixel((3, 3)) == (20, 30, 40)


def test_build_tooltip_image_without_polygon_is_opaque():
    screenshot = Image.new("RGB", (12, 12), color=(100, 120, 140))
    bbox_xywh = (2, 2, 6, 6)

    tooltip_image = TooltipDetector._build_tooltip_image(screenshot, bbox_xywh, None)

    assert tooltip_image.mode == "RGB"
    assert tooltip_image.size == (6, 6)
    assert tooltip_image.getpixel((1, 1)) == (100, 120, 140)


def test_build_tooltip_image_with_components_still_returns_opaque_rectangular_crop():
    screenshot = Image.new("RGB", (24, 12), color=(80, 90, 100))
    bbox_xywh = (0, 0, 24, 12)
    components = [
        {
            "bbox_xywh": (2, 2, 7, 6),
            "polygon": None,
        },
        {
            "bbox_xywh": (14, 2, 7, 6),
            "polygon": None,
        },
    ]

    tooltip_image = TooltipDetector._build_tooltip_image(
        screenshot,
        bbox_xywh,
        polygon=None,
        components=components,
    )

    assert tooltip_image.mode == "RGB"
    assert tooltip_image.size == (24, 12)
    assert tooltip_image.getpixel((4, 4)) == (80, 90, 100)
    assert tooltip_image.getpixel((16, 4)) == (80, 90, 100)
    assert tooltip_image.getpixel((11, 4)) == (80, 90, 100)
