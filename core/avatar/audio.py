# core/avatar/audio.py
"""
INDUS Avatar System -- Low-Latency PCM Audio Energy Analyzer
Fast, robust RMS extraction from incoming 16kHz PCM audio buffers.
"""

import math
import struct
from typing import Optional


def compute_pcm_rms(pcm_bytes: bytes) -> float:
    """
    Computes Root-Mean-Square (RMS) amplitude energy from raw 16-bit PCM bytes.
    Returns float energy level (0.0 to ~32767.0).
    """
    if not pcm_bytes or len(pcm_bytes) < 2:
        return 0.0

    count = len(pcm_bytes) // 2
    format_str = f"<{count}h"
    try:
        samples = struct.unpack(format_str, pcm_bytes[: count * 2])
    except Exception:
        return 0.0

    if not samples:
        return 0.0

    # Calculate sum of squares
    sum_squares = sum(float(s) * float(s) for s in samples)
    mean_square = sum_squares / count
    return math.sqrt(mean_square)
