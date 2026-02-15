from pathlib import Path

from deadlock_hero_ability_statistics_image_extractor.convert_labelme_to_yolo_seg import (
    convert_shapes_to_yolo_lines,
)


def test_convert_shapes_to_yolo_lines_converts_rectangle_to_four_points():
    shapes = [
        {
            "label": "tooltip",
            "shape_type": "rectangle",
            "points": [[10, 20], [30, 40]],
        }
    ]

    lines = convert_shapes_to_yolo_lines(
        shapes=shapes,
        image_width=100,
        image_height=100,
        class_map={"tooltip": 0},
        strict=True,
        annotation_path=Path("sample.json"),
    )

    assert lines == [
        "0 0.100000 0.200000 0.300000 0.200000 0.300000 0.400000 0.100000 0.400000"
    ]


def test_convert_shapes_to_yolo_lines_keeps_polygon_and_rectangle():
    shapes = [
        {
            "label": "tooltip",
            "shape_type": "polygon",
            "points": [[0, 0], [10, 0], [10, 10]],
        },
        {
            "label": "tooltip",
            "shape_type": "rectangle",
            "points": [[20, 20], [40, 60]],
        },
    ]

    lines = convert_shapes_to_yolo_lines(
        shapes=shapes,
        image_width=100,
        image_height=100,
        class_map={"tooltip": 0},
        strict=True,
        annotation_path=Path("sample.json"),
    )

    assert len(lines) == 2


def test_convert_shapes_to_yolo_lines_skips_invalid_rectangle_in_non_strict_mode():
    shapes = [
        {
            "label": "tooltip",
            "shape_type": "rectangle",
            "points": [[10, 20]],
        }
    ]

    lines = convert_shapes_to_yolo_lines(
        shapes=shapes,
        image_width=100,
        image_height=100,
        class_map={"tooltip": 0},
        strict=False,
        annotation_path=Path("sample.json"),
    )

    assert lines == []
