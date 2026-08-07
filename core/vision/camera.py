"""
CameraManager - Camera access for face recognition and visual context
"""

import cv2
import numpy as np
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass
from PIL import Image
import io
import threading
import time


@dataclass
class CameraInfo:
    """Camera device information."""
    index: int
    name: str
    width: int
    height: int
    fps: float


@dataclass
class CameraFrame:
    """Single camera frame."""
    image: Image.Image
    timestamp: float
    camera_index: int


class CameraManager:
    """Manage camera devices for capture and streaming."""
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._capture_thread: Optional[threading.Thread] = None
    
    def list_cameras(self) -> List[CameraInfo]:
        """List available camera devices."""
        cameras = []
        for i in range(10):  # Check first 10 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                cameras.append(CameraInfo(
                    index=i,
                    name=f"Camera {i}",
                    width=width,
                    height=height,
                    fps=fps
                ))
                cap.release()
            else:
                break
        return cameras
    
    def open(self, camera_index: Optional[int] = None) -> bool:
        """Open camera device."""
        if camera_index is not None:
            self.camera_index = camera_index
        
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            return False
        
        # Set reasonable defaults
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._cap.set(cv2.CAP_PROP_FPS, 30)
        
        return True
    
    def close(self):
        """Close camera device."""
        self.stop_capture()
        if self._cap:
            self._cap.release()
            self._cap = None
    
    def capture_frame(self) -> Optional[Image.Image]:
        """Capture single frame."""
        if not self._cap or not self._cap.isOpened():
            if not self.open():
                return None
        
        ret, frame = self._cap.read()
        if not ret:
            return None
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    
    def capture_frame_bytes(self) -> Optional[bytes]:
        """Capture single frame as JPEG bytes."""
        img = self.capture_frame()
        if not img:
            return None
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
    
    def start_capture(self, callback=None):
        """Start continuous frame capture in background thread."""
        if self._running:
            return
        
        if not self._cap or not self._cap.isOpened():
            if not self.open():
                return False
        
        self._running = True
        
        def capture_loop():
            while self._running and self._cap and self._cap.isOpened():
                ret, frame = self._cap.read()
                if ret:
                    with self._frame_lock:
                        self._latest_frame = frame.copy()
                    if callback:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        callback(Image.fromarray(frame_rgb))
                time.sleep(1/30)  # ~30 FPS
        
        self._capture_thread = threading.Thread(target=capture_loop, daemon=True)
        self._capture_thread.start()
        return True
    
    def stop_capture(self):
        """Stop continuous frame capture."""
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2)
            self._capture_thread = None
    
    def get_latest_frame(self) -> Optional[Image.Image]:
        """Get latest captured frame."""
        with self._frame_lock:
            if self._latest_frame is not None:
                frame_rgb = cv2.cvtColor(self._latest_frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(frame_rgb)
        return None
    
    def get_latest_frame_bytes(self) -> Optional[bytes]:
        """Get latest frame as JPEG bytes."""
        img = self.get_latest_frame()
        if not img:
            return None
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CameraStream:
    """Generator-based camera stream for real-time processing."""
    
    def __init__(self, camera_index: int = 0, fps: int = 30):
        self.camera_index = camera_index
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
    
    def __iter__(self) -> Generator[Image.Image, None, None]:
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            return
        
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        try:
            while True:
                ret, frame = self._cap.read()
                if not ret:
                    break
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yield Image.fromarray(frame_rgb)
        finally:
            if self._cap:
                self._cap.release()
                self._cap = None


# Global instance
_camera_manager: Optional[CameraManager] = None


def get_camera_manager(camera_index: int = 0) -> CameraManager:
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = CameraManager(camera_index)
    return _camera_manager