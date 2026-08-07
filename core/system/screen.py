"""
ScreenAnalyzer - Screen capture, OCR, and analysis
"""

import mss
import mss.tools
from PIL import Image
import io
import base64
import tempfile
import os
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ScreenRegion:
    """Screen region definition."""
    left: int
    top: int
    width: int
    height: int
    
    @property
    def right(self) -> int:
        return self.left + self.width
    
    @property
    def bottom(self) -> int:
        return self.top + self.height
    
    def to_mss_dict(self) -> Dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


class ScreenAnalyzer:
    """Capture and analyze screen content."""
    
    def __init__(self, ocr_provider: str = "tesseract"):
        """
        Initialize screen analyzer.
        
        Args:
            ocr_provider: "tesseract" (local), "gemini_vision" (cloud), or "nvidia_vision" (cloud)
        """
        self.ocr_provider = ocr_provider
        self._sct = mss.mss()
        self._gemini_client = None
        self._nvidia_client = None
        self._nvidia_model = "meta/llama-3.2-11b-vision-instruct"
        
        if ocr_provider == "gemini_vision":
            self._init_gemini()
        elif ocr_provider == "nvidia_vision":
            self._init_nvidia()
    
    def _init_gemini(self) -> None:
        """Initialize Gemini Vision client."""
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self._gemini_client = genai.GenerativeModel("gemini-2.0-flash")
        except ImportError:
            pass
    
    def _init_nvidia(self) -> None:
        """Initialize NVIDIA Vision client."""
        try:
            from openai import OpenAI
            api_key = os.getenv("NVIDIA_API_KEY")
            if api_key:
                self._nvidia_client = OpenAI(
                    api_key=api_key,
                    base_url="https://integrate.api.nvidia.com/v1"
                )
        except ImportError:
            pass
    
    def capture_full_screen(self) -> Image.Image:
        """Capture entire screen."""
        monitors = self._sct.monitors
        # Monitor 0 is all monitors combined
        screenshot = self._sct.grab(monitors[0])
        return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    
    def capture_monitor(self, monitor_index: int = 1) -> Image.Image:
        """Capture specific monitor (1 = primary)."""
        monitors = self._sct.monitors
        if monitor_index < len(monitors):
            screenshot = self._sct.grab(monitors[monitor_index])
            return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return self.capture_full_screen()
    
    def capture_region(self, region: ScreenRegion) -> Image.Image:
        """Capture specific screen region."""
        screenshot = self._sct.grab(region.to_mss_dict())
        return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    
    def capture_window(self, window_title: str) -> Optional[Image.Image]:
        """Capture specific window by title."""
        try:
            import win32gui
            hwnd = win32gui.FindWindow(None, window_title)
            if not hwnd:
                # Try partial match
                def enum_windows(h, _):
                    if win32gui.IsWindowVisible(h):
                        title = win32gui.GetWindowText(h)
                        if window_title.lower() in title.lower():
                            return h
                    return None
                win32gui.EnumWindows(lambda h, l: l.append(h) if enum_windows(h, l) else True, [])
            
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                region = ScreenRegion(
                    left=rect[0], top=rect[1],
                    width=rect[2] - rect[0],
                    height=rect[3] - rect[1]
                )
                return self.capture_region(region)
        except ImportError:
            pass
        return None
    
    def save_screenshot(self, image: Image.Image, path: Optional[str] = None) -> str:
        """Save screenshot to file."""
        if path is None:
            path = tempfile.mktemp(suffix=".png")
        image.save(path)
        return path
    
    def ocr_tesseract(self, image: Image.Image, lang: str = "eng") -> str:
        """OCR using Tesseract (local)."""
        try:
            import pytesseract
            return pytesseract.image_to_string(image, lang=lang)
        except ImportError:
            return "Tesseract not installed (pip install pytesseract + tesseract binary)"
        except Exception as e:
            return f"OCR error: {e}"
    
    def ocr_gemini_vision(self, image: Image.Image, prompt: str = "Extract all text from this image") -> str:
        """OCR using Gemini Vision (cloud)."""
        if not self._gemini_client:
            return "Gemini Vision not configured (need GEMINI_API_KEY)"
        
        try:
            # Convert to bytes
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            
            response = self._gemini_client.generate_content([
                prompt,
                {"mime_type": "image/png", "data": img_bytes.read()}
            ])
            return response.text
        except Exception as e:
            return f"Gemini Vision error: {e}"
    
    def ocr_nvidia_vision(self, image: Image.Image, prompt: str = "Extract all text from this image") -> str:
        """OCR using NVIDIA Vision (cloud)."""
        if not self._nvidia_client:
            return "NVIDIA Vision not configured (need NVIDIA_API_KEY)"
        
        try:
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            b64_image = base64.b64encode(buffer.getvalue()).decode()
            
            response = self._nvidia_client.chat.completions.create(
                model=self._nvidia_model,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                    ]}
                ],
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"NVIDIA Vision error: {e}"
    
    def ocr(self, image: Image.Image, lang: str = "eng") -> str:
        """Perform OCR using configured provider."""
        if self.ocr_provider == "gemini_vision":
            return self.ocr_gemini_vision(image)
        elif self.ocr_provider == "nvidia_vision":
            return self.ocr_nvidia_vision(image)
        return self.ocr_tesseract(image, lang)
    
    def analyze_screen(self, prompt: str = "Describe what's on the screen") -> str:
        """Analyze full screen with vision LLM."""
        if self.ocr_provider == "gemini_vision" and self._gemini_client:
            try:
                image = self.capture_full_screen()
                img_bytes = io.BytesIO()
                image.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                
                response = self._gemini_client.generate_content([
                    prompt,
                    {"mime_type": "image/png", "data": img_bytes.read()}
                ])
                return response.text
            except Exception as e:
                return f"Screen analysis error: {e}"
        elif self.ocr_provider == "nvidia_vision" and self._nvidia_client:
            try:
                image = self.capture_full_screen()
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                b64_image = base64.b64encode(buffer.getvalue()).decode()
                
                response = self._nvidia_client.chat.completions.create(
                    model=self._nvidia_model,
                    messages=[
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                        ]}
                    ],
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"NVIDIA Vision analysis error: {e}"
        return "No vision provider configured"
    
    def find_text_on_screen(self, text: str) -> List[ScreenRegion]:
        """Find text on screen using OCR (returns regions where text found)."""
        # This would require more sophisticated OCR with position data
        # For now, return empty - would need pytesseract with output_type=dict
        return []
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get primary monitor size."""
        monitors = self._sct.monitors
        if len(monitors) > 1:
            return monitors[1]["width"], monitors[1]["height"]
        return monitors[0]["width"], monitors[0]["height"]


# Global instance
_screen_analyzer = None


def get_screen_analyzer(ocr_provider: str = "tesseract") -> ScreenAnalyzer:
    global _screen_analyzer
    if _screen_analyzer is None:
        _screen_analyzer = ScreenAnalyzer(ocr_provider)
    return _screen_analyzer