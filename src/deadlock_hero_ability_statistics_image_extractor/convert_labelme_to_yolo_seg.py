import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert LabelMe polygon annotations to YOLO segmentation labels"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="LabelMe annotation path (a .json file or directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for YOLO segmentation .txt labels",
    )
    parser.add_argument(
        "--class-map",
        nargs="+",
        default=["tooltip=0"],
        help="Class mapping entries like 'tooltip=0' 'other_label=1'",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on invalid shapes instead of skipping them",
    )
    return parser


def parse_class_map(entries: Sequence[str]) -> Dict[str, int]:
    class_map: Dict[str, int] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(
                f"Invalid class map entry '{entry}'. Expected format 'label=id'."
            )

        label, class_id_str = entry.split("=", 1)
        label = label.strip()
        class_id_str = class_id_str.strip()

        if not label:
            raise ValueError(f"Invalid class map entry '{entry}': empty label.")

        try:
            class_id = int(class_id_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid class id in class map entry '{entry}'."
            ) from exc

        if class_id < 0:
            raise ValueError(f"Class id must be non-negative in '{entry}'.")

        class_map[label] = class_id

    return class_map


def collect_annotation_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".json":
            raise ValueError("--input file must be a .json LabelMe annotation file.")
        return [input_path]

    if input_path.is_dir():
        return sorted(input_path.rglob("*.json"))

    raise ValueError(f"Input path does not exist: {input_path}")


def load_annotation(annotation_path: Path) -> Dict[str, object]:
    with annotation_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Annotation JSON must be an object: {annotation_path}")
    return payload


def resolve_image_size(annotation_path: Path, payload: Dict[str, object]) -> Tuple[int, int]:
    image_width = payload.get("imageWidth")
    image_height = payload.get("imageHeight")

    if isinstance(image_width, int) and isinstance(image_height, int):
        if image_width > 0 and image_height > 0:
            return image_width, image_height

    image_path_raw = payload.get("imagePath")
    if isinstance(image_path_raw, str) and image_path_raw.strip():
        image_path = (annotation_path.parent / image_path_raw).resolve()
        if image_path.exists():
            with Image.open(image_path) as image:
                return image.size

    raise ValueError(
        "Could not determine image size from 'imageWidth/imageHeight' "
        f"or imagePath for annotation: {annotation_path}"
    )


def normalize_point(point: Sequence[object], image_width: int, image_height: int) -> Tuple[float, float]:
    if len(point) != 2:
        raise ValueError(f"Invalid point (expected [x, y]): {point}")

    try:
        px = float(point[0])
        py = float(point[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Point contains non-numeric values: {point}") from exc

    x_norm = px / image_width
    y_norm = py / image_height
    return x_norm, y_norm


def is_normalized_point_in_bounds(point: Tuple[float, float], tolerance: float = 1e-6) -> bool:
    x_norm, y_norm = point
    return (
        -tolerance <= x_norm <= 1.0 + tolerance
        and -tolerance <= y_norm <= 1.0 + tolerance
    )


def clamp_normalized_point(point: Tuple[float, float]) -> Tuple[float, float]:
    x_norm, y_norm = point
    x_norm = max(0.0, min(1.0, x_norm))
    y_norm = max(0.0, min(1.0, y_norm))
    return x_norm, y_norm


def convert_shapes_to_yolo_lines(
    shapes: Iterable[object],
    image_width: int,
    image_height: int,
    class_map: Dict[str, int],
    strict: bool,
    annotation_path: Path,
) -> List[str]:
    lines: List[str] = []

    for index, shape in enumerate(shapes):
        if not isinstance(shape, dict):
            if strict:
                raise ValueError(
                    f"Shape #{index} is not an object in {annotation_path}: {shape}"
                )
            print(f"Skipping non-object shape #{index} in {annotation_path.name}")
            continue

        label = shape.get("label")
        if not isinstance(label, str) or not label:
            if strict:
                raise ValueError(f"Shape #{index} has invalid label in {annotation_path}")
            print(f"Skipping shape #{index}: missing label in {annotation_path.name}")
            continue

        if label not in class_map:
            if strict:
                raise ValueError(
                    f"Shape #{index} uses unknown label '{label}' in {annotation_path}"
                )
            print(
                f"Skipping shape #{index}: label '{label}' not in class map "
                f"for {annotation_path.name}"
            )
            continue

        shape_type = shape.get("shape_type", "polygon")
        points = shape.get("points")
        if not isinstance(points, list):
            if strict:
                raise ValueError(
                    f"Shape #{index} must contain a points list in {annotation_path}"
                )
            print(
                f"Skipping shape #{index}: missing points list in {annotation_path.name}"
            )
            continue

        if shape_type in {"polygon", None}:
            if len(points) < 3:
                if strict:
                    raise ValueError(
                        f"Shape #{index} must contain at least 3 points in {annotation_path}"
                    )
                print(
                    f"Skipping shape #{index}: polygon requires at least 3 points "
                    f"in {annotation_path.name}"
                )
                continue
        elif shape_type == "rectangle":
            if len(points) != 2:
                if strict:
                    raise ValueError(
                        f"Shape #{index} rectangle must contain exactly 2 points in "
                        f"{annotation_path}"
                    )
                print(
                    f"Skipping shape #{index}: rectangle requires exactly 2 points "
                    f"in {annotation_path.name}"
                )
                continue

            try:
                x1, y1 = float(points[0][0]), float(points[0][1])
                x2, y2 = float(points[1][0]), float(points[1][1])
            except (TypeError, ValueError, IndexError) as exc:
                if strict:
                    raise ValueError(
                        f"Shape #{index} rectangle has invalid corner points in "
                        f"{annotation_path}"
                    ) from exc
                print(
                    f"Skipping shape #{index}: rectangle has invalid corner points "
                    f"in {annotation_path.name}"
                )
                continue

            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            points = [
                [left, top],
                [right, top],
                [right, bottom],
                [left, bottom],
            ]
        else:
            if strict:
                raise ValueError(
                    f"Shape #{index} has unsupported shape_type '{shape_type}' in "
                    f"{annotation_path}"
                )
            print(
                f"Skipping shape #{index}: unsupported shape_type '{shape_type}' "
                f"in {annotation_path.name}"
            )
            continue

        normalized_points: List[Tuple[float, float]] = []
        out_of_bounds = False
        for point in points:
            normalized = normalize_point(point, image_width, image_height)
            if not is_normalized_point_in_bounds(normalized):
                out_of_bounds = True
            normalized_points.append(clamp_normalized_point(normalized))

        if out_of_bounds:
            message = (
                f"Shape #{index} in {annotation_path.name} had out-of-bounds points; "
                "values were clamped to [0, 1]."
            )
            if strict:
                raise ValueError(message)
            print(f"WARNING: {message}")

        class_id = class_map[label]
        flattened = [coord for point in normalized_points for coord in point]
        coords_text = " ".join(f"{coord:.6f}" for coord in flattened)
        lines.append(f"{class_id} {coords_text}")

    return lines


def convert_annotation_file(
    annotation_path: Path,
    output_dir: Path,
    class_map: Dict[str, int],
    strict: bool,
) -> int:
    payload = load_annotation(annotation_path)
    image_width, image_height = resolve_image_size(annotation_path, payload)

    shapes = payload.get("shapes")
    if not isinstance(shapes, list):
        raise ValueError(f"'shapes' must be a list in annotation: {annotation_path}")

    yolo_lines = convert_shapes_to_yolo_lines(
        shapes,
        image_width,
        image_height,
        class_map,
        strict,
        annotation_path,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{annotation_path.stem}.txt"
    output_path.write_text("\n".join(yolo_lines), encoding="utf-8")

    return len(yolo_lines)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    class_map = parse_class_map(args.class_map)
    annotation_files = collect_annotation_files(args.input)

    if not annotation_files:
        print(f"No LabelMe JSON files found in: {args.input}")
        return

    converted_files = 0
    converted_shapes = 0

    for annotation_path in annotation_files:
        shape_count = convert_annotation_file(
            annotation_path=annotation_path,
            output_dir=args.output,
            class_map=class_map,
            strict=args.strict,
        )
        converted_files += 1
        converted_shapes += shape_count
        print(
            f"Converted {annotation_path.name} -> {annotation_path.stem}.txt "
            f"({shape_count} polygons)"
        )

    print(
        f"Done. Converted {converted_files} file(s) with {converted_shapes} total polygon(s)."
    )


if __name__ == "__main__":
    main()
