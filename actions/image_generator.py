# actions/image_generator.py
"""
INDUS Autonomous AI Image Generator & Neural Studio
====================================================
Generates photorealistic artwork, wallpapers, illustrations, and concept art
using FLUX.1, SDXL, and Neural Diffusion models.

Features:
- Instant high-res image generation (1024x1024, 16:9 1280x720, 9:16 720x1280)
- Floating HUD Image Card integration with live preview
- One-click Set Wallpaper and Open Fullscreen actions
- Clean automatic file organization in Desktop/IndusGeneratedImages
"""

from __future__ import annotations
import ctypes
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

import requests

logger = logging.getLogger("IndusImageGenerator")

DESKTOP = Path.home() / "Desktop"
IMAGES_OUT = DESKTOP / "IndusGeneratedImages"
IMAGES_OUT.mkdir(parents=True, exist_ok=True)


STYLE_PROMPTS = {
    "photorealistic": "photorealistic, 8k resolution, highly detailed, master photography, natural lighting, sharp focus",
    "cyberpunk": "cyberpunk style, neon glow, futuristic city, cinematic volumetric lighting, high tech octane render 8k",
    "anime": "anime aesthetic, Makoto Shinkai style, vibrant colors, detailed illustration, masterpiece",
    "cinematic": "cinematic movie still, 35mm photograph, dramatic atmosphere, anamorphic lens flare, depth of field",
    "3d_render": "3D Pixar Disney style render, blender 3D, octane render, smooth lighting, ultra-detailed",
    "digital_art": "digital concept art, trending on ArtStation, dynamic composition, vibrant palette",
}

ASPECT_DIMS = {
    "1:1": (1024, 1024),
    "square": (1024, 1024),
    "16:9": (1280, 720),
    "landscape": (1280, 720),
    "wallpaper": (1920, 1080),
    "9:16": (720, 1280),
    "portrait": (720, 1280),
    "story": (720, 1280),
    "reels": (720, 1280),
}


def generate_ai_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    style: str = "photorealistic",
    set_as_wallpaper: bool = False,
    player=None,
    speak=None,
) -> Dict[str, Any]:
    """
    Synthesizes a high-definition AI image, saves to Desktop, and triggers the HUD Image Card.
    """
    clean_p = (prompt or "").strip()
    if not clean_p:
        return {"success": False, "message": "Please describe what image you want to generate."}

    if player:
        player.write_log(f"[ImageGen] Generating artwork for prompt: '{clean_p[:40]}...'")

    # 1. Resolve dimensions & style enhancement
    aspect_key = (aspect_ratio or "1:1").lower().strip()
    w, h = ASPECT_DIMS.get(aspect_key, (1024, 1024))

    style_suffix = STYLE_PROMPTS.get((style or "").lower().strip(), "")
    full_prompt = f"{clean_p}, {style_suffix}".strip().rstrip(",")

    seed = random.randint(1000, 9999999)
    encoded_prompt = quote_plus(full_prompt)

    # 2. Query FLUX.1 Neural Engine
    api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&model=flux&nologo=true&seed={seed}"

    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^a-zA-Z0-9_]", "_", clean_p[:25]).strip("_") or "artwork"
    out_file = IMAGES_OUT / f"{safe_title}_{ts}.png"

    try:
        r = requests.get(api_url, timeout=25, headers={"User-Agent": "INDUS-NeuralStudio/2.0"})
        if r.status_code == 200 and len(r.content) > 5000:
            out_file.write_bytes(r.content)
            logger.info(f"[ImageGen] Successfully saved: {out_file}")
        else:
            # Fallback to Turbo Model
            fb_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&model=turbo&nologo=true&seed={seed}"
            r_fb = requests.get(fb_url, timeout=20)
            if r_fb.status_code == 200 and len(r_fb.content) > 5000:
                out_file.write_bytes(r_fb.content)
            else:
                return {
                    "success": False,
                    "message": "Image generation server temporarily busy. Please try again in a few seconds."
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"Image generation network error: {e}"
        }

    # 3. Trigger HUD Image Card
    card_data = {
        "prompt": clean_p,
        "image_path": str(out_file.resolve()),
        "model": "FLUX.1-NeuralHD",
        "dimensions": f"{w}x{h}",
    }

    if player:
        try:
            if hasattr(player, "show_image_card"):
                player.show_image_card(card_data)
            elif hasattr(player, "_win") and hasattr(player._win, "show_image_card"):
                player._win.show_image_card(card_data)
        except Exception as e:
            print(f"[ImageGen] Card show error: {e}")

    # 4. Optional Set Wallpaper
    if set_as_wallpaper:
        try:
            SPI_SETDESKWALLPAPER = 20
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(out_file.resolve()), 3)
            if player:
                player.write_log("[ImageGen] Image set as Desktop wallpaper!")
        except Exception:
            pass

    spoken_msg = f"Aapki image generate ho gayi hai aur screen par display ho rahi hai. File Desktop/IndusGeneratedImages mein save ho chuki hai."
    return {
        "success": True,
        "image_path": str(out_file),
        "message": spoken_msg,
    }


def image_generator(parameters: dict = None, player=None, speak=None) -> str:
    """Main tool entry point for image_generator."""
    params = parameters or {}
    prompt = params.get("prompt") or params.get("description") or ""
    aspect = params.get("aspect_ratio") or params.get("aspect") or "1:1"
    style = params.get("style", "photorealistic")
    set_wp = bool(params.get("set_as_wallpaper", False))

    res = generate_ai_image(
        prompt=prompt,
        aspect_ratio=aspect,
        style=style,
        set_as_wallpaper=set_wp,
        player=player,
        speak=speak
    )
    return res.get("message", "Image generation finished.")
