"""
Phase 6 Integration Tests - Vision (NVIDIA Vision, Camera, Face, Objects, Live)
Tests vision components with real APIs.
Run: python -m pytest tests/test_integration_phase6.py -v -s
"""

import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.system.screen import ScreenAnalyzer, get_screen_analyzer


def test_nvidia_vision_screen_describe():
    """Test NVIDIA Vision screen description."""
    from core.system.screen import ScreenAnalyzer
    
    print("Testing NVIDIA Vision screen analysis...")
    analyzer = get_screen_analyzer("nvidia_vision")
    
    image = analyzer.capture_full_screen()
    assert image is not None
    
    result = analyzer.analyze_screen("Describe what you see on this screen in detail")
    print(f"Screen analysis result: {result[:200]}...")
    
    assert isinstance(result, str)
    assert len(result) > 50, "Analysis too short"
    assert "error" not in result.lower() or "not configured" not in result.lower()


def test_nvidia_vision_ocr():
    """Test NVIDIA Vision OCR."""
    from core.system.screen import ScreenAnalyzer
    
    analyzer = get_screen_analyzer("nvidia_vision")
    image = analyzer.capture_full_screen()
    
    result = analyzer.ocr(image)
    print(f"NVIDIA Vision OCR result: {result[:200]}...")
    
    assert isinstance(result, str)


def test_nvidia_vision_find_element():
    """Test finding UI element on screen."""
    from core.system.screen import ScreenAnalyzer
    
    analyzer = get_screen_analyzer("nvidia_vision")
    image = analyzer.capture_full_screen()
    
    result = analyzer.ocr_nvidia_vision(image, "Find the address bar or search box on screen. Return its approximate location.")
    print(f"Find element result: {result[:200]}...")
    
    assert isinstance(result, str)


def test_camera_capture():
    """Test camera capture."""
    from core.vision.camera import CameraManager
    
    print("Testing camera capture...")
    camera = CameraManager()
    
    # List cameras
    cameras = camera.list_cameras()
    print(f"Available cameras: {cameras}")
    
    if cameras:
        # Open first camera
        result = camera.open(cameras[0])
        assert result is True, "Failed to open camera"
        
        # Capture frame
        frame = camera.capture()
        assert frame is not None, "Failed to capture frame"
        
        import cv2
        h, w = frame.shape[:2]
        print(f"Captured frame: {w}x{h}")
        
        camera.close()
        print("Camera test passed")
    else:
        pytest.skip("No cameras available")


def test_face_recognition_enroll():
    """Test face recognition enrollment."""
    from core.vision.face import FaceRecognizer
    from core.vision.camera import CameraManager
    
    print("Testing face recognition...")
    recognizer = FaceRecognizer()
    camera = CameraManager()
    
    cameras = camera.list_cameras()
    if not cameras:
        pytest.skip("No cameras available")
    
    camera.open(cameras[0])
    
    # Capture face
    frame = camera.capture()
    camera.close()
    
    if frame is not None:
        # Try to enroll
        result = recognizer.enroll("TestUser", frame)
        print(f"Enroll result: {result}")
        
        # List enrolled faces
        faces = recognizer.list_faces()
        print(f"Enrolled faces: {faces}")
        
        assert "TestUser" in faces or "enrolled" in str(result).lower()
    else:
        pytest.skip("Could not capture frame")


def test_object_detection():
    """Test YOLOv8 object detection."""
    from core.vision.objects import ObjectDetector
    from core.system.screen import ScreenAnalyzer
    
    print("Testing object detection...")
    detector = ObjectDetector()
    analyzer = get_screen_analyzer()
    
    image = analyzer.capture_full_screen()
    
    # Convert PIL to numpy for YOLO
    import numpy as np
    import cv2
    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    detections = detector.detect(frame)
    print(f"Detections: {len(detections)} objects found")
    
    for det in detections[:5]:
        print(f"  - {det['class']}: {det['confidence']:.2f} at {det['bbox']}")
    
    assert isinstance(detections, list)


def test_vision_skills():
    """Test vision skills through ChatEngine."""
    from core.chat_engine import ChatEngine
    from core.memory import Memory
    from providers.nvidia_provider import NVIDIAProvider
    
    print("Testing vision skills via ChatEngine...")
    memory = Memory(db_path="test_vision.db")
    provider = NVIDIAProvider()
    engine = ChatEngine(provider=provider, memory=memory, use_intents=True, enable_semantic_memory=False)
    
    # Test describe screen skill
    reply = engine.respond("what's on my screen")
    print(f"Describe screen reply: {reply[:200]}...")
    
    # Should contain some analysis
    assert isinstance(reply, str)
    assert len(reply) > 10


def test_vision_live_screen():
    """Test live screen vision skill."""
    from core.chat_engine import ChatEngine
    from core.memory import Memory
    from providers.nvidia_provider import NVIDIAProvider
    
    print("Testing live screen vision skill...")
    memory = Memory(db_path="test_vision_live.db")
    provider = NVIDIAProvider()
    engine = ChatEngine(provider=provider, memory=memory, use_intents=True, enable_semantic_memory=False)
    
    # Test start live screen
    reply = engine.respond("start live screen vision")
    print(f"Live screen start reply: {reply}")
    
    import time
    time.sleep(3)
    
    # Get latest analysis
    reply = engine.respond("get latest screen share analysis")
    print(f"Live screen analysis: {reply[:200]}...")
    
    # Stop live screen
    reply = engine.respond("stop live screen vision")
    print(f"Live screen stop reply: {reply}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])