# actions/media_streamer.py
# INDUS Universal Autonomous Media & Series Streaming Engine
# Streams movies, anime, cartoons, serials (e.g. Taarak Mehta), and web series with persistent source learning

import os
import sys
import re
import webbrowser
import urllib.parse
from pathlib import Path

from memory.db_engine import db_get_category_facts, db_set_fact, db_get_fact_by_category


# Direct official show URLs for Sony LIV & Hotstar
SONY_LIV_SHOWS = {
    "taarak mehta": "https://www.sonyliv.com/shows/taarak-mehta-ka-ooltah-chashmah-1700000084",
    "tarak mehta": "https://www.sonyliv.com/shows/taarak-mehta-ka-ooltah-chashmah-1700000084",
    "tmkoc": "https://www.sonyliv.com/shows/taarak-mehta-ka-ooltah-chashmah-1700000084",
    "cid": "https://www.sonyliv.com/shows/c-i-d--1700000066",
    "c.i.d": "https://www.sonyliv.com/shows/c-i-d--1700000066",
    "crime patrol": "https://www.sonyliv.com/shows/crime-patrol-1700000087",
    "kapil sharma": "https://www.sonyliv.com/shows/the-kapil-sharma-show-1700000083",
    "the kapil sharma show": "https://www.sonyliv.com/shows/the-kapil-sharma-show-1700000083",
    "kaun banega crorepati": "https://www.sonyliv.com/shows/kaun-banega-crorepati-1700000086",
    "kbc": "https://www.sonyliv.com/shows/kaun-banega-crorepati-1700000086",
    "wagle ki duniya": "https://www.sonyliv.com/shows/wagle-ki-duniya-1700000570",
    "pushpa impossible": "https://www.sonyliv.com/shows/pushpa-impossible-1700000922",
    "baalveer": "https://www.sonyliv.com/shows/baalveer-3-1700001096",
}

HOTSTAR_SHOWS = {
    "anupama": "https://www.hotstar.com/in/shows/anupama/1260022017",
    "anupamaa": "https://www.hotstar.com/in/shows/anupama/1260022017",
    "yeh rishta": "https://www.hotstar.com/in/shows/yeh-rishta-kya-kehlata-hai/586",
}


def save_media_source_preference(keyword_or_title: str, url_or_platform: str) -> str:
    """
    Saves user instructions like 'Anime hamesha site X se dikhana' or
    'Taarak Mehta SonyLIV se play karna' into permanent SQLite memory.
    """
    key = (keyword_or_title or "").lower().strip().replace(" ", "_")
    val = (url_or_platform or "").strip()

    if not key or not val:
        return "Please provide both the keyword/show title and the target platform or URL."

    db_set_fact(category="media_sources", key=key, value=val)
    print(f"[MediaStreamer] [!] Saved persistent media source: {key} -> {val}")
    return f"Preference saved: For '{keyword_or_title}', INDUS will always stream from '{val}'."


def _get_preferred_source(title: str, media_type: str = "") -> str | None:
    """Checks SQLite memory for user-defined media streaming sources."""
    sources = db_get_category_facts("media_sources")
    if not sources:
        return None

    t_lower = (title or "").lower().strip().replace(" ", "_")
    m_lower = (media_type or "").lower().strip().replace(" ", "_")

    # 1. Exact match on title or media_type
    if t_lower in sources:
        return sources[t_lower]
    if m_lower in sources:
        return sources[m_lower]

    # 2. Substring matching
    for k, v in sources.items():
        if k in t_lower or t_lower in k or (m_lower and k in m_lower):
            return v

    return None


def stream_content(title: str, media_type: str = "auto", custom_url: str = "", player=None) -> str:
    """
    Autonomously searches and streams movies, anime, serials, and shows:
    1. Checks saved SQLite source preferences first.
    2. Uses direct show mappings (SonyLIV, Hotstar) or official YouTube HD streaming.
    3. Handles anime via specialized fast streamers (HiAnime / Kaido).
    """
    clean_title = (title or "").strip()
    if not clean_title and not custom_url:
        return "Please specify the name of the show, movie, anime, or video you would like to stream."

    # Direct custom URL override
    if custom_url:
        webbrowser.open(custom_url)
        return f"Streaming directly from: {custom_url}"

    t_lower = clean_title.lower()

    # 1. Check for stored persistent preference
    pref_source = _get_preferred_source(clean_title, media_type)
    target_site = ""
    direct_url = ""

    if pref_source:
        if pref_source.startswith("http://") or pref_source.startswith("https://"):
            direct_url = pref_source
        else:
            target_site = pref_source.lower().strip()
        print(f"[MediaStreamer] [!] Using saved source preference: {pref_source} for '{clean_title}'")

    # 2. Direct show URL mapping if Sony LIV or Hotstar
    if not direct_url:
        if target_site in ("sony_liv", "sonyliv") or "sony" in t_lower:
            for show_key, show_url in SONY_LIV_SHOWS.items():
                if show_key in t_lower:
                    direct_url = show_url
                    break

        elif target_site in ("hotstar", "disney") or "hotstar" in t_lower:
            for show_key, show_url in HOTSTAR_SHOWS.items():
                if show_key in t_lower:
                    direct_url = show_url
                    break

    # If direct official show URL is resolved, open directly in system default browser
    if direct_url:
        if player:
            player.write_log(f"[Streamer] Opening direct URL: {direct_url}")
        webbrowser.open(direct_url)
        return f"Streaming '{clean_title}' on official page: {direct_url}"

    # 3. Anime streaming (HiAnime / Kaido)
    if "anime" in media_type.lower() or any(a in t_lower for a in ["naruto", "one piece", "dragon ball", "jujutsu", "attack on titan", "demon slayer", "bleach", "death note", "solo leveling"]):
        anime_query = re.sub(r"\b(anime|stream|watch|play|episode)\b", "", clean_title, flags=re.IGNORECASE).strip()
        anime_url = f"https://hianime.to/search?keyword={urllib.parse.quote_plus(anime_query or clean_title)}"
        webbrowser.open(anime_url)
        if player:
            player.write_log(f"[Streamer] Anime search: {anime_query or clean_title}")
        return f"Streaming anime '{clean_title}' on HiAnime."

    # 4. Indian Serials (TMKOC, CID, etc.)
    # If user explicitly asked for SonyLIV without direct map, open SonyLIV search in browser
    if target_site in ("sony_liv", "sonyliv") or "sony liv" in t_lower or "sonyliv" in t_lower:
        # Check if known Sony LIV show
        for show_key, show_url in SONY_LIV_SHOWS.items():
            if show_key in t_lower:
                webbrowser.open(show_url)
                return f"Streaming '{clean_title}' on Sony LIV: {show_url}"
        # Fallback to Sony LIV search
        sony_search = f"https://www.sonyliv.com/search?keyword={urllib.parse.quote_plus(clean_title)}"
        webbrowser.open(sony_search)
        return f"Opening '{clean_title}' search on Sony LIV."

    # 5. Default & Highest Reliability: Official YouTube HD Stream with Auto Ad-Skipping
    # For TMKOC, CID, KBC, Songs, Videos, Trailor, etc.
    # Sony SAB / Sony LIV / Zee officially uploads full episodes in 1080p HD on YouTube
    from actions.youtube_video import youtube_video
    yt_query = clean_title
    if any(s in t_lower for s in ["taarak mehta", "tarak mehta", "tmkoc"]):
        yt_query = "Taarak Mehta Ka Ooltah Chashmah latest full episode Sony SAB"
    elif any(s in t_lower for s in ["cid", "c.i.d"]):
        yt_query = "CID latest full episode Sony PAL"
    elif "crime patrol" in t_lower:
        yt_query = "Crime Patrol latest full episode SET India"
    elif "kapil sharma" in t_lower:
        yt_query = "The Kapil Sharma Show full episode Sony LIV"

    return youtube_video(
        parameters={"action": "play_and_skip_ad", "query": yt_query},
        player=player
    )


def media_streamer(parameters: dict = None, player=None) -> str:
    """Main tool dispatch entry point for media_streamer."""
    params = parameters or {}
    action = params.get("action", "stream").lower().strip()
    title = params.get("title") or params.get("query") or params.get("name") or ""
    media_type = params.get("media_type") or params.get("type") or "auto"
    custom_url = params.get("custom_url") or params.get("url") or ""

    if player:
        player.write_log(f"[Streamer] {action} {title[:25]}")

    if action in ("save_preference", "save_source", "set_preference", "remember_source"):
        source = params.get("url_or_platform") or params.get("source") or params.get("url") or ""
        return save_media_source_preference(keyword_or_title=title, url_or_platform=source)

    return stream_content(title=title, media_type=media_type, custom_url=custom_url, player=player)

