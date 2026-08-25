import json
import sys
import time
import base64
import logging
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openrouter_client")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR     = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"

def _load_api_keys() -> tuple[str, str]:
    or_key = ""
    nv_key = ""
    try:
        from core.secure_storage import load_secure_json
        data = load_secure_json(API_KEY_PATH)
        or_key = data.get("openrouter_api_key", "").strip()
        nv_key = data.get("nvidia_api_key", "").strip()
    except Exception as e:
        logger.warning(f"[API Keys] Load warning: {e}")
    return or_key, nv_key


def _load_groq_key() -> str:
    try:
        from core.secure_storage import load_secure_json
        data = load_secure_json(API_KEY_PATH)
        return data.get("groq_api_key", "").strip()
    except Exception:
        return ""


TEXT_MODELS: list[str] = [
    # Verified free OpenRouter models (2025-08)
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]

VISION_MODELS: list[str] = [
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "meta-llama/llama-3.2-90b-vision-instruct:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
]

API_URL               = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MAX_TOKENS    = 4096
DEFAULT_TEMPERATURE   = 0.7
REQUEST_TIMEOUT       = 60   # seconds per request
MAX_RETRIES_PER_MODEL = 2    # attempts before moving to next model
RETRY_DELAY           = 2    # seconds between retries
RATE_LIMIT_COOLDOWN   = 60   # seconds before retrying a rate-limited model
_rate_limited: dict[str, float] = {}

# -- Groq LPU (ultra-fast) ------------------------------------------------------
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_FAST_MODELS = ["llama-3.3-70b-versatile", "llama3-8b-8192", "gemma2-9b-it"]

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODELS: list[str] = [
    "meta/llama-3.3-70b-instruct",
    "mistralai/mixtral-8x7b-instruct-v0.1",
]

class OpenRouterClient:

    def __init__(self) -> None:
        self.api_key, self.nvidia_api_key = _load_api_keys()
        self.groq_key = _load_groq_key()
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/indus",
            "X-Title":       "INDUS",
        }

    def reload_keys(self):
        self.api_key, self.nvidia_api_key = _load_api_keys()
        self.groq_key = _load_groq_key()
        self._headers["Authorization"] = f"Bearer {self.api_key}"

    def _call_nvidia(
        self,
        messages: list[dict],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        if not self.nvidia_api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type":  "application/json",
        }

        for model in NVIDIA_MODELS:
            payload: dict = {
                "model":       model,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
            }
            if response_format:
                payload["response_format"] = response_format

            try:
                logger.info(f"[NVIDIA API] Trying NVIDIA Nim model: {model}")
                resp = requests.post(
                    NVIDIA_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                    )
                    if content:
                        logger.info(f"[NVIDIA API] [OK] Success via {model}")
                        return content.strip()
                else:
                    logger.warning(
                        f"[NVIDIA API] {model} -> HTTP {resp.status_code}: {resp.text[:120]}"
                    )
            except Exception as e:
                logger.warning(f"[NVIDIA API] {model} error: {e}")

        return None


    def _is_rate_limited(self, model: str) -> bool:
        ts = _rate_limited.get(model)
        if ts is None:
            return False
        if time.time() - ts > RATE_LIMIT_COOLDOWN:
            del _rate_limited[model]
            return False
        return True

    def _mark_rate_limited(self, model: str) -> None:
        _rate_limited[model] = time.time()
        logger.warning(
            f"[OpenRouter] Rate limited: {model} -- "
            f"cooling down for {RATE_LIMIT_COOLDOWN}s"
        )

    def _call_groq(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> Optional[str]:
        """Groq LPU -- ultra-fast sub-second inference for intent/JSON tasks."""
        if not self.groq_key:
            return None
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }
        for model in GROQ_FAST_MODELS:
            try:
                resp = requests.post(
                    GROQ_API_URL,
                    headers=headers,
                    json={"model": model, "messages": messages,
                          "max_tokens": max_tokens, "temperature": temperature},
                    timeout=8,
                )
                if resp.status_code == 200:
                    content = (resp.json().get("choices", [{}])[0]
                               .get("message", {}).get("content", ""))
                    if content:
                        logger.info(f"[Groq] Success via {model}")
                        return content.strip()
            except Exception as e:
                logger.warning(f"[Groq] {model} error: {e}")
        return None

    def _call(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        payload: dict = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                resp = requests.post(
                    API_URL,
                    headers=self._headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

                if resp.status_code == 401:
                    logger.warning("[OpenRouter] Invalid/expired API key (HTTP 401). Aborting OpenRouter pool.")
                    self._auth_failed = True
                    return None

                if resp.status_code == 429:
                    self._mark_rate_limited(model)
                    return None

                if resp.status_code == 200:
                    data    = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                    )
                    return content.strip() if content else None

                logger.warning(
                    f"[OpenRouter] {model} ? HTTP {resp.status_code} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )

            except requests.exceptions.Timeout:
                logger.warning(
                    f"[OpenRouter] {model} ? Timeout "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )
            except Exception as e:
                logger.error(f"[OpenRouter] {model} ? Unexpected error: {e}")

            if attempt < MAX_RETRIES_PER_MODEL:
                time.sleep(RETRY_DELAY)

        return None

    def _call_with_fallback(
        self,
        pool: list[str],
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> str:
        # 1. Groq LPU ultra-fast priority if available
        if self.groq_key:
            groq_res = self._call_groq(messages, max_tokens, temperature)
            if groq_res:
                return groq_res

        # 2. OpenRouter pool
        if not getattr(self, "_auth_failed", False):
            if model and not self._is_rate_limited(model):
                result = self._call(model, messages, max_tokens, temperature, response_format)
                if result:
                    return result
                if getattr(self, "_auth_failed", False):
                    pass
                else:
                    logger.info(f"[OpenRouter] Requested model failed, falling back to pool: {model}")

            if not getattr(self, "_auth_failed", False):
                for m in pool:
                    if self._is_rate_limited(m):
                        continue
                    logger.info(f"[OpenRouter] Trying: {m}")
                    result = self._call(m, messages, max_tokens, temperature, response_format)
                    if result:
                        logger.info(f"[OpenRouter] [OK] Success: {m}")
                        return result
                    if getattr(self, "_auth_failed", False):
                        break

        # 3. Fallback to NVIDIA API
        if self.nvidia_api_key:
            logger.info("[NVIDIA API] Falling back to NVIDIA NIM...")
            nv_result = self._call_nvidia(messages, max_tokens, temperature, response_format)
            if nv_result:
                return nv_result

        raise RuntimeError(
            "[OpenRouter/NVIDIA] All model providers failed or are rate-limited. "
            "Please check your OpenRouter / NVIDIA API keys and network connection."
        )


    def chat(
        self,
        prompt: str,
        system: str = (
            "You are a component of INDUS, an AI assistant inspired by JARVIS. "
            "Be concise, helpful, and precise."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        return self._call_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature
        )

    def fast_chat(
        self,
        prompt: str,
        system: str = "Be concise and precise.",
        max_tokens: int = 512,
    ) -> str:
        """Groq LPU fast path -> OpenRouter fallback. Sub-second for intent/classification."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        result = self._call_groq(messages, max_tokens=max_tokens, temperature=0.2)
        if result:
            return result
        return self._call_with_fallback(TEXT_MODELS, messages, max_tokens=max_tokens, temperature=0.2)

    def chat_json(
        self,
        prompt: str,
        system: str = (
            "Return ONLY valid JSON. "
            "No markdown fences, no extra text, no explanation."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        raw = self._call_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature=0.2
        )

        clean = raw.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("`").strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(
                f"[OpenRouter] JSON parse failed: {e}\n"
                f"Raw response (first 300 chars): {raw[:300]}"
            )
            raise ValueError(
                f"Model returned unparseable JSON: {e}\n"
                f"Raw output: {raw[:200]}"
            )

    def vision(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/png",
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        return self._call_with_fallback(
            VISION_MODELS, messages, model, max_tokens, temperature=0.2
        )

    def vision_from_file(
        self,
        prompt: str,
        image_path: str,
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        path = Path(image_path)
        mime_map = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif":  "image/gif",
        }
        mime = mime_map.get(path.suffix.lower(), "image/png")

        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        return self.vision(prompt, image_b64, mime, system, model, max_tokens)

    def multi_turn(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
    
        return self._call_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature
        )

    def available_models(self) -> dict:
        return {
            "text_models":   TEXT_MODELS,
            "vision_models": VISION_MODELS,
            "rate_limited":  list(_rate_limited.keys()),
            "total_text":    len(TEXT_MODELS),
            "total_vision":  len(VISION_MODELS),
        }

client = OpenRouterClient()

if __name__ == "__main__":
    print("=" * 55)
    print("  INDUS -- OpenRouter Client Self-Test")
    print("=" * 55)

    print("\n[TEST 1] Basic chat...")
    try:
        reply = client.chat("Introduce yourself in one sentence.")
        print(f"  Response : {reply}")
        print(f"  Status   : PASS [OK]")
    except Exception as e:
        print(f"  Status   : FAIL ? -- {e}")

    print("\n[TEST 2] JSON mode...")
    try:
        data = client.chat_json(
            'List 3 programming languages. Format: {"languages": ["a", "b", "c"]}',
            system="Return only valid JSON. No extra text."
        )
        print(f"  Response : {data}")
        print(f"  Status   : PASS [OK]")
    except Exception as e:
        print(f"  Status   : FAIL ? -- {e}")

    print("\n[TEST 3] Multi-turn conversation...")
    try:
        history = [
            {"role": "system",    "content": "You are a helpful assistant. Be brief."},
            {"role": "user",      "content": "My name is Tony."},
            {"role": "assistant", "content": "Hello Tony, how can I help you?"},
            {"role": "user",      "content": "What is my name?"},
        ]
        reply = client.multi_turn(history)
        print(f"  Response : {reply}")
        print(f"  Status   : PASS [OK]")
    except Exception as e:
        print(f"  Status   : FAIL ? -- {e}")

    print("\n[TEST 4] Model pool info...")
    info = client.available_models()
    print(f"  Text models   : {info['total_text']}")
    print(f"  Vision models : {info['total_vision']}")
    print(f"  Rate limited  : {info['rate_limited'] or 'none'}")
    print(f"  Status        : PASS [OK]")

    print("\n" + "=" * 55)
    print("  All tests complete.")
    print("=" * 55)