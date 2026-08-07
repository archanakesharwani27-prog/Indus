"""
ObjectDetector - Object detection for UI elements and general objects
"""

import os
import cv2
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from PIL import Image

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


@dataclass
class DetectedObject:
    """Detected object in image."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    class_id: int


class ObjectDetector:
    """Object detection using YOLO or other models."""
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        device: str = "auto"  # "cpu", "cuda", "auto"
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._model = None
        self._class_names = {}
        self._init_model()
    
    def _init_model(self):
        if not YOLO_AVAILABLE:
            return
        
        try:
            self._model = YOLO(self.model_path)
            self._class_names = self._model.names
        except Exception as e:
            print(f"YOLO model init failed: {e}")
            self._model = None
    
    def detect(
        self,
        image: Image.Image,
        classes: Optional[List[str]] = None
    ) -> List[DetectedObject]:
        """Detect objects in image."""
        if not self._model:
            return []
        
        # Convert PIL to numpy
        img_array = np.array(image)
        
        # Run inference
        results = self._model(img_array, verbose=False, conf=self.confidence_threshold)
        
        objects = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                
                class_name = self._class_names.get(cls_id, str(cls_id))
                
                # Filter by class if specified
                if classes and class_name not in classes:
                    continue
                
                objects.append(DetectedObject(
                    class_name=class_name,
                    confidence=conf,
                    bbox=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                    class_id=cls_id
                ))
        
        return objects
    
    def detect_ui_elements(self, image: Image.Image) -> List[DetectedObject]:
        """Detect common UI elements (buttons, inputs, etc.)."""
        # Common UI element classes in COCO dataset
        ui_classes = [
            "button", "input", "textbox", "checkbox", "radio",
            "link", "menu", "dropdown", "slider", "tab",
            "window", "dialog", "tooltip", "icon", "image"
        ]
        
        # YOLOv8 COCO classes that map to UI elements
        coco_ui_mapping = {
            0: "person",  # Not UI
            62: "tv/monitor",  # Screen
            63: "laptop",  # Laptop screen
            66: "keyboard",
            67: "mouse",
        }
        
        # For now, detect all and filter
        return self.detect(image)
    
    def find_object(
        self,
        image: Image.Image,
        target_class: str
    ) -> Optional[DetectedObject]:
        """Find specific object class."""
        objects = self.detect(image, classes=[target_class])
        return objects[0] if objects else None
    
    def draw_detections(
        self,
        image: Image.Image,
        objects: List[DetectedObject],
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> Image.Image:
        """Draw detection boxes on image."""
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        for obj in objects:
            x1, y1, x2, y2 = obj.bbox
            
            # Draw box
            cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{obj.class_name} {obj.confidence:.2f}"
            cv2.putText(
                img_bgr, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )
        
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img_rgb)
    
    def get_available_classes(self) -> Dict[int, str]:
        """Get available class names."""
        return self._class_names.copy()


class ScreenElementDetector:
    """Specialized detector for screen UI elements using template matching or heuristics."""
    
    def __init__(self):
        self._templates = {}
    
    def find_button(self, image: Image.Image, text: str = "") -> List[Tuple[int, int, int, int]]:
        """Find buttons on screen (heuristic-based)."""
        # Convert to grayscale
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Find rectangular contours that could be buttons
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = w / h if h > 0 else 0
            
            # Button-like: roughly rectangular, reasonable size
            if 0.5 < aspect_ratio < 5 and 30 < w < 300 and 15 < h < 80:
                buttons.append((x, y, x + w, y + h))
        
        return buttons
    
    def find_text_field(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Find text input fields."""
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Look for horizontal lines (bottom of text fields)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fields = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 100 and h < 5:
                fields.append((x, y, x + w, y + h))
        
        return fields
    
    def find_clickable_elements(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Find all potentially clickable elements."""
        buttons = self.find_button(image)
        fields = self.find_text_field(image)
        
        elements = []
        for bbox in buttons:
            elements.append({
                "type": "button",
                "bbox": bbox,
                "center": ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
            })
        
        for bbox in fields:
            elements.append({
                "type": "text_field",
                "bbox": bbox,
                "center": ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
            })
        
        return elements


# Global instances
_object_detector: Optional[ObjectDetector] = None
_screen_element_detector: Optional[ScreenElementDetector] = None


def get_object_detector(model_path: str = "yolov8n.pt", **kwargs) -> ObjectDetector:
    global _object_detector
    if _object_detector is None:
        _object_detector = ObjectDetector(model_path, **kwargs)
    return _object_detector


def get_screen_element_detector() -> ScreenElementDetector:
    global _screen_element_detector
    if _screen_element_detector is None:
        _screen_element_detector = ScreenElementDetector()
    return _screen_element_detector