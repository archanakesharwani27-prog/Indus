"""
ScreenUnderstanding - Screen analysis using vision LLMs (Gemini, OpenAI, NVIDIA, Local)
"""

import os
import io
import base64
from typing import Optional, Literal
from dataclasses import dataclass
from PIL import Image

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class ScreenAnalysisResult:
    """Result of screen analysis."""
    description: str
    model_used: str
    confidence: float = 1.0


class ScreenUnderstanding:
    """Analyze screen content using vision LLMs."""
    
    def __init__(
        self,
        provider: Literal["gemini", "openai", "nvidia", "auto"] = "auto",
        gemini_model: str = "gemini-1.5-flash",
        openai_model: str = "gpt-4o-mini",
        nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    ):
        self.provider = provider
        self.gemini_model = gemini_model
        self.openai_model = openai_model
        self.nvidia_model = nvidia_model
        
        self._gemini_client = None
        self._openai_client = None
        self._nvidia_client = None
        
        self._init_clients()
    
    def _init_clients(self):
        """Initialize available vision clients."""
        # Gemini Vision
        if GEMINI_AVAILABLE:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    self._gemini_client = genai.GenerativeModel(self.gemini_model)
                except Exception:
                    pass
        
        # OpenAI Vision (GPT-4V)
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    self._openai_client = OpenAI(api_key=api_key)
                except Exception:
                    pass
        
        # NVIDIA Vision models (multimodal)
        # Note: Nemotron is text-only. Use these vision models instead:
        # - meta/llama-3.2-11b-vision-instruct (fast)
        # - meta/llama-3.2-90b-vision-instruct (capable)
        # - nvidia/nemotron-nano-12b-v2-vl (NVIDIA's VL model)
        api_key = os.getenv("NVIDIA_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                self._nvidia_client = OpenAI(
                    api_key=api_key,
                    base_url="https://integrate.api.nvidia.com/v1"
                )
                # Default to Llama 3.2 11B Vision (fast, accurate)
                self.nvidia_model = "meta/llama-3.2-11b-vision-instruct"
            except Exception:
                pass
        
        # Auto-select provider
        if self.provider == "auto":
            # Prefer NVIDIA when NVIDIA_API_KEY is set (user preference)
            if self._nvidia_client:
                self.provider = "nvidia"
            elif self._gemini_client:
                self.provider = "gemini"
            elif self._openai_client:
                self.provider = "openai"
            else:
                self.provider = "none"
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    
    def analyze_full_screen(
        self, 
        prompt: str = "Describe what's on this screen in detail",
        monitor: int = 1
    ) -> ScreenAnalysisResult:
        """Analyze full screen with vision LLM."""
        from core.system.screen import get_screen_analyzer
        analyzer = get_screen_analyzer("tesseract")
        image = analyzer.capture_monitor(monitor)
        
        return self.analyze_image(image, prompt)
    
    def analyze_image(self, image: Image.Image, prompt: str) -> ScreenAnalysisResult:
        """Analyze image with vision LLM."""
        
        if self.provider == "gemini" and self._gemini_client:
            return self._analyze_gemini(image, prompt)
        elif self.provider == "openai" and self._openai_client:
            return self._analyze_openai(image, prompt)
        elif self.provider == "nvidia" and self._nvidia_client:
            return self._analyze_nvidia(image, prompt)
        else:
            return ScreenAnalysisResult(
                description="No vision provider configured. Set GEMINI_API_KEY, OPENAI_API_KEY, or NVIDIA_API_KEY.",
                model_used="none",
                confidence=0.0
            )
    
    def _analyze_gemini(self, image: Image.Image, prompt: str) -> ScreenAnalysisResult:
        """Analyze with Gemini Vision."""
        try:
            img_bytes = self._image_to_bytes(image)
            response = self._gemini_client.generate_content([
                prompt,
                {"mime_type": "image/png", "data": img_bytes}
            ])
            return ScreenAnalysisResult(
                description=response.text,
                model_used=f"gemini-{self.gemini_model}",
                confidence=0.9
            )
        except Exception as e:
            return ScreenAnalysisResult(
                description=f"Gemini Vision error: {e}",
                model_used="gemini",
                confidence=0.0
            )
    
    def _analyze_openai(self, image: Image.Image, prompt: str) -> ScreenAnalysisResult:
        """Analyze with OpenAI GPT-4V."""
        try:
            b64_image = self._image_to_base64(image)
            response = self._openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                    ]}
                ],
                max_tokens=1000
            )
            return ScreenAnalysisResult(
                description=response.choices[0].message.content,
                model_used=f"openai-{self.openai_model}",
                confidence=0.9
            )
        except Exception as e:
            return ScreenAnalysisResult(
                description=f"OpenAI Vision error: {e}",
                model_used="openai",
                confidence=0.0
            )
    
    def _analyze_nvidia(self, image: Image.Image, prompt: str) -> ScreenAnalysisResult:
        """Analyze with NVIDIA API (if vision model available)."""
        # Note: NVIDIA Nemotron is text-only. 
        # For vision, would need a vision-capable model on NVIDIA API.
        # Currently falling back to text description.
        try:
            b64_image = self._image_to_base64(image)
            response = self._nvidia_client.chat.completions.create(
                model=self.nvidia_model,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": f"{prompt}\n\n[Image provided but {self.nvidia_model} is text-only. Describe what you would expect to see.]"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                    ]}
                ],
                max_tokens=1000
            )
            return ScreenAnalysisResult(
                description=response.choices[0].message.content + "\n\n[Note: NVIDIA Nemotron is text-only. For true vision analysis, use Gemini or OpenAI.]",
                model_used=f"nvidia-{self.nvidia_model}",
                confidence=0.5
            )
        except Exception as e:
            return ScreenAnalysisResult(
                description=f"NVIDIA Vision error: {e}",
                model_used="nvidia",
                confidence=0.0
            )
    
    def find_element_on_screen(self, query: str, monitor: int = 1) -> ScreenAnalysisResult:
        """Find specific element on screen."""
        prompt = f"Find and describe the location of: {query}. Return coordinates if possible."
        return self.analyze_full_screen(prompt, monitor)
    
    def read_screen_region(self, region, prompt: str = "Extract all text from this region") -> ScreenAnalysisResult:
        """Read specific screen region."""
        from core.system.screen import get_screen_analyzer
        analyzer = get_screen_analyzer("tesseract")
        image = analyzer.capture_region(region)
        return self.analyze_image(image, prompt)
    
    def analyze_window(self, window_title: str, prompt: str = "Describe this window") -> ScreenAnalysisResult:
        """Analyze specific window."""
        from core.system.screen import get_screen_analyzer
        analyzer = get_screen_analyzer("tesseract")
        image = analyzer.capture_window(window_title)
        if not image:
            return ScreenAnalysisResult(
                description=f"Window not found: {window_title}",
                model_used="none",
                confidence=0.0
            )
        return self.analyze_image(image, prompt)


# Global instance
_screen_understanding: Optional[ScreenUnderstanding] = None


def get_screen_understanding(
    provider: Literal["gemini", "openai", "nvidia", "auto"] = "auto"
) -> ScreenUnderstanding:
    global _screen_understanding
    if _screen_understanding is None:
        _screen_understanding = ScreenUnderstanding(provider=provider)
    return _screen_understanding