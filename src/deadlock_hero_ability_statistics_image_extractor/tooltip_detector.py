import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import pyautogui
import time
import asyncio
from ultralytics import YOLO

class TooltipDetector:
    def __init__(self, debug=False):
        # The training script saves the best model in runs/detect/train/weights/best.pt
        self.model_path = Path("runs/detect/train/weights/best.pt")
        self.model = None
        self.load_model()
        self.debug = debug

    def load_model(self):
        print("Loading YOLOv8 tooltip detection model...")
        if self.model_path.exists():
            try:
                self.model = YOLO(self.model_path)
                print("YOLOv8 model loaded successfully.")
            except Exception as e:
                print(f"Error loading YOLOv8 model: {e}")
        else:
            print(f"WARNING: Trained model not found at '{self.model_path}'.")
            print("Please run the YOLO training script first.")

    def detect_with_ml_model(self, screenshot: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        if self.model is None:
            return None

        # The model expects RGB images, which pyautogui provides
        results = self.model(screenshot, verbose=False)

        # Assumes one detection per screen for simplicity
        for result in results:
            if len(result.boxes) > 0:
                # Get the box with the highest confidence
                best_box = sorted(result.boxes, key=lambda b: b.conf, reverse=True)[0]
                coords = best_box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = coords
                confidence = best_box.conf[0].cpu().numpy()
                print(f"YOLO found tooltip with confidence {confidence:.2f}")
                return (x1, y1, x2 - x1, y2 - y1)
        
        return None

    async def wait_for_tooltip(self, timeout: float = 3.0) -> Optional[Tuple[int, int, int, int]]:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # pyautogui.screenshot() returns a PIL Image in RGB format
            screenshot_pil = pyautogui.screenshot()
            screenshot_np = np.array(screenshot_pil)
            
            tooltip_region = self.detect_with_ml_model(screenshot_np)
            
            if tooltip_region:
                print(f"YOLO detected tooltip at: {tooltip_region}")
                return tooltip_region
                
            await asyncio.sleep(0.2)
            
        print("YOLO Model could not detect a tooltip.")
        return None

    async def capture_tooltip(self, hover_position: Tuple[int, int], wait_time: float = 0.7) -> Optional[dict]:
        pyautogui.moveTo(hover_position[0], hover_position[1])
        await asyncio.sleep(wait_time)
        
        tooltip_region = await self.wait_for_tooltip(timeout=3.0)
        
        if tooltip_region:
            x, y, w, h = tooltip_region
            screenshot = pyautogui.screenshot()
            
            tooltip_image = screenshot.crop((x, y, x + w, y + h))
            
            return {
                "image": tooltip_image,
                "region": (x, y, w, h),
                "hover_position": hover_position
            }
            
        return None

    async def capture_ability_tooltip(self, hover_position: Tuple[int, int], hero_id: int, ability_index: int, wait_time: float = 0.7) -> Optional[dict]:
        return await self.capture_tooltip(hover_position, wait_time)

    async def capture_stat_tooltip(self, hover_position: Tuple[int, int], hero_id: int, stat_name: str, wait_time: float = 0.7) -> Optional[dict]:
        return await self.capture_tooltip(hover_position, wait_time)