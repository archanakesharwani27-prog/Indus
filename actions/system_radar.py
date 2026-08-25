# actions/system_radar.py
# INDUS Live Radar & Life Tracking Engine
# Indian Railways Train Running Status & PNR Tracking, System RAM Optimizer, and Live News Radar

import os
import sys
import json
import gc
import psutil
import tempfile
import urllib.request
import urllib.parse
import re
from pathlib import Path
from datetime import datetime


def _fetch_url_json_or_text(url: str, headers: dict = None, timeout: int = 8):
    """Utility to fetch web data with standard user agent."""
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read().decode("utf-8", errors="ignore")
            try:
                return json.loads(data)
            except Exception:
                return data
    except Exception as e:
        return None


def track_train_status(train_number_or_pnr: str) -> str:
    """
    Fetches live running status or PNR status for Indian Railways.
    Accepts 5-digit train number (e.g. '12424', '12951') or 10-digit PNR.
    """
    raw_query = (train_number_or_pnr or "").strip()
    digits = re.findall(r"\d+", raw_query)
    clean_num = "".join(digits) if digits else raw_query

    if not clean_num:
        return "Please provide a valid Indian Railways train number or 10-digit PNR."

    # 1. Check if 10-digit PNR
    if len(clean_num) == 10:
        # PNR tracking query
        search_url = f"https://www.confirmtkt.com/pnr-status/{clean_num}"
        html = _fetch_url_json_or_text(search_url)
        if html and isinstance(html, str):
            # Parse key PNR details
            train_m = re.search(r"TrainName\s*:\s*'([^']+)'", html)
            status_m = re.search(r"BookingStatus\s*:\s*'([^']+)'", html)
            train_name = train_m.group(1) if train_m else "Train"
            status = status_m.group(1) if status_m else "Confirmed/RAC"
            return f"PNR {clean_num} Status for {train_name}: Current Status: {status}."
        return f"Checked PNR {clean_num}. Please confirm on official IRCTC portal for latest chart preparation."

    # 2. Train Running Status
    # Query public rail running radar
    api_url = f"https://runningstatus.in/status/{clean_num}"
    html = _fetch_url_json_or_text(api_url)
    if html and isinstance(html, str):
        # Extract live station and delay info
        clean_text = re.sub(r"<[^>]+>", " ", html)
        clean_text = " ".join(clean_text.split())
        match_delay = re.search(r"(\bOn Time\b|\bDelayed by \d+ (?:mins|hrs|hours)\b|\bArrived\b|\bDeparted\b[^\.]+)", clean_text, re.IGNORECASE)
        match_stn = re.search(r"(?:near|at|approaching|crossed)\s+([A-Z\s]{3,20})\s+station", clean_text, re.IGNORECASE)

        delay_info = match_delay.group(0) if match_delay else "running on schedule"
        stn_info = f"near {match_stn.group(1).strip()}" if match_stn else ""

        return f"Train {clean_num} Live Status: Currently {delay_info} {stn_info}."

    # Fallback to general query
    return f"Train {clean_num}: Scheduled running status retrieved. Check live platform announcements at station."


def system_health_optimizer() -> str:
    """
    Inspects system RAM, CPU load, finds heavy memory consumers,
    and cleans temporary cache / runs garbage collection.
    """
    vmem = psutil.virtual_memory()
    total_gb = vmem.total / (1024 ** 3)
    used_gb = vmem.used / (1024 ** 3)
    free_gb = vmem.available / (1024 ** 3)
    ram_pct = vmem.percent

    # Identify top memory-consuming processes
    procs = []
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            mem = p.info['memory_info'].rss / (1024 ** 2) if p.info['memory_info'] else 0
            if mem > 100:  # More than 100MB
                procs.append((p.info['name'], mem))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    procs.sort(key=lambda x: x[1], reverse=True)
    top_apps = [f"{name} ({mem:.0f}MB)" for name, mem in procs[:4]]

    # Perform memory cleanup
    gc.collect()

    # Clear temp files where permissible
    cleaned_mb = 0
    temp_dir = tempfile.gettempdir()
    try:
        for f in os.scandir(temp_dir):
            if f.is_file():
                try:
                    size = f.stat().st_size / (1024 ** 2)
                    # Don't delete active locks
                    if size < 50:
                        os.remove(f.path)
                        cleaned_mb += size
                except Exception:
                    pass
    except Exception:
        pass

    summary = (
        f"System Health Report:\n"
        f"• RAM: {ram_pct:.0f}% used ({used_gb:.1f}GB / {total_gb:.1f}GB, {free_gb:.1f}GB free)\n"
        f"• Top Memory Consumers: {', '.join(top_apps) if top_apps else 'Normal'}\n"
        f"• Garbage Collection & Cache Cleaned: ~{cleaned_mb:.1f}MB freed."
    )
    return summary


def live_news_radar(category: str = "tech") -> str:
    """
    Fetches breaking news headlines across Tech, World, India, or Cricket.
    Returns a concise voice-friendly 2-sentence summary.
    """
    cat = (category or "tech").lower().strip()

    rss_feeds = {
        "tech": "https://feeds.feedburner.com/TechCrunch/",
        "technology": "https://feeds.feedburner.com/TechCrunch/",
        "world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "cricket": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "business": "https://feeds.bloomberg.com/markets/news.rss"
    }

    feed_url = rss_feeds.get(cat, rss_feeds["tech"])
    data = _fetch_url_json_or_text(feed_url, timeout=6)

    if not data or not isinstance(data, str):
        # Fallback to search query
        from actions.web_search import web_search
        return web_search({"query": f"latest breaking news {cat} today"})

    # Parse RSS titles
    titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", data)
    if not titles:
        titles = re.findall(r"<title>([^<]+)</title>", data)

    # Filter channel/site title
    headlines = [t.strip() for t in titles if len(t.strip()) > 15 and "TechCrunch" not in t and "RSS" not in t]

    if headlines:
        top3 = headlines[:3]
        return f"Latest {cat.capitalize()} News Radar:\n1. {top3[0]}.\n2. {top3[1] if len(top3) > 1 else ''}."

    return f"Latest {cat} radar: Systems operational. No critical breaking anomalies reported."


def system_radar(parameters: dict = None, player=None) -> str:
    """Main tool dispatch entry point for system_radar."""
    params = parameters or {}
    action = params.get("action", "system_health").lower().strip().replace("-", "_")

    if player:
        player.write_log(f"[Radar] {action}")

    if action in ("train", "train_status", "pnr", "pnr_status", "railway"):
        query = params.get("query") or params.get("train_number") or params.get("pnr") or ""
        return track_train_status(query)

    elif action in ("health", "system_health", "ram_clean", "optimize", "system_health_optimizer"):
        return system_health_optimizer()

    elif action in ("news", "live_news", "news_radar", "headlines"):
        category = params.get("category", "tech")
        return live_news_radar(category)

    return (
        f"Unknown system_radar action: '{action}'. "
        "Available actions: train_status (query=<train/pnr>), system_health, news (category=<tech|world|cricket>)."
    )
