"""
LiveVisionStream - Real-time camera/screen streaming with vision LLM analysis
Like Gemini Live: continuous visual understanding
"""

import threading
import time
import queue
from typing import Optional, Generator, Callable, Literal
from dataclasses import dataclass
from PIL import Image
import io
import base64

from core.vision.screen import get_screen_understanding
from core.vision.camera import get_camera_manager


@dataclass
class LiveVisionResult:
    """Result from live vision analysis."""
    description: str
    model_used: str
    timestamp: float
    source: str  # "camera" or "screen"
    frame_number: int


class LiveVisionStream:
    """
    Real-time vision streaming - continuous analysis of camera or screen.
    
    Usage:
        # Camera live stream
        stream = LiveVisionStream(source="camera", camera_index=0, fps=2)
        stream.start(on_result=callback)
        
        # Screen live stream  
        stream = LiveVisionStream(source="screen", monitor=1, fps=1)
        stream.start(on_result=callback)
    """
    
    def __init__(
        self,
        source: Literal["camera", "screen"] = "screen",
        camera_index: int = 0,
        monitor: int = 1,
        fps: float = 1.0,
        prompt: str = "Describe what you see in detail. Focus on changes since last frame.",
        vision_provider: str = "auto"
    ):
        self.source = source
        self.camera_index = camera_index
        self.monitor = monitor
        self.fps = fps
        self.prompt = prompt
        self.vision_provider = vision_provider
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[LiveVisionResult], None]] = None
        self._result_queue: queue.Queue = queue.Queue(maxsize=10)
        self._frame_count = 0
        self._vision = None
        self._camera = None
        self._screen_analyzer = None
        
    def _init_vision(self):
        """Initialize vision model."""
        if self._vision is None:
            self._vision = get_screen_understanding(provider=self.vision_provider)
    
    def _init_camera(self):
        """Initialize camera."""
        if self._camera is None:
            self._camera = get_camera_manager(self.camera_index)
            self._camera.open()
    
    def _init_screen(self):
        """Initialize screen analyzer."""
        if self._screen_analyzer is None:
            from core.system.screen import get_screen_analyzer
            self._screen_analyzer = get_screen_analyzer("nvidia_vision")
    
    def _capture_frame(self) -> Optional[Image.Image]:
        """Capture frame from source."""
        if self.source == "camera":
            self._init_camera()
            if self._camera and self._camera._cap and self._camera._cap.isOpened():
                return self._camera.capture_frame()
        else:
            self._init_screen()
            if self._screen_analyzer:
                return self._screen_analyzer.capture_monitor(self.monitor)
        return None
    
    def _analyze_frame(self, image: Image.Image) -> LiveVisionResult:
        """Analyze frame with vision LLM."""
        self._init_vision()
        
        if self._vision:
            result = self._vision.analyze_image(image, self.prompt)
            return LiveVisionResult(
                description=result.description,
                model_used=result.model_used,
                timestamp=time.time(),
                source=self.source,
                frame_number=self._frame_count
            )
        
        return LiveVisionResult(
            description="Vision not available",
            model_used="none",
            timestamp=time.time(),
            source=self.source,
            frame_number=self._frame_count
        )
    
    def _run_loop(self):
        """Main streaming loop."""
        interval = 1.0 / self.fps
        
        while self._running:
            start_time = time.time()
            
            # Capture frame
            frame = self._capture_frame()
            if frame:
                self._frame_count += 1
                
                # Analyze
                result = self._analyze_frame(frame)
                
                # Callback
                if self._callback:
                    try:
                        self._callback(result)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
                # Queue for polling
                try:
                    self._result_queue.put_nowait(result)
                except queue.Full:
                    try:
                        self._result_queue.get_nowait()
                        self._result_queue.put_nowait(result)
                    except queue.Empty:
                        pass
            
            # Sleep to maintain FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)
    
    def start(self, callback: Optional[Callable[[LiveVisionResult], None]] = None):
        """Start live vision stream."""
        if self._running:
            return
        
        self._callback = callback
        self._running = True
        self._frame_count = 0
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop live vision stream."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        
        if self._camera:
            self._camera.close()
            self._camera = None
    
    def get_latest(self, timeout: float = 1.0) -> Optional[LiveVisionResult]:
        """Get latest result (blocking)."""
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def iter_results(self) -> Generator[LiveVisionResult, None, None]:
        """Iterate over results (for async use)."""
        while self._running:
            result = self.get_latest(timeout=2.0)
            if result:
                yield result
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class ScreenShareVisionStream:
    """
    Screen share with vision - like sharing screen in video call + AI analysis.
    Captures screen, sends to vision LLM, returns structured analysis.
    """
    
    def __init__(
        self,
        monitor: int = 1,
        fps: float = 2.0,
        prompt: str = "Analyze this screen for: 1) Active application 2) Visible text/code 3) UI elements 4) User activity context"
    ):
        self.monitor = monitor
        self.fps = fps
        self.prompt = prompt
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[LiveVisionResult], None]] = None
        self._result_queue: queue.Queue = queue.Queue(maxsize=10)
        self._frame_count = 0
        self._screen_analyzer = None
        self._vision = None
    
    def _init_components(self):
        if self._screen_analyzer is None:
            from core.system.screen import get_screen_analyzer
            self._screen_analyzer = get_screen_analyzer("nvidia_vision")
        if self._vision is None:
            self._vision = get_screen_understanding(provider="nvidia")
    
    def _capture_and_analyze(self) -> Optional[LiveVisionResult]:
        self._init_components()
        
        if not self._screen_analyzer or not self._vision:
            return None
        
        frame = self._screen_analyzer.capture_monitor(self.monitor)
        if not frame:
            return None
        
        self._frame_count += 1
        result = self._vision.analyze_image(frame, self.prompt)
        
        return LiveVisionResult(
            description=result.description,
            model_used=result.model_used,
            timestamp=time.time(),
            source="screen_share",
            frame_number=self._frame_count
        )
    
    def _run_loop(self):
        interval = 1.0 / self.fps
        
        while self._running:
            start = time.time()
            
            result = self._capture_and_analyze()
            if result:
                if self._callback:
                    try:
                        self._callback(result)
                    except Exception:
                        pass
                try:
                    self._result_queue.put_nowait(result)
                except queue.Full:
                    try:
                        self._result_queue.get_nowait()
                        self._result_queue.put_nowait(result)
                    except queue.Empty:
                        pass
            
            elapsed = time.time() - start
            time.sleep(max(0, interval - elapsed))
    
    def start(self, callback: Optional[Callable[[LiveVisionResult], None]] = None):
        if self._running:
            return
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
    
    def get_latest(self, timeout: float = 1.0) -> Optional[LiveVisionResult]:
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None


# Global instances for easy access
_live_camera_stream: Optional[LiveVisionStream] = None
_live_screen_stream: Optional[LiveVisionStream] = None
_screen_share_stream: Optional[ScreenShareVisionStream] = None


def get_live_camera_stream(
    camera_index: int = 0,
    fps: float = 1.0,
    prompt: str = "Describe what you see in detail"
) -> LiveVisionStream:
    """Get global live camera vision stream."""
    global _live_camera_stream
    if _live_camera_stream is None:
        _live_camera_stream = LiveVisionStream(
            source="camera",
            camera_index=camera_index,
            fps=fps,
            prompt=prompt
        )
    return _live_camera_stream


def get_live_screen_stream(
    monitor: int = 1,
    fps: float = 1.0,
    prompt: str = "Describe what you see on screen in detail"
) -> LiveVisionStream:
    """Get global live screen vision stream."""
    global _live_screen_stream
    if _live_screen_stream is None:
        _live_screen_stream = LiveVisionStream(
            source="screen",
            monitor=monitor,
            fps=fps,
            prompt=prompt
        )
    return _live_screen_stream


def get_screen_share_stream(
    monitor: int = 1,
    fps: float = 2.0,
    prompt: str = "Analyze screen for active app, visible text, UI elements, user context"
) -> ScreenShareVisionStream:
    """Get global screen share vision stream."""
    global _screen_share_stream
    if _screen_share_stream is None:
        _screen_share_stream = ScreenShareVisionStream(
            monitor=monitor,
            fps=fps,
            prompt=prompt
        )
    return _screen_share_stream