# actions/deep_research.py
# INDUS Deep Research Engine (IRIS-style)
# Primary: DuckDuckGo multi-search | Optional: Tavily
import json, re, sys
from pathlib import Path

def _get_base_dir():
    if getattr(sys, "frozen", False): return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()

def _load_tavily_key():
    try:
        with open(BASE_DIR / "config" / "api_keys.json", encoding="utf-8") as f:
            return json.load(f).get("tavily_api_key", "")
    except Exception:
        return ""

CATEGORY_SUFFIXES = {
    "sports": "latest score results standings 2025",
    "cricket": "cricket match score wickets runs 2025",
    "ipl": "IPL 2025 points table standings",
    "football": "football match result goal scorer 2025",
    "movies": "movie release date cast 2025",
    "games": "game release date platforms 2025",
    "tech": "comparison specifications benchmark 2025",
    "ai": "AI model benchmark parameters performance 2025",
    "news": "latest news today India 2025",
    "general": "",
}

def _ddg_search(query, max_results=5):
    """Robust DuckDuckGo web search scraper — zero key required."""
    try:
        import requests
        import html as html_lib
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=headers, timeout=8)
        if r.status_code == 200:
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
            results = []
            for s in snippets[:max_results]:
                clean = re.sub(r"<[^>]+>", "", s).strip()
                clean = html_lib.unescape(clean)
                if clean:
                    results.append({"snippet": clean})
            if results:
                return results
    except Exception as e:
        print(f"[Research] DDG scraper error: {e}")
    return []

def _gemini_deep_search(query: str, domain: str) -> str:
    """Use Gemini 2.5 Flash with Google Search Grounding for real-time live research."""
    try:
        from google import genai
        with open(BASE_DIR / "config" / "api_keys.json", "r", encoding="utf-8") as f:
            api_key = json.load(f).get("gemini_api_key", "")
        if not api_key:
            return ""

        client = genai.Client(api_key=api_key)
        system_instruction = (
            "You are INDUS Deep Research Assistant. "
            "Given a live research query, synthesize the real-time facts into a crisp, concise 2 to 3 sentence "
            "spoken executive summary in natural conversational Hinglish. "
            "Include specific numbers, match scores/standings, release dates, or benchmark statistics where available. "
            "Do NOT include citations, URLs, or markdown headings. State the facts clearly."
        )

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=f"Domain: {domain}. Research topic: {query}",
            config={
                "system_instruction": system_instruction,
                "tools": [{"google_search": {}}],
                "temperature": 0.3,
            },
        )

        text = ""
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
        return text.strip()
    except Exception as e:
        print(f"[Research] Gemini Grounded Search error: {e}")
        return ""


def _synthesize(query, domain, snippets, direct_answer=""):
    from or_client import client
    combined = ""
    if direct_answer: combined += f"Direct Answer: {direct_answer}\n\n"
    for i, s in enumerate(snippets[:4]): combined += f"Source {i+1}: {s.get('snippet','')}\n"
    if not combined.strip():
        return f"'{query}' ke baare mein koi relevant real-time information nahi mili."
    prompt = (
        f"Research query: '{query}' (category: {domain})\n\nSearch results:\n{combined}\n\n"
        "Synthesize into a crisp 2-3 sentence spoken summary in natural Hinglish. "
        "Include key numbers, dates, scores. Do NOT mention sources or URLs."
    )
    try:
        return client.chat(prompt, system="You are INDUS research assistant. Give 2-3 sentence factual Hinglish summaries with numbers and specifics.", max_tokens=200, temperature=0.3).strip()
    except Exception:
        if direct_answer: return direct_answer[:300]
        return snippets[0].get("snippet","Research unavailable.")[:300] if snippets else "No results found."


def deep_research(query: str, domain: str = "general", player=None) -> str:
    """
    IRIS-style real-time research engine.
    Fetches real-time structured facts for sports, games/movie release dates, tech benchmarks,
    and returns a concise 2-3 sentence executive spoken summary.
    """
    if player: player.write_log(f"[Research] {query} [{domain}]")
    print(f"[Research] Starting deep_research for: '{query}' [{domain}]")

    try:
        from core.cancellation import cancellation_manager
    except Exception:
        cancellation_manager = None

    if cancellation_manager and cancellation_manager.is_cancelled():
        return "Research operation was cancelled."

    # 1. Try Tavily API if configured
    key = _load_tavily_key()
    if key:
        suffix = CATEGORY_SUFFIXES.get(domain.lower(), "")
        search_query = f"{query} {suffix}".strip()
        snippets, direct_answer = _tavily_search(search_query, key)
        if snippets or direct_answer:
            if cancellation_manager and cancellation_manager.is_cancelled():
                return "Research operation was cancelled."
            return _synthesize(query, domain, snippets, direct_answer)

    if cancellation_manager and cancellation_manager.is_cancelled():
        return "Research operation was cancelled."

    # 2. Google Grounded Search (Gemini 2.5 Flash with live web)
    gemini_summary = _gemini_deep_search(query, domain)
    if gemini_summary:
        if player: player.write_log(f"[Research] Done: {gemini_summary[:50]}...")
        return gemini_summary

    if cancellation_manager and cancellation_manager.is_cancelled():
        return "Research operation was cancelled."

    # 3. DuckDuckGo multi-search fallback
    suffix = CATEGORY_SUFFIXES.get(domain.lower(), "")
    search_query = f"{query} {suffix}".strip()
    snippets = _ddg_search(search_query)
    return _synthesize(query, domain, snippets, "")


