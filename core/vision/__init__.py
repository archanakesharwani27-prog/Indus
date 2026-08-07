"""
Vision Package - Computer vision and multimodal capabilities
"""

from core.vision.screen import ScreenUnderstanding, get_screen_understanding, ScreenAnalysisResult
from core.vision.camera import CameraManager, CameraStream, get_camera_manager, CameraInfo, CameraFrame
from core.vision.face import FaceRecognizer, get_face_recognizer, FaceEncoding, DetectedFace
from core.vision.objects import ObjectDetector, ScreenElementDetector, get_object_detector, get_screen_element_detector, DetectedObject
from core.vision.live import LiveVisionStream, ScreenShareVisionStream, get_live_camera_stream, get_live_screen_stream, get_screen_share_stream, LiveVisionResult

__all__ = [
    "ScreenUnderstanding",
    "get_screen_understanding",
    "ScreenAnalysisResult",
    "CameraManager",
    "CameraStream",
    "get_camera_manager",
    "CameraInfo",
    "CameraFrame",
    "FaceRecognizer",
    "get_face_recognizer",
    "FaceEncoding",
    "DetectedFace",
    "ObjectDetector",
    "ScreenElementDetector",
    "get_object_detector",
    "get_screen_element_detector",
    "DetectedObject",
    "LiveVisionStream",
    "ScreenShareVisionStream",
    "get_live_camera_stream",
    "get_live_screen_stream",
    "get_screen_share_stream",
    "LiveVisionResult",
]