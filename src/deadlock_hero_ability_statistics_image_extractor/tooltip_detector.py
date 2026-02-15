import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image
from ultralytics import YOLO

try:
    import pyautogui
except Exception:  # pragma: no cover - depends on host display environment
    pyautogui = None


class TooltipDetector:
    def __init__(
        self,
        debug: bool = False,
        model_paths: Optional[Sequence[Path]] = None,
    ):
        default_model_paths = [
            Path("models/abilities/best.pt"),
            Path("runs/abilities/segment/train/weights/best.pt"),
            Path("runs/segment/train/weights/best.pt"),
            Path("runs/detect/train/weights/best.pt"),
        ]
        self.model_paths = list(model_paths) if model_paths is not None else default_model_paths
        self.model_path: Optional[Path] = None
        self.model = None
        self.debug = debug
        self.load_model()

    @staticmethod
    def _to_numpy(value: Any) -> np.ndarray:
        if value is None:
            return np.asarray([])
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "numpy"):
            value = value.numpy()
        return np.asarray(value)

    @staticmethod
    def _bbox_from_xyxy(
        xyxy: Sequence[float], image_width: int, image_height: int
    ) -> Optional[Tuple[int, int, int, int]]:
        if len(xyxy) != 4:
            return None

        x1 = int(round(float(xyxy[0])))
        y1 = int(round(float(xyxy[1])))
        x2 = int(round(float(xyxy[2])))
        y2 = int(round(float(xyxy[3])))

        x1 = max(0, min(x1, image_width))
        y1 = max(0, min(y1, image_height))
        x2 = max(0, min(x2, image_width))
        y2 = max(0, min(y2, image_height))

        if x2 <= x1 or y2 <= y1:
            return None

        return (x1, y1, x2 - x1, y2 - y1)

    @staticmethod
    def _union_bbox_xywh(
        bbox_a: Tuple[int, int, int, int], bbox_b: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        ax, ay, aw, ah = bbox_a
        bx, by, bw, bh = bbox_b

        x1 = min(ax, bx)
        y1 = min(ay, by)
        x2 = max(ax + aw, bx + bw)
        y2 = max(ay + ah, by + bh)
        return (x1, y1, x2 - x1, y2 - y1)

    @staticmethod
    def _expand_bbox_xywh(
        bbox_xywh: Tuple[int, int, int, int],
        image_width: int,
        image_height: int,
        min_padding_px: int = 4,
        padding_ratio: float = 0.02,
    ) -> Tuple[int, int, int, int]:
        x, y, w, h = bbox_xywh
        if w <= 0 or h <= 0:
            return bbox_xywh

        pad_x = max(min_padding_px, int(round(w * padding_ratio)))
        pad_y = max(min_padding_px, int(round(h * padding_ratio)))

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(image_width, x + w + pad_x)
        y2 = min(image_height, y + h + pad_y)

        if x2 <= x1 or y2 <= y1:
            return bbox_xywh

        return (x1, y1, x2 - x1, y2 - y1)

    @staticmethod
    def _bbox_from_polygon(
        polygon: np.ndarray, image_width: int, image_height: int
    ) -> Optional[Tuple[int, int, int, int]]:
        polygon = np.asarray(polygon, dtype=float)
        if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3:
            return None

        x1 = int(np.floor(np.min(polygon[:, 0])))
        y1 = int(np.floor(np.min(polygon[:, 1])))
        x2 = int(np.ceil(np.max(polygon[:, 0])))
        y2 = int(np.ceil(np.max(polygon[:, 1])))

        x1 = max(0, min(x1, image_width))
        y1 = max(0, min(y1, image_height))
        x2 = max(0, min(x2, image_width))
        y2 = max(0, min(y2, image_height))

        if x2 <= x1 or y2 <= y1:
            return None

        return (x1, y1, x2 - x1, y2 - y1)

    def load_model(self) -> None:
        print("Loading YOLO tooltip model (segmentation-first)...")

        for model_path in self.model_paths:
            if not model_path.exists():
                continue

            try:
                self.model = YOLO(model_path)
                self.model_path = model_path
                print(f"YOLO model loaded successfully from '{model_path}'.")
                return
            except Exception as e:
                print(f"Error loading YOLO model from '{model_path}': {e}")

        searched_paths = ", ".join(str(path) for path in self.model_paths)
        print(f"WARNING: Trained model not found at: {searched_paths}")
        print("Please run the YOLO training script first.")

    @staticmethod
    def _extract_detections(
        result: Any, image_shape: Tuple[int, int, int]
    ) -> List[Dict[str, Any]]:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        boxes_xyxy = TooltipDetector._to_numpy(getattr(boxes, "xyxy", None))
        if boxes_xyxy.size == 0:
            return []

        boxes_xyxy = np.atleast_2d(boxes_xyxy)

        confidences = TooltipDetector._to_numpy(getattr(boxes, "conf", None)).reshape(-1)
        if confidences.size < len(boxes_xyxy):
            padding = len(boxes_xyxy) - confidences.size
            confidences = np.pad(confidences, (0, padding), mode="constant")

        image_height, image_width = image_shape[:2]

        masks = getattr(result, "masks", None)
        mask_polygons = getattr(masks, "xy", None) if masks is not None else None

        detections: List[Dict[str, Any]] = []
        for index, box_xyxy in enumerate(boxes_xyxy):
            bbox_xywh = TooltipDetector._bbox_from_xyxy(box_xyxy, image_width, image_height)
            if bbox_xywh is None:
                continue

            confidence = float(confidences[index]) if confidences.size > index else 0.0
            polygon = None
            has_mask = False

            if mask_polygons is not None and len(mask_polygons) > index:
                candidate_polygon = np.asarray(mask_polygons[index], dtype=float)
                polygon_bbox = TooltipDetector._bbox_from_polygon(
                    candidate_polygon, image_width, image_height
                )
                if polygon_bbox is not None:
                    polygon = candidate_polygon
                    has_mask = True
                    bbox_xywh = TooltipDetector._union_bbox_xywh(bbox_xywh, polygon_bbox)

            x, y, w, h = bbox_xywh
            detections.append(
                {
                    "confidence": confidence,
                    "bbox_xywh": bbox_xywh,
                    "bbox_xyxy": (x, y, x + w, y + h),
                    "region": bbox_xywh,
                    "polygon": polygon,
                    "has_mask": has_mask,
                }
            )

        return detections

    @staticmethod
    def _select_best_detection(
        result: Any, image_shape: Tuple[int, int, int]
    ) -> Optional[Dict[str, Any]]:
        detections = TooltipDetector._extract_detections(result, image_shape)
        if not detections:
            return None

        return max(detections, key=lambda detection: detection["confidence"])

    @staticmethod
    def _boxes_are_close(
        bbox_a_xyxy: Tuple[int, int, int, int],
        bbox_b_xyxy: Tuple[int, int, int, int],
        max_gap: int,
    ) -> bool:
        ax1, ay1, ax2, ay2 = bbox_a_xyxy
        bx1, by1, bx2, by2 = bbox_b_xyxy

        horizontal_gap = max(0, max(ax1, bx1) - min(ax2, bx2))
        vertical_gap = max(0, max(ay1, by1) - min(ay2, by2))
        return horizontal_gap <= max_gap and vertical_gap <= max_gap

    def _merge_detections(
        self, detections: Sequence[Dict[str, Any]], image_shape: Optional[Tuple[int, int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        if not detections:
            return None

        best_detection = max(detections, key=lambda detection: detection["confidence"])

        best_w = int(best_detection["bbox_xywh"][2])
        best_h = int(best_detection["bbox_xywh"][3])
        proximity_gap = max(12, int(min(best_w, best_h) * 0.2))
        confidence_floor = max(0.15, float(best_detection["confidence"]) * 0.35)

        candidates = [
            detection
            for detection in detections
            if float(detection["confidence"]) >= confidence_floor
        ]

        selected: List[Dict[str, Any]] = [best_detection]
        changed = True
        while changed:
            changed = False
            for detection in candidates:
                if any(existing is detection for existing in selected):
                    continue

                if any(
                    TooltipDetector._boxes_are_close(
                        detection["bbox_xyxy"],
                        existing["bbox_xyxy"],
                        proximity_gap,
                    )
                    for existing in selected
                ):
                    selected.append(detection)
                    changed = True

        x1 = min(int(detection["bbox_xyxy"][0]) for detection in selected)
        y1 = min(int(detection["bbox_xyxy"][1]) for detection in selected)
        x2 = max(int(detection["bbox_xyxy"][2]) for detection in selected)
        y2 = max(int(detection["bbox_xyxy"][3]) for detection in selected)

        bbox_xywh = (x1, y1, x2 - x1, y2 - y1)
        if image_shape is not None and len(image_shape) >= 2:
            image_height, image_width = image_shape[:2]
            bbox_xywh = self._expand_bbox_xywh(
                bbox_xywh,
                image_width=image_width,
                image_height=image_height,
            )
            x1, y1, w, h = bbox_xywh
            x2 = x1 + w
            y2 = y1 + h

        return {
            "confidence": float(best_detection["confidence"]),
            "bbox_xywh": bbox_xywh,
            "bbox_xyxy": (x1, y1, x2, y2),
            "region": bbox_xywh,
            "polygon": best_detection["polygon"],
            "has_mask": any(bool(detection["has_mask"]) for detection in selected),
            "components": selected,
            "component_count": len(selected),
        }

    @staticmethod
    def _build_tooltip_image(
        screenshot: Image.Image,
        bbox_xywh: Tuple[int, int, int, int],
        polygon: Optional[np.ndarray],
        components: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Image.Image:
        x, y, w, h = bbox_xywh
        return screenshot.crop((x, y, x + w, y + h)).convert("RGB")

    @staticmethod
    def _require_pyautogui() -> Any:
        if pyautogui is None:
            raise RuntimeError(
                "pyautogui is unavailable in this environment. "
                "Tooltip capture requires an active GUI session."
            )
        return pyautogui

    @staticmethod
    def _take_screenshot(
        screenshot_provider: Optional[Callable[[], Image.Image]] = None,
    ) -> Image.Image:
        if screenshot_provider is not None:
            screenshot = screenshot_provider()
            if isinstance(screenshot, Image.Image):
                return screenshot
            raise RuntimeError("screenshot provider must return a PIL Image.")

        gui = TooltipDetector._require_pyautogui()
        return gui.screenshot()

    def detect_with_ml_model(self, screenshot: np.ndarray) -> Optional[Dict[str, Any]]:
        if self.model is None:
            return None

        results = self.model(screenshot, verbose=False)
        all_detections: List[Dict[str, Any]] = []

        for result in results:
            all_detections.extend(self._extract_detections(result, screenshot.shape))

        merged_detection = self._merge_detections(all_detections, image_shape=screenshot.shape)

        if merged_detection is not None:
            print(
                "YOLO found tooltip with confidence "
                f"{merged_detection['confidence']:.2f} "
                f"across {merged_detection['component_count']} component(s)"
            )

        return merged_detection

    async def wait_for_tooltip(
        self,
        timeout: float = 3.0,
        screenshot_provider: Optional[Callable[[], Image.Image]] = None,
    ) -> Optional[Dict[str, Any]]:
        start_time = time.time()

        while time.time() - start_time < timeout:
            screenshot_pil = self._take_screenshot(screenshot_provider)
            screenshot_np = np.array(screenshot_pil)

            tooltip_detection = self.detect_with_ml_model(screenshot_np)

            if tooltip_detection:
                component_count = int(tooltip_detection.get("component_count", 1))
                print(
                    f"YOLO detected tooltip at: {tooltip_detection['bbox_xywh']} "
                    f"(mask={tooltip_detection['has_mask']}, components={component_count})"
                )
                return tooltip_detection

            await asyncio.sleep(0.2)

        print("YOLO Model could not detect a tooltip.")
        return None

    async def capture_tooltip(
        self,
        hover_position: Tuple[int, int],
        wait_time: float = 0.7,
        move_mouse_callback: Optional[Callable[[int, int], None]] = None,
        screenshot_provider: Optional[Callable[[], Image.Image]] = None,
    ) -> Optional[dict]:
        if move_mouse_callback is not None:
            move_mouse_callback(int(hover_position[0]), int(hover_position[1]))
        else:
            gui = self._require_pyautogui()
            gui.moveTo(hover_position[0], hover_position[1])

        await asyncio.sleep(wait_time)

        tooltip_detection = await self.wait_for_tooltip(
            timeout=3.0,
            screenshot_provider=screenshot_provider,
        )

        if tooltip_detection:
            screenshot = self._take_screenshot(screenshot_provider)

            tooltip_image = self._build_tooltip_image(
                screenshot,
                tooltip_detection["bbox_xywh"],
                tooltip_detection["polygon"],
                components=tooltip_detection.get("components"),
            )

            return {
                "image": tooltip_image,
                "region": tooltip_detection["bbox_xywh"],
                "hover_position": hover_position,
                "confidence": tooltip_detection["confidence"],
                "has_mask": tooltip_detection["has_mask"],
                "component_count": tooltip_detection.get("component_count", 1),
            }

        return None

    async def capture_ability_tooltip(
        self,
        hover_position: Tuple[int, int],
        hero_id: int,
        ability_index: int,
        wait_time: float = 0.7,
        move_mouse_callback: Optional[Callable[[int, int], None]] = None,
        screenshot_provider: Optional[Callable[[], Image.Image]] = None,
    ) -> Optional[dict]:
        return await self.capture_tooltip(
            hover_position,
            wait_time,
            move_mouse_callback=move_mouse_callback,
            screenshot_provider=screenshot_provider,
        )

    async def capture_item_tooltip(
        self,
        hover_position: Tuple[int, int],
        item_id: int,
        item_name: str,
        wait_time: float = 0.7,
        move_mouse_callback: Optional[Callable[[int, int], None]] = None,
        screenshot_provider: Optional[Callable[[], Image.Image]] = None,
    ) -> Optional[dict]:
        return await self.capture_tooltip(
            hover_position,
            wait_time,
            move_mouse_callback=move_mouse_callback,
            screenshot_provider=screenshot_provider,
        )