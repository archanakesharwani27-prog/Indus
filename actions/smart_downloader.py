# actions/smart_downloader.py
"""
INDUS Autonomous Smart Downloader & Media Retrieval Engine
==========================================================
Universal downloader supporting:
1. Direct URL downloads (EXE, ZIP, PDF, ISO, MP4, MP3, etc.)
2. Universal video/audio from 1500+ platforms (YouTube, Insta, X, Reddit, TikTok) via yt-dlp
3. Website search & download link extraction (scrapes download buttons from any site)
4. YouTube tutorial & Web Search fallback when download flow is complex/ambiguous
5. Auto-organization in Downloads/IndusDownloads
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
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger("IndusDownloader")

DOWNLOADS_DIR = Path.home() / "Downloads" / "IndusDownloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _get_ffmpeg_path() -> Optional[str]:
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


# --- 1. Direct File Downloader ---------------------------------------------

def download_direct_url(url: str, output_name: Optional[str] = None, player=None) -> Dict[str, Any]:
    """Downloads a file directly from a URL via streaming HTTP/HTTPS."""
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    if player:
        player.write_log(f"[Download] Starting direct download: {clean_url[:45]}...")

    headers = {"User-Agent": USER_AGENT}
    try:
        with requests.get(clean_url, stream=True, timeout=30, headers=headers) as r:
            r.raise_for_status()

            # Determine filename
            fname = output_name
            if not fname:
                cd = r.headers.get("content-disposition", "")
                fname_match = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
                if fname_match:
                    fname = fname_match.group(1).strip()
                else:
                    path_part = urlparse(clean_url).path.rstrip("/")
                    fname = os.path.basename(path_part) or f"download_{int(time.time())}.bin"

            # Clean filename
            fname = re.sub(r'[\/\\*?:"<>|]', "_", fname)
            out_path = DOWNLOADS_DIR / fname

            # Write stream
            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            size_mb = out_path.stat().st_size / (1024 * 1024)
            if player:
                player.write_log(f"[Download] Complete: {fname} ({size_mb:.2f} MB)")

            return {
                "success": True,
                "file_path": str(out_path),
                "filename": fname,
                "size_mb": round(size_mb, 2),
                "message": f"File '{fname}' ({size_mb:.2f} MB) successfully download ho gayi! Downloads/IndusDownloads mein saved hai."
            }
    except Exception as e:
        logger.error(f"[Download] Direct download error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Direct download failed: {e}"
        }


# --- 2. Universal Video & Audio Downloader (yt-dlp) ------------------------

def download_media_platform(
    url: str,
    format_type: str = "video",
    player=None
) -> Dict[str, Any]:
    """Downloads media from YouTube, Instagram, X, Reddit, TikTok, etc. via yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        return {
            "success": False,
            "message": "yt-dlp module not installed."
        }

    if player:
        player.write_log(f"[Download] Fetching media ({format_type}): {url[:45]}...")

    ffmpeg_exe = _get_ffmpeg_path()
    out_tmpl = str(DOWNLOADS_DIR / "%(title).60s_%(id)s.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "outtmpl": out_tmpl,
        "quiet": True,
        "no_warnings": True,
        "user_agent": USER_AGENT,
    }

    if ffmpeg_exe:
        ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_exe).parent)

    if format_type.lower() in ("audio", "mp3"):
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        })
    else:  # best video + audio
        ydl_opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Media")
            ext = "mp3" if format_type.lower() in ("audio", "mp3") else info.get("ext", "mp4")

            if player:
                player.write_log(f"[Download] Media download complete: {title[:30]}")

            return {
                "success": True,
                "title": title,
                "format": ext,
                "message": f"'{title}' ({ext.upper()}) successfully download ho gaya! Downloads/IndusDownloads folder mein save ho chuka hai."
            }
    except Exception as e:
        logger.error(f"[Download] yt-dlp error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Media download failed: {e}"
        }


# --- 3. Smart Website Scraper & Download Link Finder ------------------------

def find_and_download_from_site(
    website_url: str,
    item_name: str,
    player=None
) -> Dict[str, Any]:
    """
    Visits a website, finds direct download links matching the requested item/file,
    and initiates the download.
    """
    clean_url = website_url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    if player:
        player.write_log(f"[Download] Searching download link on {clean_url} for '{item_name}'...")

    try:
        r = requests.get(clean_url, headers={"User-Agent": USER_AGENT}, timeout=15)
        html = r.text

        # Extract all href links
        links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        binary_exts = (".exe", ".msi", ".zip", ".iso", ".dmg", ".pkg", ".tar.gz", ".pdf", ".mp4", ".mp3", ".rar", ".7z")

        candidate_links = []
        for l in links:
            full_l = urljoin(clean_url, l)
            lower_l = full_l.lower()
            if any(lower_l.endswith(ext) or ext in lower_l for ext in binary_exts):
                candidate_links.append(full_l)

        # Match with item_name keywords
        item_words = re.findall(r'[a-zA-Z0-9]+', item_name.lower())
        best_link = None
        for cl in candidate_links:
            score = sum(1 for w in item_words if w in cl.lower())
            if score > 0 or not best_link:
                best_link = cl
                if score >= len(item_words):
                    break

        if best_link:
            if player:
                player.write_log(f"[Download] Found direct link: {best_link[:50]}")
            return download_direct_url(best_link, player=player)

        # If no direct downloadable link found, check if it is a media platform
        if any(dom in clean_url.lower() for dom in ("youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com", "reddit.com", "tiktok.com", "vimeo.com")):
            return download_media_platform(clean_url, format_type="video", player=player)

        # Fallback: Open in browser and guide user
        return {
            "success": False,
            "need_assistance": True,
            "url": clean_url,
            "message": f"Direct link automatically detect nahi hua. Main browser mein download page open kar rahi hoon."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "need_assistance": True,
            "url": clean_url,
            "message": f"Website access error: {e}"
        }


# --- 4. YouTube Tutorial / Web Research Fallback ---------------------------

def research_how_to_download(item_name: str, website: str = "", player=None) -> str:
    """
    Searches YouTube / Web for tutorials on how to download a specific software/item,
    and returns a crisp Hinglish step-by-step guide or opens the video.
    """
    query = f"how to download {item_name} from {website}".strip() if website else f"how to download {item_name}"
    if player:
        player.write_log(f"[Download] Researching tutorial: {query}")

    from actions.deep_research import deep_research
    summary = deep_research(query=query, domain="tech", player=player)
    return summary


# --- 5. Winget Download fallback for known apps ----------------------------

_WINGET_KNOWN = {
    "bluestacks": "BlueStack Systems", "chrome": "Google.Chrome",
    "firefox": "Mozilla.Firefox", "vlc": "VideoLAN.VLC",
    "7zip": "7zip.7zip", "7-zip": "7zip.7zip", "git": "Git.Git",
    "nodejs": "OpenJS.NodeJS", "node": "OpenJS.NodeJS",
    "python": "Python.Python.3.12", "discord": "Discord.Discord",
    "telegram": "Telegram.TelegramDesktop", "steam": "Valve.Steam",
    "spotify": "Spotify.Spotify", "obs": "OBSProject.OBSStudio",
    "vscode": "Microsoft.VisualStudioCode", "vs code": "Microsoft.VisualStudioCode",
    "zoom": "Zoom.Zoom", "winrar": "RARLab.WinRAR",
}

def _winget_download(item_name: str, player=None) -> Dict[str, Any]:
    """Try to install/download via winget for known apps."""
    try:
        import shutil
        winget = shutil.which("winget")
        if not winget:
            return {"success": False}
        name_lower = item_name.lower()
        winget_id = None
        for key, wid in _WINGET_KNOWN.items():
            if key in name_lower:
                winget_id = wid
                break
        if not winget_id:
            return {"success": False}

        if player:
            player.write_log(f"[Download] Installing {item_name} via winget ({winget_id})...")
        result = subprocess.run(
            [winget, "install", "--id", winget_id, "--silent", "--accept-package-agreements",
             "--accept-source-agreements", "--disable-interactivity"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return {"success": True, "message": f"{item_name} successfully install ho gaya! Winget se automatically install kiya gaya hai."}
        return {"success": False, "error": result.stderr[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- 6. Master Smart Downloader Dispatcher ----------------------------------

def smart_downloader(parameters: dict = None, player=None, speak=None) -> str:
    """
    Main tool handler for smart_downloader.
    Parameters:
    - url / website: URL of the website or file
    - item_name / query: Name of the software, file, or media to download
    - format: 'video' | 'audio' | 'direct' (default: auto)
    - action: 'download' | 'tutorial' | 'open_folder'
    - dry_run: True = don't actually download, just detect (for testing)
    """
    params = parameters or {}
    action = params.get("action", "download").lower().strip()
    url = (params.get("url") or params.get("website") or "").strip()
    item_name = (params.get("item_name") or params.get("query") or params.get("item") or "").strip()
    format_type = params.get("format", "video").lower().strip()
    dry_run = params.get("dry_run", False)

    if dry_run:
        return f"[DryRun] smart_downloader ready. URL='{url}' item='{item_name}' format='{format_type}'"

    if action == "open_folder":
        os.startfile(str(DOWNLOADS_DIR))
        return "Downloads folder open kar diya gaya hai."

    if action in ("tutorial", "help", "guide"):
        guide = research_how_to_download(item_name=item_name or url, website=url, player=player)
        return f"Download Tutorial Guide:\n{guide}"

    # If URL is a media site (YouTube, Instagram, etc.)
    if url and any(p in url.lower() for p in ("youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com", "reddit.com", "tiktok.com", "pin.it", "pinterest.com", "vimeo.com", "facebook.com", "fb.watch")):
        res = download_media_platform(url=url, format_type=format_type, player=player)
        return res.get("message", "Media download complete.")

    # Intelligent direct content detection (check if URL returns a direct binary or non-HTML file)
    if url:
        clean_u = url.strip()
        if not clean_u.startswith(("http://", "https://")): clean_u = "https://" + clean_u
        try:
            head_r = requests.head(clean_u, headers={"User-Agent": USER_AGENT}, timeout=5, allow_redirects=True)
            ctype = head_r.headers.get("content-type", "").lower()
            cdisp = head_r.headers.get("content-disposition", "").lower()
            if "attachment" in cdisp or (ctype and not "text/html" in ctype):
                res = download_direct_url(url=clean_u, player=player)
                if res.get("success"):
                    return res.get("message")
        except Exception:
            pass

    # If direct file link (ends with extension)
    if url and any(url.lower().split("?")[0].endswith(ext) for ext in (".exe", ".msi", ".zip", ".iso", ".dmg", ".pdf", ".mp4", ".mp3", ".rar", ".7z", ".tar.gz", ".txt", ".bin", ".whl", ".deb", ".rpm")):
        res = download_direct_url(url=url, player=player)
        return res.get("message", "Direct download complete.")

    # If website was given with item name
    if url:
        res = find_and_download_from_site(website_url=url, item_name=item_name or "download", player=player)
        if res.get("success"):
            return res.get("message", "File download complete.")
        elif res.get("need_assistance"):
            # Open the browser on screen and offer YouTube tutorial/guidance
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass
            # Research tutorial
            guide = research_how_to_download(item_name=item_name or url, website=url, player=player)
            return (
                f"Sir, maine browser mein download page open kar diya hai. "
                f"Iske download steps ye hain: {guide}. "
                f"Agar koi human verification/captcha chahiye to screen par complete kar lijiye."
            )
        else:
            return res.get("message", "Download attempt finished.")

    # If only item name was given (e.g. "Blender download karo", "VS Code download karo")
    if item_name:
        # Check if deep research can find official download URL
        from actions.deep_research import deep_research
        res_info = deep_research(f"official direct download link for {item_name}", domain="tech", player=player)
        # Search for direct URL in summary
        urls_found = re.findall(r'https?://[\w\-\.\/\?\=\&\%]+', res_info)
        if urls_found:
            dl_res = find_and_download_from_site(website_url=urls_found[0], item_name=item_name, player=player)
            if dl_res.get("success"):
                return dl_res.get("message")

        # Fallback: Open browser to search and explain
        search_url = f"https://www.google.com/search?q={requests.utils.quote(item_name + ' download')}"
        try:
            import webbrowser
            webbrowser.open(search_url)
        except Exception:
            pass
        return f"Sir, maine browser mein '{item_name}' ka official download page open kar diya hai. Aap wahan se 1-click mein download start kar sakte hain."

    return "Sir, please website URL ya item name provide karein jo aap download karna chahte hain."
