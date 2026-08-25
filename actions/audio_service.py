import json
import logging
import time
from math import gcd
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import scipy.signal
import sounddevice as sd

logger = logging.getLogger("IndusAudio")

SEND_SAMPLE_RATE = 16000
DEFAULT_GAIN = 1.6


def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"


def get_available_mics() -> List[Dict]:
    """List all available audio input devices with user-friendly names."""
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
    except Exception as e:
        logger.error(f"Failed to query sound devices: {e}")
        return []

    mic_list = []
    default_in = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else 0

    for idx, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            api_name = hostapis[d["hostapi"]]["name"] if d.get("hostapi") is not None and d["hostapi"] < len(hostapis) else "Unknown"
            is_default = (idx == default_in)
            
            # Clean up device name
            raw_name = d.get("name", "Unknown Device").strip()
            # If name has system driver path, shorten it
            if "@System32" in raw_name or "bthhfenum" in raw_name:
                display_name = raw_name.split(";")[-1].replace(")", "").replace("%0", "").strip() or raw_name[:30]
            else:
                display_name = raw_name

            mic_list.append({
                "index": idx,
                "name": raw_name,
                "display_name": display_name,
                "hostapi": api_name,
                "channels": d.get("max_input_channels", 1),
                "samplerate": int(d.get("default_samplerate", 44100)),
                "is_default": is_default,
                "label": f"[{idx}] {display_name} ({api_name}){' * DEFAULT' if is_default else ''}"
            })
    return mic_list


def get_configured_mic_index() -> Optional[int]:
    """Retrieve user-configured microphone index or device name from config."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            saved = cfg.get("input_device")
            if saved is not None:
                # If integer index
                if isinstance(saved, int):
                    return saved
                # If name string, match against current devices
                mics = get_available_mics()
                for m in mics:
                    if saved.lower() in m["name"].lower() or saved.lower() in m["display_name"].lower():
                        return m["index"]
        except Exception:
            pass
    return None


def set_configured_mic(device_index_or_name) -> bool:
    """Save user-selected microphone to config."""
    try:
        cfg = {}
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        cfg["input_device"] = device_index_or_name
        CONFIG_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Failed to save input_device: {e}")
        return False


def get_configured_gain() -> float:
    """Retrieve configured mic gain boost (default 1.6x)."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return float(cfg.get("mic_gain", DEFAULT_GAIN))
        except Exception:
            pass
    return DEFAULT_GAIN


def set_configured_gain(gain: float) -> bool:
    """Save mic gain to config."""
    try:
        cfg = {}
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        cfg["mic_gain"] = float(gain)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        return True
    except Exception as e:
        return False


def resample_audio(audio_np_int16: np.ndarray, src_rate: int, dst_rate: int = SEND_SAMPLE_RATE, gain: float = 1.0) -> bytes:
    """Resample int16 PCM audio from src_rate to dst_rate and apply gain."""
    if src_rate != dst_rate:
        g = gcd(dst_rate, src_rate)
        up = dst_rate // g
        down = src_rate // g
        resampled = scipy.signal.resample_poly(audio_np_int16.astype(np.float32), up, down)
    else:
        resampled = audio_np_int16.astype(np.float32)

    if gain != 1.0:
        resampled = resampled * gain

    clipped = np.clip(resampled, -32768, 32767).astype(np.int16)
    return clipped.tobytes()


def calculate_rms(audio_np_int16: np.ndarray) -> float:
    """Calculate RMS volume level of audio chunk."""
    if len(audio_np_int16) == 0:
        return 0.0
    return float(np.linalg.norm(audio_np_int16) / np.sqrt(len(audio_np_int16)))


def create_input_stream(
    pcm_16k_callback: Callable[[bytes, float], None],
    device_index: Optional[int] = None,
    gain: Optional[float] = None,
    blocksize: int = 1024,
) -> Tuple[sd.InputStream, int, int]:
    """
    Creates and returns an sd.InputStream configured for the specified or best device.
    pcm_16k_callback receives: (pcm_bytes_16khz, rms_volume)
    Returns: (stream, actual_device_index, native_samplerate)
    """
    if gain is None:
        gain = get_configured_gain()

    if device_index is None:
        device_index = get_configured_mic_index()

    # List candidates to try if the primary device fails
    candidates = []
    if device_index is not None:
        candidates.append(device_index)
    
    # Add default device
    try:
        def_dev = sd.default.device[0]
        if def_dev is not None and def_dev not in candidates:
            candidates.append(def_dev)
    except Exception:
        pass

    # Add other MME / DirectSound devices (0, 7, etc.)
    for extra in [0, 7, 1, 8, None]:
        if extra not in candidates:
            candidates.append(extra)

    last_err = None
    for cand in candidates:
        try:
            # Query candidate device info
            dev_info = sd.query_devices(cand) if cand is not None else sd.query_devices(sd.default.device[0])
            native_sr = int(dev_info.get("default_samplerate", 44100))
            channels = 1

            # Try 16000Hz first, then native_sr
            for sr in [SEND_SAMPLE_RATE, native_sr]:
                try:
                    def _sd_callback(indata, frames, time_info, status):
                        # Convert to int16 1D numpy array
                        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
                        rms = calculate_rms(mono)
                        pcm_bytes = resample_audio(mono, src_rate=sr, dst_rate=SEND_SAMPLE_RATE, gain=gain)
                        pcm_16k_callback(pcm_bytes, rms)

                    stream = sd.InputStream(
                        device=cand,
                        samplerate=sr,
                        channels=channels,
                        dtype="int16",
                        blocksize=blocksize,
                        callback=_sd_callback,
                    )
                    actual_idx = cand if cand is not None else sd.default.device[0]
                    return stream, actual_idx, sr
                except Exception as e:
                    last_err = e
                    continue
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Could not open any audio input stream. Last error: {last_err}")
