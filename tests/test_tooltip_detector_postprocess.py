import numpy as np

from deadlock_hero_ability_statistics_image_extractor.tooltip_detector import (
    TooltipDetector,
)


class FakeBoxes:
    def __init__(self, xyxy, conf):
        self.xyxy = np.asarray(xyxy, dtype=float)
        self.conf = np.asarray(conf, dtype=float)


class FakeMasks:
    def __init__(self, polygons):
        self.xy = polygons


class FakeResult:
    def __init__(self, boxes, masks=None):
        self.boxes = boxes
        self.masks = masks


def test_bbox_from_polygon_returns_expected_xywh():
    polygon = np.array([[10.1, 20.1], [30.9, 22.0], [25.3, 40.4]], dtype=float)

    bbox = TooltipDetector._bbox_from_polygon(polygon, image_width=100, image_height=100)

    assert bbox == (10, 20, 21, 21)


def test_bbox_from_polygon_requires_at_least_three_points():
    polygon = np.array([[1.0, 1.0], [5.0, 5.0]], dtype=float)

    bbox = TooltipDetector._bbox_from_polygon(polygon, image_width=100, image_height=100)

    assert bbox is None


def test_select_best_detection_uses_union_of_box_and_mask_bbox_when_available():
    detector = TooltipDetector.__new__(TooltipDetector)

    boxes = FakeBoxes(
        xyxy=[[5, 5, 15, 15], [10, 10, 18, 18]],
        conf=[0.25, 0.9],
    )
    masks = FakeMasks(
        polygons=[
            np.array([[5, 5], [15, 5], [15, 15], [5, 15]], dtype=float),
            np.array([[11, 11], [19, 11], [19, 20], [11, 20]], dtype=float),
        ]
    )

    result = FakeResult(boxes=boxes, masks=masks)

    detection = detector._select_best_detection(result, image_shape=(32, 32, 3))

    assert detection is not None
    assert detection["confidence"] == 0.9
    assert detection["has_mask"] is True
    assert detection["bbox_xywh"] == (10, 10, 9, 10)


def test_select_best_detection_falls_back_to_box_when_mask_missing():
    detector = TooltipDetector.__new__(TooltipDetector)

    boxes = FakeBoxes(xyxy=[[2, 3, 12, 13]], conf=[0.8])
    result = FakeResult(boxes=boxes, masks=None)

    detection = detector._select_best_detection(result, image_shape=(20, 20, 3))

    assert detection is not None
    assert detection["has_mask"] is False
    assert detection["bbox_xywh"] == (2, 3, 10, 10)


def test_merge_detections_combines_tooltip_panels_and_ignores_far_noise():
    detector = TooltipDetector.__new__(TooltipDetector)

    detections = [
        {
            "confidence": 0.9,
            "bbox_xywh": (100, 100, 120, 80),
            "bbox_xyxy": (100, 100, 220, 180),
            "region": (100, 100, 120, 80),
            "polygon": np.array([[100, 100], [220, 100], [220, 180], [100, 180]]),
            "has_mask": True,
        },
        {
            "confidence": 0.55,
            "bbox_xywh": (100, 182, 40, 30),
            "bbox_xyxy": (100, 182, 140, 212),
            "region": (100, 182, 40, 30),
            "polygon": None,
            "has_mask": False,
        },
        {
            "confidence": 0.5,
            "bbox_xywh": (145, 182, 40, 30),
            "bbox_xyxy": (145, 182, 185, 212),
            "region": (145, 182, 40, 30),
            "polygon": None,
            "has_mask": False,
        },
        {
            "confidence": 0.48,
            "bbox_xywh": (190, 182, 40, 30),
            "bbox_xyxy": (190, 182, 230, 212),
            "region": (190, 182, 40, 30),
            "polygon": None,
            "has_mask": False,
        },
        {
            "confidence": 0.2,
            "bbox_xywh": (500, 500, 60, 60),
            "bbox_xyxy": (500, 500, 560, 560),
            "region": (500, 500, 60, 60),
            "polygon": None,
            "has_mask": False,
        },
    ]

    merged = detector._merge_detections(detections)

    assert merged is not None
    assert merged["confidence"] == 0.9
    assert merged["component_count"] == 4
    assert merged["bbox_xywh"] == (100, 100, 130, 112)
    assert merged["has_mask"] is True


def test_merge_detections_expands_bbox_with_image_shape_to_reduce_clipping():
    detector = TooltipDetector.__new__(TooltipDetector)

    detections = [
        {
            "confidence": 0.9,
            "bbox_xywh": (100, 120, 200, 160),
            "bbox_xyxy": (100, 120, 300, 280),
            "region": (100, 120, 200, 160),
            "polygon": None,
            "has_mask": False,
        }
    ]

    merged = detector._merge_detections(detections, image_shape=(600, 800, 3))

    assert merged is not None
    x, y, w, h = merged["bbox_xywh"]
    assert x < 100
    assert y < 120
    assert w > 200
    assert h > 160
    assert x >= 0
    assert y >= 0
    assert x + w <= 800
    assert y + h <= 600
