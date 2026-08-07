"""
Vision Skills - Screen understanding, camera, face recognition, object detection
"""

from typing import List
from core.skills.base import BaseSkill, SkillParameter


class VisionDescribeScreenSkill(BaseSkill):
    """Describe what's on the screen using vision LLM."""
    
    @property
    def name(self) -> str:
        return "vision.describe_screen"
    
    @property
    def description(self) -> str:
        return "Analyze and describe screen content using vision AI"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="prompt",
                type="string",
                description="Custom prompt for analysis",
                required=False,
                default="Describe what's on this screen in detail",
            ),
            SkillParameter(
                name="monitor",
                type="number",
                description="Monitor index (1=primary)",
                required=False,
                default=1,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "vision"
    
    @property
    def examples(self) -> List[str]:
        return [
            "What's on my screen?",
            "Describe my screen",
            "Analyze screen content",
        ]
    
    def execute(self, prompt: str = "", monitor: int = 1) -> str:
        try:
            from core.vision.screen import get_screen_understanding
            vision = get_screen_understanding()
            result = vision.analyze_full_screen(prompt or "Describe what's on this screen in detail", monitor)
            return f"Screen Analysis ({result.model_used}):\n{result.description}"
        except Exception as e:
            return f"Screen analysis failed: {e}"


class VisionFindOnScreenSkill(BaseSkill):
    """Find specific element on screen."""
    
    @property
    def name(self) -> str:
        return "vision.find_on_screen"
    
    @property
    def description(self) -> str:
        return "Find specific UI element or text on screen"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type="string",
                description="What to find (e.g., 'submit button', 'login form', 'error message')",
                required=True,
            ),
            SkillParameter(
                name="monitor",
                type="number",
                description="Monitor index",
                required=False,
                default=1,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "vision"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Find the submit button",
            "Where is the login form?",
            "Find error message on screen",
        ]
    
    def execute(self, query: str, monitor: int = 1) -> str:
        try:
            from core.vision.screen import get_screen_understanding
            vision = get_screen_understanding()
            result = vision.find_element_on_screen(query, monitor)
            return f"Search Result ({result.model_used}):\n{result.description}"
        except Exception as e:
            return f"Find on screen failed: {e}"


class VisionReadRegionSkill(BaseSkill):
    """Read specific screen region."""
    
    @property
    def name(self) -> str:
        return "vision.read_region"
    
    @property
    def description(self) -> str:
        return "Read text from specific screen region using vision"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="x",
                type="number",
                description="Left coordinate",
                required=True,
            ),
            SkillParameter(
                name="y",
                type="number",
                description="Top coordinate",
                required=True,
            ),
            SkillParameter(
                name="width",
                type="number",
                description="Region width",
                required=True,
            ),
            SkillParameter(
                name="height",
                type="number",
                description="Region height",
                required=True,
            ),
            SkillParameter(
                name="prompt",
                type="string",
                description="Custom prompt",
                required=False,
                default="Extract all text from this region",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "vision"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Read region 100 100 500 300",
            "Extract text from area 0 0 800 600",
        ]
    
    def execute(self, x: int, y: int, width: int, height: int, prompt: str = "") -> str:
        try:
            from core.vision.screen import get_screen_understanding
            from core.system.screen import ScreenRegion
            vision = get_screen_understanding()
            region = ScreenRegion(left=x, top=y, width=width, height=height)
            result = vision.read_screen_region(region, prompt or "Extract all text from this region")
            return f"Region Text ({result.model_used}):\n{result.description}"
        except Exception as e:
            return f"Read region failed: {e}"


class VisionAnalyzeWindowSkill(BaseSkill):
    """Analyze specific window."""
    
    @property
    def name(self) -> str:
        return "vision.analyze_window"
    
    @property
    def description(self) -> str:
        return "Analyze specific window by title"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="window_title",
                type="string",
                description="Window title to analyze",
                required=True,
            ),
            SkillParameter(
                name="prompt",
                type="string",
                description="Custom prompt",
                required=False,
                default="Describe this window",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "vision"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Analyze Chrome window",
            "Describe VS Code window",
        ]
    
    def execute(self, window_title: str, prompt: str = "") -> str:
        try:
            from core.vision.screen import get_screen_understanding
            vision = get_screen_understanding()
            result = vision.analyze_window(window_title, prompt or "Describe this window")
            return f"Window Analysis ({result.model_used}):\n{result.description}"
        except Exception as e:
            return f"Window analysis failed: {e}"


class CameraIdentifyUserSkill(BaseSkill):
    """Identify user via camera face recognition."""
    
    @property
    def name(self) -> str:
        return "camera.identify_user"
    
    @property
    def description(self) -> str:
        return "Identify person in front of camera using face recognition"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="camera_index",
                type="number",
                description="Camera index",
                required=False,
                default=0,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "camera"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Who is in front of the camera?",
            "Identify user",
        ]
    
    def execute(self, camera_index: int = 0) -> str:
        try:
            from core.vision.camera import get_camera_manager
            from core.vision.face import get_face_recognizer
            
            camera = get_camera_manager(camera_index)
            if not camera.open():
                return "Failed to open camera"
            
            frame = camera.capture_frame()
            camera.close()
            
            if not frame:
                return "Failed to capture frame"
            
            recognizer = get_face_recognizer()
            faces = recognizer.identify_face(frame)
            
            if not faces:
                return "No faces detected"
            
            results = []
            for face in faces:
                name = face.name or "Unknown"
                conf = face.confidence
                results.append(f"{name} (confidence: {conf:.2f})")
            
            return f"Identified: {', '.join(results)}"
        except Exception as e:
            return f"Camera identification failed: {e}"


class CameraEnrollFaceSkill(BaseSkill):
    """Enroll new face for recognition."""
    
    @property
    def name(self) -> str:
        return "camera.enroll_face"
    
    @property
    def description(self) -> str:
        return "Enroll a new face for future recognition"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="name",
                type="string",
                description="Name for the face",
                required=True,
            ),
            SkillParameter(
                name="camera_index",
                type="number",
                description="Camera index",
                required=False,
                default=0,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "camera"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Enroll my face as Ansh",
            "Learn face for John",
        ]
    
    def execute(self, name: str, camera_index: int = 0) -> str:
        try:
            from core.vision.camera import get_camera_manager
            from core.vision.face import get_face_recognizer
            
            camera = get_camera_manager(camera_index)
            if not camera.open():
                return "Failed to open camera"
            
            frame = camera.capture_frame()
            camera.close()
            
            if not frame:
                return "Failed to capture frame"
            
            recognizer = get_face_recognizer()
            face_id = recognizer.enroll_face(frame, name)
            
            if face_id:
                return f"Enrolled {name} with ID: {face_id}"
            return "Enrollment failed - no face detected"
        except Exception as e:
            return f"Face enrollment failed: {e}"


class CameraListFacesSkill(BaseSkill):
    """List enrolled faces."""
    
    @property
    def name(self) -> str:
        return "camera.list_faces"
    
    @property
    def description(self) -> str:
        return "List all enrolled faces"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "camera"
    
    @property
    def examples(self) -> List[str]:
        return [
            "List enrolled faces",
            "Show known faces",
        ]
    
    def execute(self) -> str:
        try:
            from core.vision.face import get_face_recognizer
            recognizer = get_face_recognizer()
            faces = recognizer.get_known_faces()
            
            if not faces:
                return "No faces enrolled"
            
            lines = [f"Enrolled faces ({len(faces)}):"]
            for face in faces:
                lines.append(f"  {face.name} (ID: {face.id}) - {face.created_at[:10]}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"List faces failed: {e}"


class ObjectDetectSkill(BaseSkill):
    """Detect objects on screen or camera."""
    
    @property
    def name(self) -> str:
        return "vision.detect_objects"
    
    @property
    def description(self) -> str:
        return "Detect objects in image using YOLO"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="source",
                type="string",
                description="Source: 'screen' or 'camera'",
                required=True,
                enum=["screen", "camera"],
            ),
            SkillParameter(
                name="classes",
                type="string",
                description="Comma-separated class names to detect",
                required=False,
                default="",
            ),
            SkillParameter(
                name="camera_index",
                type="number",
                description="Camera index if source is camera",
                required=False,
                default=0,
            ),
            SkillParameter(
                name="monitor",
                type="number",
                description="Monitor index if source is screen",
                required=False,
                default=1,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "vision"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Detect objects on screen",
            "Find person on camera",
            "Detect buttons on screen",
        ]
    
    def execute(self, source: str, classes: str = "", camera_index: int = 0, monitor: int = 1) -> str:
        try:
            if source == "camera":
                from core.vision.camera import get_camera_manager
                camera = get_camera_manager(camera_index)
                if not camera.open():
                    return "Failed to open camera"
                image = camera.capture_frame()
                camera.close()
            elif source == "screen":
                from core.system.screen import get_screen_analyzer
                analyzer = get_screen_analyzer()
                image = analyzer.capture_monitor(monitor)
            else:
                return f"Unknown source: {source}"
            
            if not image:
                return "Failed to capture image"
            
            from core.vision.objects import get_object_detector
            detector = get_object_detector()
            
            class_list = [c.strip() for c in classes.split(",")] if classes else None
            objects = detector.detect(image, classes=class_list)
            
            if not objects:
                return "No objects detected"
            
            lines = [f"Detected {len(objects)} objects:"]
            for obj in objects:
                lines.append(f"  {obj.class_name} ({obj.confidence:.2f}) at {obj.bbox}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Object detection failed: {e}"


class ScreenFindElementSkill(BaseSkill):
    """Find UI elements on screen (buttons, inputs, etc.)."""
    
    @property
    def name(self) -> str:
        return "vision.find_ui_element"
    
    @property
    def description(self) -> str:
        return "Find clickable UI elements on screen"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="element_type",
                type="string",
                description="Type: 'button', 'text_field', 'all'",
                required=False,
                default="all",
                enum=["button", "text_field", "all"],
            ),
            SkillParameter(
                name="monitor",
                type="number",
                description="Monitor index",
                required=False,
                default=1,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "vision"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Find buttons on screen",
            "Find text fields",
            "Find clickable elements",
        ]
    
    def execute(self, element_type: str = "all", monitor: int = 1) -> str:
        try:
            from core.system.screen import get_screen_analyzer
            from core.vision.objects import get_screen_element_detector
            
            analyzer = get_screen_analyzer()
            image = analyzer.capture_monitor(monitor)
            
            detector = get_screen_element_detector()
            elements = detector.find_clickable_elements(image)
            
            if element_type != "all":
                elements = [e for e in elements if e["type"] == element_type]
            
            if not elements:
                return f"No {element_type} elements found"
            
            lines = [f"Found {len(elements)} {element_type} elements:"]
            for el in elements:
                center = el["center"]
                lines.append(f"  {el['type']} at ({center[0]}, {center[1]}) bbox: {el['bbox']}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"UI element detection failed: {e}"


class LiveCameraVisionSkill(BaseSkill):
    """Start live camera vision stream (like Gemini Live)."""

    @property
    def name(self) -> str:
        return "vision.live_camera"

    @property
    def description(self) -> str:
        return "Start continuous camera analysis with vision LLM (Gemini Live style)"

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'start', 'stop', 'get_latest'",
                required=True,
                enum=["start", "stop", "get_latest"],
            ),
            SkillParameter(
                name="camera_index",
                type="number",
                description="Camera index",
                required=False,
                default=0,
            ),
            SkillParameter(
                name="fps",
                type="number",
                description="Frames per second",
                required=False,
                default=1.0,
            ),
            SkillParameter(
                name="prompt",
                type="string",
                description="Analysis prompt",
                required=False,
                default="Describe what you see in detail. Focus on people, objects, text, and activity.",
            ),
        ]

    @property
    def category(self) -> str:
        return "vision"

    @property
    def examples(self) -> List[str]:
        return [
            "Start live camera vision",
            "Stop live camera vision",
            "Get latest camera analysis",
        ]

    def execute(self, action: str, camera_index: int = 0, fps: float = 1.0, prompt: str = "") -> str:
        try:
            from core.vision.live import get_live_camera_stream
            
            stream = get_live_camera_stream(camera_index=camera_index, fps=fps, prompt=prompt)
            
            if action == "start":
                stream.start()
                return f"Live camera vision started (camera {camera_index}, {fps} FPS)"
            elif action == "stop":
                stream.stop()
                return "Live camera vision stopped"
            elif action == "get_latest":
                result = stream.get_latest(timeout=5.0)
                if result:
                    return f"Frame {result.frame_number}: {result.description[:200]}..."
                return "No frame available yet"
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Live camera vision failed: {e}"


class LiveScreenVisionSkill(BaseSkill):
    """Start live screen vision stream."""

    @property
    def name(self) -> str:
        return "vision.live_screen"

    @property
    def description(self) -> str:
        return "Start continuous screen analysis with vision LLM"

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'start', 'stop', 'get_latest'",
                required=True,
                enum=["start", "stop", "get_latest"],
            ),
            SkillParameter(
                name="monitor",
                type="number",
                description="Monitor index",
                required=False,
                default=1,
            ),
            SkillParameter(
                name="fps",
                type="number",
                description="Frames per second",
                required=False,
                default=1.0,
            ),
            SkillParameter(
                name="prompt",
                type="string",
                description="Analysis prompt",
                required=False,
                default="Describe what you see on screen in detail. Identify apps, code, text, UI elements.",
            ),
        ]

    @property
    def category(self) -> str:
        return "vision"

    @property
    def examples(self) -> List[str]:
        return [
            "Start live screen vision",
            "Stop live screen vision",
            "Get latest screen analysis",
        ]

    def execute(self, action: str, monitor: int = 1, fps: float = 1.0, prompt: str = "") -> str:
        try:
            from core.vision.live import get_live_screen_stream
            
            stream = get_live_screen_stream(monitor=monitor, fps=fps, prompt=prompt)
            
            if action == "start":
                stream.start()
                return f"Live screen vision started (monitor {monitor}, {fps} FPS)"
            elif action == "stop":
                stream.stop()
                return "Live screen vision stopped"
            elif action == "get_latest":
                result = stream.get_latest(timeout=5.0)
                if result:
                    return f"Frame {result.frame_number}: {result.description[:200]}..."
                return "No frame available yet"
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Live screen vision failed: {e}"


class ScreenShareVisionSkill(BaseSkill):
    """Screen share with vision analysis (like video call screen share + AI)."""

    @property
    def name(self) -> str:
        return "vision.screen_share"

    @property
    def description(self) -> str:
        return "Screen share with continuous vision analysis - like sharing screen in call with AI"

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'start', 'stop', 'get_latest'",
                required=True,
                enum=["start", "stop", "get_latest"],
            ),
            SkillParameter(
                name="monitor",
                type="number",
                description="Monitor index",
                required=False,
                default=1,
            ),
            SkillParameter(
                name="fps",
                type="number",
                description="Frames per second (higher = more responsive)",
                required=False,
                default=2.0,
            ),
        ]

    @property
    def category(self) -> str:
        return "vision"

    @property
    def examples(self) -> List[str]:
        return [
            "Start screen share vision",
            "Stop screen share vision",
            "Analyze shared screen",
        ]

    def execute(self, action: str, monitor: int = 1, fps: float = 2.0) -> str:
        try:
            from core.vision.live import get_screen_share_stream
            
            stream = get_screen_share_stream(monitor=monitor, fps=fps)
            
            if action == "start":
                stream.start()
                return f"Screen share vision started (monitor {monitor}, {fps} FPS)"
            elif action == "stop":
                stream.stop()
                return "Screen share vision stopped"
            elif action == "get_latest":
                result = stream.get_latest(timeout=5.0)
                if result:
                    return f"Frame {result.frame_number}: {result.description[:300]}..."
                return "No frame available yet"
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Screen share vision failed: {e}"


def register_vision_skills(registry) -> None:
    """Register all vision skills."""
    skills = [
        VisionDescribeScreenSkill(),
        VisionFindOnScreenSkill(),
        VisionReadRegionSkill(),
        VisionAnalyzeWindowSkill(),
        CameraIdentifyUserSkill(),
        CameraEnrollFaceSkill(),
        CameraListFacesSkill(),
        ObjectDetectSkill(),
        ScreenFindElementSkill(),
        LiveCameraVisionSkill(),
        LiveScreenVisionSkill(),
        ScreenShareVisionSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())