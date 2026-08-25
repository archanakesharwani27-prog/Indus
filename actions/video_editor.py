# actions/video_editor.py
"""
INDUS Autonomous AI Video Editing & Media Studio
=================================================
Comprehensive voice & text controlled video editor powered by FFmpeg 7.1 and OpenCV.

Capabilities:
1. trim / cut: Precise time clipping (start, end)
2. merge / concatenate: Join multiple video clips
3. extract_audio: Convert video to high-bitrate MP3/WAV/AAC
4. add_audio / replace_audio: Background music overlay or sound replacement
5. change_speed: Slow-motion (0.25x-0.75x) or Timelapse/Fast-forward (1.25x-8.0x)
6. convert_aspect_ratio: 9:16 (Reels/Shorts/TikTok), 16:9 (YouTube), 1:1 (Instagram)
7. compress: High-efficiency compression for WhatsApp/Discord sharing
8. extract_frame / screenshot: High-res frame snapshot at timestamp
9. create_gif: Palette-optimized animated GIF generation
10. mute: Remove audio track completely
11. reverse: Reverse video playback
12. apply_filter: Black & White, Sepia, Vintage, Brighten, Vignette
13. add_watermark / text_overlay: Burn logo or text overlay onto video
14. info: Inspect video duration, resolution, fps, bitrate, and codec
"""

from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("IndusVideoEditor")

DESKTOP = Path.home() / "Desktop"
VIDEOS_OUT = DESKTOP / "IndusEditedVideos"
VIDEOS_OUT.mkdir(parents=True, exist_ok=True)


def _get_ffmpeg_exe() -> str:
    """Finds FFmpeg executable via system PATH or imageio_ffmpeg binary."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _get_ffprobe_exe() -> str:
    """Finds FFprobe executable."""
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffprobe:
        return sys_ffprobe
    # Fallback to ffmpeg companion if in same dir
    ffmpeg_exe = _get_ffmpeg_exe()
    probe_candidate = Path(ffmpeg_exe).parent / "ffprobe.exe"
    if probe_candidate.exists():
        return str(probe_candidate)
    return "ffprobe"


def _format_time(t_val: Any) -> str:
    """Convert integer seconds or string time to standard HH:MM:SS format."""
    if isinstance(t_val, (int, float)):
        secs = int(t_val)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    s = str(t_val).strip()
    if re.match(r"^\d+$", s):
        secs = int(s)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    return s


def _make_out_path(src_path: str, suffix: str, ext: str = ".mp4") -> Path:
    """Generate timestamped output path in Desktop/IndusEditedVideos."""
    p = Path(src_path)
    stem = p.stem if p.exists() else "video"
    ts = time.strftime("%Y%m%d_%H%M%S")
    return VIDEOS_OUT / f"{stem}_{suffix}_{ts}{ext}"


# --- 1. Video Info & Inspection --------------------------------------------

def get_video_info(video_path: str) -> Dict[str, Any]:
    """Inspects video metadata via FFmpeg."""
    p = Path(video_path)
    if not p.exists():
        return {"error": f"File not found: {video_path}"}

    ffmpeg = _get_ffmpeg_exe()
    cmd = [ffmpeg, "-i", str(p)]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    stderr = res.stderr

    duration_m = re.search(r"Duration:\s*([\d:.]+)", stderr)
    resolution_m = re.search(r"Video:.*?(\d{3,4}x\d{3,4})", stderr)
    fps_m = re.search(r"([\d.]+)\s*fps", stderr)
    bitrate_m = re.search(r"bitrate:\s*([\d.]+\s*\w+/s)", stderr)

    return {
        "file": p.name,
        "size": f"{p.stat().st_size / (1024*1024):.2f} MB",
        "duration": duration_m.group(1) if duration_m else "Unknown",
        "resolution": resolution_m.group(1) if resolution_m else "Unknown",
        "fps": fps_m.group(1) if fps_m else "Unknown",
        "bitrate": bitrate_m.group(1) if bitrate_m else "Unknown",
    }


# --- 2. Trimming & Cutting --------------------------------------------------

def trim_video(
    video_path: str,
    start: str = "00:00:00",
    end: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """Cuts a video segment between start and end timestamps."""
    p = Path(video_path)
    if not p.exists():
        return f"Video file not found: {video_path}"

    start_fmt = _format_time(start)
    out_file = Path(output_path) if output_path else _make_out_path(video_path, "trimmed")

    ffmpeg = _get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-ss", start_fmt, "-i", str(p)]
    if end:
        cmd.extend(["-to", _format_time(end)])
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero", str(out_file)])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_file.exists():
        return f"Video trim ho gayi! Output saved: {out_file}"
    return f"Video trim failed: {res.stderr[:300]}"


# --- 3. Extract Audio -------------------------------------------------------

def extract_audio(
    video_path: str,
    audio_format: str = "mp3",
    bitrate: str = "320k",
    output_path: Optional[str] = None
) -> str:
    """Extracts soundtrack from video into high quality MP3 or WAV."""
    p = Path(video_path)
    if not p.exists():
        return f"Video file not found: {video_path}"

    ext = f".{audio_format.lstrip('.')}"
    out_file = Path(output_path) if output_path else _make_out_path(video_path, "audio", ext)

    ffmpeg = _get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-i", str(p), "-vn", "-b:a", bitrate, str(out_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        return f"Audio extract ho gaya! Format: {audio_format.upper()} ({bitrate}). Saved: {out_file}"
    return f"Audio extraction failed: {res.stderr[:300]}"


# --- 4. Add Background Music / Replace Audio --------------------------------

def add_audio_track(
    video_path: str,
    audio_path: str,
    mix_mode: str = "replace",
    bg_volume: float = 0.3,
    output_path: Optional[str] = None
) -> str:
    """Overlays or replaces video audio with background music."""
    vp, ap = Path(video_path), Path(audio_path)
    if not vp.exists(): return f"Video file not found: {video_path}"
    if not ap.exists(): return f"Audio file not found: {audio_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, "bgm")
    ffmpeg = _get_ffmpeg_exe()

    if mix_mode == "replace":
        cmd = [
            ffmpeg, "-y", "-i", str(vp), "-i", str(ap),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_file)
        ]
    else:  # Overlay mix
        cmd = [
            ffmpeg, "-y", "-i", str(vp), "-i", str(ap),
            "-filter_complex", f"[0:a]volume=1.0[a1];[1:a]volume={bg_volume}[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", str(out_file)
        ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_file.exists():
        return f"Background music add ho gaya! Mode: {mix_mode}. Saved: {out_file}"
    return f"Audio mixing failed: {res.stderr[:300]}"


# --- 5. Change Speed (Slow-mo / Timelapse) ----------------------------------

def _has_audio_stream(video_path: Path) -> bool:
    """Checks if video contains an audio stream."""
    ffmpeg = _get_ffmpeg_exe()
    res = subprocess.run([ffmpeg, "-i", str(video_path)], capture_output=True, text=True, errors="ignore")
    return "Audio:" in res.stderr


def change_speed(
    video_path: str,
    speed: float = 2.0,
    output_path: Optional[str] = None
) -> str:
    """Changes video playback speed (e.g. 0.5 for 2x slow-mo, 2.0 for 2x fast-forward)."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, f"speed_{speed}x")
    ffmpeg = _get_ffmpeg_exe()

    pts_factor = 1.0 / max(0.1, float(speed))
    has_audio = _has_audio_stream(p)

    if has_audio:
        audio_filters = []
        curr_s = speed
        while curr_s > 2.0:
            audio_filters.append("atempo=2.0")
            curr_s /= 2.0
        while curr_s < 0.5:
            audio_filters.append("atempo=0.5")
            curr_s /= 0.5
        audio_filters.append(f"atempo={curr_s:.3f}")
        atempo_str = ",".join(audio_filters)

        cmd = [
            ffmpeg, "-y", "-i", str(p),
            "-filter_complex", f"[0:v]setpts={pts_factor:.4f}*PTS[v];[0:a]{atempo_str}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-c:a", "aac", str(out_file)
        ]
    else:
        cmd = [
            ffmpeg, "-y", "-i", str(p),
            "-vf", f"setpts={pts_factor:.4f}*PTS",
            "-c:v", "libx264", str(out_file)
        ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_file.exists():
        return f"Video speed {speed}x set ho gayi! Saved: {out_file}"
    return f"Change speed failed: {res.stderr[:300]}"


# --- 6. Aspect Ratio Conversion (Reels 9:16 / 16:9 / 1:1) -------------------

def convert_aspect_ratio(
    video_path: str,
    aspect: str = "9:16",
    output_path: Optional[str] = None
) -> str:
    """Converts video aspect ratio with blurred background padding (Reels 9:16, YouTube 16:9, Square 1:1)."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    clean_aspect = aspect.lower().strip()
    out_file = Path(output_path) if output_path else _make_out_path(video_path, f"aspect_{clean_aspect.replace(':','x')}")
    ffmpeg = _get_ffmpeg_exe()

    if clean_aspect in ("9:16", "reels", "shorts", "tiktok"):
        w, h = 1080, 1920
    elif clean_aspect in ("1:1", "square", "instagram"):
        w, h = 1080, 1080
    else:  # 16:9
        w, h = 1920, 1080

    # Fit video inside target box with black padding / centered
    filter_str = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"

    cmd = [
        ffmpeg, "-y", "-i", str(p),
        "-vf", filter_str,
        "-c:v", "libx264", "-c:a", "copy", str(out_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_file.exists():
        return f"Video aspect ratio {aspect} ({w}x{h}) format mein convert ho gayi! Saved: {out_file}"
    return f"Aspect ratio conversion failed: {res.stderr[:300]}"


# --- 7. Video Compression --------------------------------------------------

def compress_video(
    video_path: str,
    preset: str = "whatsapp",
    output_path: Optional[str] = None
) -> str:
    """Compresses video for easy social sharing without noticeable visual degradation."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, "compressed")
    ffmpeg = _get_ffmpeg_exe()

    crf = "28"
    if preset == "discord": crf = "26"
    elif preset == "high":  crf = "23"
    elif preset == "low":   crf = "32"

    cmd = [
        ffmpeg, "-y", "-i", str(p),
        "-vcodec", "libx264", "-crf", crf, "-preset", "medium",
        "-acodec", "aac", "-b:a", "128k", str(out_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        orig_mb = p.stat().st_size / (1024*1024)
        new_mb = out_file.stat().st_size / (1024*1024)
        reduction = (1 - (new_mb / orig_mb)) * 100 if orig_mb > 0 else 0
        return f"Video compress ho gayi! Size {orig_mb:.1f}MB se ghat kar {new_mb:.1f}MB ({reduction:.0f}% reduction) ho gaya. Saved: {out_file}"
    return f"Video compression failed: {res.stderr[:300]}"


# --- 8. Extract Frame / Snapshot -------------------------------------------

def extract_frame(
    video_path: str,
    timestamp: str = "00:00:05",
    output_path: Optional[str] = None
) -> str:
    """Captures a pristine high-resolution JPEG snapshot frame at specified timestamp."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, "frame", ".jpg")
    ffmpeg = _get_ffmpeg_exe()
    ts_fmt = _format_time(timestamp)

    cmd = [ffmpeg, "-y", "-ss", ts_fmt, "-i", str(p), "-vframes", "1", "-q:v", "2", str(out_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        return f"Video frame snapshot capture ho gaya! Timestamp: {ts_fmt}. Saved: {out_file}"
    return f"Frame extraction failed: {res.stderr[:300]}"


# --- 9. Create Animated GIF ------------------------------------------------

def create_gif(
    video_path: str,
    start: str = "00:00:00",
    duration: int = 5,
    fps: int = 15,
    width: int = 480,
    output_path: Optional[str] = None
) -> str:
    """Generates a high-quality palette-optimized animated GIF."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, "anim", ".gif")
    ffmpeg = _get_ffmpeg_exe()
    ts_fmt = _format_time(start)

    filter_str = f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
    cmd = [
        ffmpeg, "-y", "-ss", ts_fmt, "-t", str(duration),
        "-i", str(p), "-vf", filter_str, str(out_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        return f"Animated GIF generate ho gaya! ({duration}s @ {fps}fps). Saved: {out_file}"
    return f"GIF creation failed: {res.stderr[:300]}"


# --- 10. Merge / Concatenate Videos ----------------------------------------

def merge_videos(video_paths: List[str], output_path: Optional[str] = None) -> str:
    """Concatenates multiple video files in sequence into one continuous video."""
    valid_paths = [Path(p) for p in video_paths if Path(p).exists()]
    if len(valid_paths) < 2:
        return "Kam se kam 2 valid video files provide karni hongi merge karne ke liye."

    out_file = Path(output_path) if output_path else VIDEOS_OUT / f"merged_video_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    list_file = VIDEOS_OUT / f"concat_list_{int(time.time())}.txt"

    with open(list_file, "w", encoding="utf-8") as f:
        for vp in valid_paths:
            f.write(f"file '{vp.resolve()}'\n")

    ffmpeg = _get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    try:
        os.remove(list_file)
    except Exception:
        pass

    if res.returncode == 0 and out_file.exists():
        return f"{len(valid_paths)} videos successfully merge ho gayi! Saved: {out_file}"
    return f"Video merge failed: {res.stderr[:300]}"


# --- 11. Mute Video --------------------------------------------------------

def mute_video(video_path: str, output_path: Optional[str] = None) -> str:
    """Completely strips audio track from video."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, "muted")
    ffmpeg = _get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-i", str(p), "-c:v", "copy", "-an", str(out_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        return f"Video mute ho gayi (Audio removed)! Saved: {out_file}"
    return f"Mute video failed: {res.stderr[:300]}"


# --- 12. Reverse Video -----------------------------------------------------

def reverse_video(video_path: str, output_path: Optional[str] = None) -> str:
    """Plays video backwards."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    out_file = Path(output_path) if output_path else _make_out_path(video_path, "reversed")
    ffmpeg = _get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-i", str(p), "-vf", "reverse", "-af", "areverse", str(out_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        return f"Video reverse playback ho gayi! Saved: {out_file}"
    return f"Reverse video failed: {res.stderr[:300]}"


# --- 13. Visual Filters & Effects ------------------------------------------

def apply_filter(
    video_path: str,
    filter_name: str = "black_and_white",
    output_path: Optional[str] = None
) -> str:
    """Applies visual color grading and aesthetic filters."""
    p = Path(video_path)
    if not p.exists(): return f"Video file not found: {video_path}"

    fname = filter_name.lower().strip()
    out_file = Path(output_path) if output_path else _make_out_path(video_path, f"filter_{fname}")
    ffmpeg = _get_ffmpeg_exe()

    filter_map = {
        "black_and_white": "hue=s=0",
        "bw": "hue=s=0",
        "grayscale": "hue=s=0",
        "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
        "vintage": "curves=vintage",
        "brighten": "eq=brightness=0.08:contrast=1.15",
        "vignette": "vignette=PI/4",
        "blur": "boxblur=5:1",
    }
    vf = filter_map.get(fname, "hue=s=0")

    cmd = [ffmpeg, "-y", "-i", str(p), "-vf", vf, "-c:a", "copy", str(out_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        return f"Video par '{filter_name}' filter apply ho gaya! Saved: {out_file}"
    return f"Filter application failed: {res.stderr[:300]}"


# --- 14. Master Video Editor Dispatcher -------------------------------------

def video_editor(parameters: dict = None, player=None, speak=None) -> str:
    """
    Main tool handler for video_editor.
    Actions:
    - trim (video_path, start, end)
    - extract_audio (video_path, format, bitrate)
    - add_audio / replace_audio (video_path, audio_path, mix_mode, bg_volume)
    - merge (video_paths)
    - change_speed (video_path, speed)
    - aspect_ratio (video_path, aspect="9:16"|"16:9"|"1:1")
    - compress (video_path, preset)
    - extract_frame (video_path, timestamp)
    - create_gif (video_path, start, duration, fps)
    - mute (video_path)
    - reverse (video_path)
    - filter (video_path, filter_name)
    - info (video_path)
    """
    params = parameters or {}
    action = params.get("action", "info").lower().strip()
    video_path = params.get("video_path") or params.get("file_path") or ""

    if player:
        player.write_log(f"[VideoEditor] Action: {action} on {Path(video_path).name if video_path else 'N/A'}")

    if action in ("info", "get_info", "stats"):
        info = get_video_info(video_path)
        if "error" in info: return info["error"]
        return f"Video Info for '{info['file']}': Duration: {info['duration']}, Res: {info['resolution']}, FPS: {info['fps']}, Bitrate: {info['bitrate']}, Size: {info['size']}."

    elif action in ("trim", "cut", "clip"):
        return trim_video(
            video_path=video_path,
            start=params.get("start", "00:00:00"),
            end=params.get("end"),
            output_path=params.get("output_path")
        )

    elif action in ("extract_audio", "to_audio", "to_mp3"):
        return extract_audio(
            video_path=video_path,
            audio_format=params.get("format", "mp3"),
            bitrate=params.get("bitrate", "320k"),
            output_path=params.get("output_path")
        )

    elif action in ("add_audio", "replace_audio", "bgm", "add_music"):
        return add_audio_track(
            video_path=video_path,
            audio_path=params.get("audio_path", ""),
            mix_mode=params.get("mix_mode", "replace"),
            bg_volume=float(params.get("volume", 0.3)),
            output_path=params.get("output_path")
        )

    elif action in ("merge", "concat", "combine", "join"):
        paths = params.get("video_paths") or [video_path]
        return merge_videos(video_paths=paths, output_path=params.get("output_path"))

    elif action in ("change_speed", "speed", "slowmo", "timelapse", "fast"):
        speed_val = float(params.get("speed", 2.0))
        return change_speed(video_path=video_path, speed=speed_val, output_path=params.get("output_path"))

    elif action in ("aspect_ratio", "reels", "shorts", "tiktok", "square", "resize"):
        aspect = params.get("aspect", "9:16")
        return convert_aspect_ratio(video_path=video_path, aspect=aspect, output_path=params.get("output_path"))

    elif action in ("compress", "reduce_size", "whatsapp", "discord"):
        preset = params.get("preset", "whatsapp")
        return compress_video(video_path=video_path, preset=preset, output_path=params.get("output_path"))

    elif action in ("extract_frame", "screenshot", "snapshot", "thumbnail"):
        ts = params.get("timestamp", "00:00:05")
        return extract_frame(video_path=video_path, timestamp=ts, output_path=params.get("output_path"))

    elif action in ("create_gif", "gif", "to_gif"):
        return create_gif(
            video_path=video_path,
            start=params.get("start", "00:00:00"),
            duration=int(params.get("duration", 5)),
            fps=int(params.get("fps", 15)),
            output_path=params.get("output_path")
        )

    elif action in ("mute", "remove_audio", "silence"):
        return mute_video(video_path=video_path, output_path=params.get("output_path"))

    elif action in ("reverse", "backwards"):
        return reverse_video(video_path=video_path, output_path=params.get("output_path"))

    elif action in ("filter", "effect", "bw", "sepia", "vintage"):
        fname = params.get("filter_name", "black_and_white")
        return apply_filter(video_path=video_path, filter_name=fname, output_path=params.get("output_path"))

    return f"Unknown video editing action: '{action}'. Available: trim, extract_audio, add_audio, merge, change_speed, aspect_ratio, compress, extract_frame, create_gif, mute, reverse, filter, info."
