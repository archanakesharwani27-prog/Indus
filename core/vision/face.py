"""
FaceRecognizer - Face detection, enrollment, and identification using InsightFace
"""

import os
import json
import pickle
import cv2
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from PIL import Image
import io


try:
    import insightface
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False


@dataclass
class FaceEncoding:
    """Face encoding with metadata."""
    id: str
    name: str
    encoding: List[float]
    created_at: str
    metadata: Dict[str, Any]


@dataclass
class DetectedFace:
    """Detected face in image."""
    location: Tuple[int, int, int, int]  # top, right, bottom, left
    encoding: Optional[List[float]] = None
    name: Optional[str] = None
    confidence: float = 0.0
    landmarks: Optional[Dict[str, Tuple[int, int]]] = None


class FaceRecognizer:
    """Face detection, enrollment, and recognition using InsightFace."""
    
    def __init__(
        self,
        data_dir: str = "face_data",
        tolerance: float = 0.6,
        det_size: Tuple[int, int] = (640, 640)
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.tolerance = tolerance
        self.det_size = det_size
        
        self._known_faces: Dict[str, FaceEncoding] = {}
        self._encodings_file = self.data_dir / "encodings.pkl"
        self._metadata_file = self.data_dir / "metadata.json"
        
        self._load_known_faces()
        
        # Initialize InsightFace
        self._insightface_app = None
        if INSIGHTFACE_AVAILABLE:
            try:
                self._insightface_app = insightface.app.FaceAnalysis()
                self._insightface_app.prepare(ctx_id=0, det_size=det_size)
            except Exception as e:
                print(f"InsightFace init failed: {e}")
                self._insightface_app = None
    
    def _load_known_faces(self):
        """Load known face encodings from disk."""
        if self._encodings_file.exists():
            try:
                with open(self._encodings_file, 'rb') as f:
                    self._known_faces = pickle.load(f)
            except Exception:
                self._known_faces = {}
        
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    metadata = json.load(f)
                    for face_id, meta in metadata.items():
                        if face_id in self._known_faces:
                            self._known_faces[face_id].metadata = meta
            except Exception:
                pass
    
    def _save_known_faces(self):
        """Save known face encodings to disk."""
        try:
            with open(self._encodings_file, 'wb') as f:
                pickle.dump(self._known_faces, f)
        except Exception:
            pass
        
        try:
            metadata = {fid: face.metadata for fid, face in self._known_faces.items()}
            with open(self._metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            pass
    
    def _pil_to_cv2(self, image: Image.Image) -> np.ndarray:
        """Convert PIL image to OpenCV format."""
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    def _cv2_to_pil(self, image: np.ndarray) -> Image.Image:
        """Convert OpenCV image to PIL format."""
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    def _cosine_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine distance between two vectors."""
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        if a_norm == 0 or b_norm == 0:
            return 1.0
        return 1.0 - np.dot(a, b) / (a_norm * b_norm)
    
    def detect_faces(
        self,
        image: Image.Image,
        return_encodings: bool = True
    ) -> List[DetectedFace]:
        """Detect faces in image using InsightFace."""
        if not self._insightface_app:
            return []
        
        cv_image = self._pil_to_cv2(image)
        faces = self._insightface_app.get(cv_image)
        
        detected = []
        for face in faces:
            bbox = face.bbox.astype(int)
            location = (bbox[1], bbox[2], bbox[3], bbox[0])  # top, right, bottom, left
            encoding = face.embedding.tolist() if face.embedding is not None else None
            
            detected.append(DetectedFace(
                location=location,
                encoding=encoding,
                confidence=face.det_score,
                landmarks={k: (int(v[0]), int(v[1])) for k, v in face.landmark_2d_106.items()} if hasattr(face, 'landmark_2d_106') else None
            ))
        
        return detected
    
    def enroll_face(
        self,
        image: Image.Image,
        name: str,
        face_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Enroll a new face."""
        faces = self.detect_faces(image)
        
        if not faces:
            return None
        
        # Use the most confident face
        best_face = max(faces, key=lambda f: f.confidence)
        
        if not best_face.encoding:
            return None
        
        import uuid
        from datetime import datetime
        
        fid = face_id or str(uuid.uuid4())[:8]
        
        encoding = FaceEncoding(
            id=fid,
            name=name,
            encoding=best_face.encoding,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self._known_faces[fid] = encoding
        self._save_known_faces()
        
        return fid
    
    def identify_face(
        self,
        image: Image.Image,
        return_all: bool = False
    ) -> List[DetectedFace]:
        """Identify faces in image against known faces."""
        faces = self.detect_faces(image)
        
        if not faces or not self._known_faces:
            return faces
        
        known_encodings = [np.array(face.encoding) for face in self._known_faces.values()]
        known_ids = list(self._known_faces.keys())
        
        for face in faces:
            if not face.encoding:
                continue
            
            face_encoding = np.array(face.encoding)
            
            # Compare with known faces using cosine distance
            best_distance = 1.0
            best_match_idx = -1
            
            for i, known_enc in enumerate(known_encodings):
                dist = self._cosine_distance(face_encoding, known_enc)
                if dist < best_distance:
                    best_distance = dist
                    best_match_idx = i
            
            if best_match_idx >= 0 and best_distance <= self.tolerance:
                face_id = known_ids[best_match_idx]
                known_face = self._known_faces[face_id]
                face.name = known_face.name
                face.confidence = float(1 - best_distance)
            else:
                face.name = "Unknown"
                face.confidence = float(1 - best_distance)
        
        return faces
    
    def get_known_faces(self) -> List[FaceEncoding]:
        """Get all known faces."""
        return list(self._known_faces.values())
    
    def remove_face(self, face_id: str) -> bool:
        """Remove enrolled face."""
        if face_id in self._known_faces:
            del self._known_faces[face_id]
            self._save_known_faces()
            return True
        return False
    
    def update_face_metadata(self, face_id: str, metadata: Dict[str, Any]) -> bool:
        """Update face metadata."""
        if face_id in self._known_faces:
            self._known_faces[face_id].metadata.update(metadata)
            self._save_known_faces()
            return True
        return False
    
    def draw_faces(
        self,
        image: Image.Image,
        faces: List[DetectedFace],
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> Image.Image:
        """Draw face boxes and labels on image."""
        cv_image = self._pil_to_cv2(image)
        
        for face in faces:
            top, right, bottom, left = face.location
            
            # Draw rectangle
            cv2.rectangle(cv_image, (left, top), (right, bottom), color, 2)
            
            # Draw label
            label = face.name or "Unknown"
            if face.confidence:
                label += f" ({face.confidence:.2f})"
            
            cv2.putText(
                cv_image, label, (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
            )
        
        return self._cv2_to_pil(cv_image)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get recognizer statistics."""
        return {
            "total_enrolled": len(self._known_faces),
            "tolerance": self.tolerance,
            "insightface_available": INSIGHTFACE_AVAILABLE,
            "det_size": self.det_size
        }


# Global instance
_face_recognizer: Optional[FaceRecognizer] = None


def get_face_recognizer(data_dir: str = "face_data", **kwargs) -> FaceRecognizer:
    global _face_recognizer
    if _face_recognizer is None:
        _face_recognizer = FaceRecognizer(data_dir, **kwargs)
    return _face_recognizer