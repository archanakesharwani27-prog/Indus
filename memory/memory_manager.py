# memory/memory_manager.py
# INDUS MEMORY MANAGER - Full Permanent Memory & Behavioral Habit Engine

import json
import re
import sys
from datetime import datetime
from threading import Lock
from pathlib import Path

from memory.db_engine import (
    db_save_conversation, db_get_recent_conversations,
    db_search_conversations, db_set_fact, db_set_facts_batch, db_get_all_facts,
    db_get_fact, db_delete_fact, db_record_app_launch,
    db_get_frequent_apps, db_set_rule
)


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
MEMORY_PATH      = BASE_DIR / "memory" / "long_term.json"
_lock            = Lock()


def _empty_memory() -> dict:
    return {
        "identity":      {},
        "preferences":   {},
        "habits":        {},
        "auto_actions":  {},
        "projects":      {},
        "relationships": {},
        "wishes":        {},
        "notes":         {}
    }


def load_memory() -> dict:
    facts = db_get_all_facts()
    if facts and any(facts.values()):
        return facts

    if not MEMORY_PATH.exists():
        return _empty_memory()

    with _lock:
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                for key in base:
                    if key not in data:
                        data[key] = {}
                db_set_facts_batch(data)
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[Memory] Load error: {e}")
            return _empty_memory()


def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return

    db_set_facts_batch(memory)

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            MEMORY_PATH.write_text(
                json.dumps(memory, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[Memory] JSON write error: {e}")


_CREDENTIAL_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE),
    re.compile(r"sk-[0-9A-Za-z\-_]{20,}", re.IGNORECASE),
    re.compile(r"nvapi-[0-9A-Za-z\-_]{20,}", re.IGNORECASE),
    re.compile(r"gsk_[0-9A-Za-z\-_]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
]


def is_sensitive_credential(key: str, val: str) -> bool:
    k_lower = str(key).lower()
    if any(s in k_lower for s in ["api_key", "apikey", "password", "secret", "private_key", "auth_token", "pin"]):
        return True
    combined = f"{key} {val}"
    return any(p.search(combined) for p in _CREDENTIAL_PATTERNS)


def update_memory(memory_update: dict) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()

    memory = load_memory()
    sanitized_keys = []
    for cat, items in memory_update.items():
        if cat not in memory or not isinstance(memory[cat], dict):
            memory[cat] = {}
        if isinstance(items, dict):
            for k, v in items.items():
                if isinstance(v, dict) and "value" in v:
                    val = str(v["value"])
                else:
                    val = str(v)
                # Security: never store raw API keys or passwords in general memory
                if is_sensitive_credential(k, val):
                    print(f"[MemorySecurity] Blocked credential storage for key '{k}'")
                    continue
                entry = {"value": val, "updated": datetime.now().strftime("%Y-%m-%d")}
                memory[cat][k] = entry
                db_set_fact(cat, k, val)
                sanitized_keys.append(k)

    save_memory(memory)
    if sanitized_keys:
        print(f"[Memory] Permanent Memory Updated: {sanitized_keys}")
        # Publish to EventBus (best-effort, never blocks memory write)
        try:
            from core.event_bus import event_bus, E
            event_bus.publish(E.MEMORY_UPDATE, source="memory_manager",
                              data={"keys": sanitized_keys})
        except Exception:
            pass
    return memory



def record_conversation_turn(user_text: str, indus_text: str, intent: str = "", summary: str = "") -> None:
    db_save_conversation(user_text, indus_text, intent, summary)


def should_extract_memory(user_text: str, jarvis_text: str, api_key: str = "") -> bool:
    """
    Fast keyword-only memory relevance check. No API calls — instant and rate-limit-free.
    Returns True if this conversation likely contains something worth remembering.
    """
    u_lower = (user_text or "").lower()

    # Personal identity and facts
    identity_keywords = [
        "mera naam", "my name", "i am", "main hoon", "i'm",
        "i live in", "main rehta", "main rehti", "mujhe pasand",
        "meri age", "my age", "meri birthday", "my birthday",
        "meri city", "mera city", "i work", "main kaam karta", "main kaam karti",
    ]
    # Preferences and settings
    preference_keywords = [
        "dark mode", "light mode", "theme", "pasand hai", "like", "prefer",
        "hamesha", "always", "har baar", "every time",
        "default", "favourite", "favorite", "best",
    ]
    # Shopping profile
    shopping_keywords = [
        "size", "shirt size", "shoe size", "pant size", "waist",
        "budget", "brand", "preferred brand", "mera size",
    ]
    # App and media habits
    habit_keywords = [
        "open youtube", "open vs code", "open notepad", "open whatsapp",
        "jab bhi open", "every time open", "startup mein",
        "music", "song", "anime", "serial", "movie",
    ]
    # Project and goals
    project_keywords = [
        "project", "working on", "kaam kar raha", "kaam kar rahi",
        "build kar", "develop kar", "create kar", "goal",
    ]

    all_keywords = identity_keywords + preference_keywords + shopping_keywords + habit_keywords + project_keywords

    if any(k in u_lower for k in all_keywords):
        return True

    # Also extract if user text is a clear statement (not a question) with personal pronoun
    personal_starters = ["mera", "meri", "mere", "main ", "i am", "i have", "my ", "mine"]
    if any(u_lower.startswith(s) for s in personal_starters) and len(user_text) > 15:
        return True

    return False


def extract_memory(user_text: str, jarvis_text: str, api_key: str = "") -> dict:
    extracted = {}
    u_lower = (user_text or "").lower()

    if "dark mode" in u_lower and any(w in u_lower for w in ["pasand", "enable", "on", "karo", "use", "prefer", "work"]):
        extracted.setdefault("preferences", {})["theme"] = {"value": "dark"}
        db_set_rule("dark_mode_auto", "theme", {"theme": "dark"}, enabled=True)

    if "light mode" in u_lower and any(w in u_lower for w in ["pasand", "enable", "on", "prefer"]):
        extracted.setdefault("preferences", {})["theme"] = {"value": "light"}

    try:
        from or_client import client as or_c
        combined = f"User: {user_text[:600]}\nIndus: {jarvis_text[:300]}"
        raw = or_c.chat(
            "Extract ALL memorable personal facts, preferences, projects, relationships, or identity details from this conversation.\nReturn ONLY valid JSON. Categories: identity, preferences, habits, projects, relationships, wishes, notes.\nEnsure theme preferences (dark/light) are stored in preferences/theme.\nFormat:\n{\n  \"preferences\": {\"theme\": {\"value\": \"dark\"}}\n}\n\nConversation:\n" + combined + "\n\nJSON:",
            system="Return ONLY valid JSON. No markdown fences, no explanation, no extra text.",
            max_tokens=1024,
            temperature=0.1
        )
        clean = raw.strip()
        clean = re.sub(r"```(?:json)?", "", clean).strip().rstrip("`").strip()
        if clean and clean != "{}":
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                for cat, items in parsed.items():
                    if isinstance(items, dict):
                        extracted.setdefault(cat, {}).update(items)
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] LLM extract exception: {e}")

    return extracted


def format_memory_for_prompt(memory: dict | None) -> str:
    if not memory:
        memory = load_memory()

    lines = []

    identity  = memory.get("identity", {})
    id_fields = ["name", "age", "birthday", "city", "job", "language", "school", "nationality"]
    for field in id_fields:
        entry = identity.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.title()}: {val}")
    for key, entry in identity.items():
        if key in id_fields:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")

    prefs = memory.get("preferences", {})
    if prefs:
        lines.append("")
        lines.append("Preferences & Settings:")
        for key, entry in list(prefs.items())[:20]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    projects = memory.get("projects", {})
    if projects:
        lines.append("")
        lines.append("Active Projects / Goals:")
        for key, entry in list(projects.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    for section_name, cat in [("People in Life", "relationships"), ("Wishes / Plans", "wishes"), ("Notes", "notes")]:
        sec_data = memory.get(cat, {})
        if sec_data:
            lines.append("")
            lines.append(f"{section_name}:")
            for key, entry in list(sec_data.items())[:8]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    # Inject recent conversation history from SQLite so INDUS remembers what was discussed across sessions
    recent_convs = db_get_recent_conversations(30)

    if recent_convs:
        lines.append("")
        lines.append("[PREVIOUS CONVERSATION HISTORY FROM PAST SESSIONS - YOU REMEMBER ALL OF THIS]")
        for c in recent_convs:
            ts = c.get("timestamp", "")[:19]
            u_text = c.get("user_text", "").strip()
            ind_text = (c.get("indus_text") or c.get("jarvis_text") or "").strip()
            if u_text:
                lines.append(f"* [{ts}] User: {u_text}")
                if ind_text:
                    lines.append(f"  INDUS: {ind_text[:120]}")

    if not lines:
        return ""

    header = "[INDUS PERMANENT LONG-TERM MEMORY & CONVERSATION HISTORY - Always remember and recall accurately]\n"
    return header + "\n".join(lines) + "\n\n"


def remember(key: str, value: str, category: str = "notes") -> str:
    if is_sensitive_credential(key, value):
        return f"[Security] Credentials or API keys cannot be stored in long-term memory."
    update_memory({category: {key: {"value": value}}})
    db_set_fact(category, key, value)
    return f"Remembered permanently: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    k_clean = str(key).strip().lower()
    db_delete_fact(k_clean)
    memory = load_memory()

    deleted_from = []
    # 1. Try specified category
    if category in memory and isinstance(memory[category], dict):
        if k_clean in memory[category]:
            del memory[category][k_clean]
            deleted_from.append(category)

    # 2. Search all categories to ensure complete purge of fact/preference
    for cat_name, cat_dict in list(memory.items()):
        if isinstance(cat_dict, dict) and k_clean in cat_dict:
            del cat_dict[k_clean]
            if cat_name not in deleted_from:
                deleted_from.append(cat_name)

    save_memory(memory)
    if deleted_from:
        return f"Forgotten '{key}' from: {', '.join(deleted_from)}"
    return f"Forgotten fact '{key}'."


def recall_memory(query: str = "", category: str = "") -> str:
    """Search profile facts, user identity, preferences, and notes."""
    all_facts = load_memory()
    if not query and not category:
        return format_memory_for_prompt(all_facts)

    query_lower = query.lower().strip()
    matches = []

    for cat_name, cat_dict in all_facts.items():
        if category and cat_name.lower() != category.lower():
            continue
        if isinstance(cat_dict, dict):
            for k, val_entry in cat_dict.items():
                val = val_entry.get("value") if isinstance(val_entry, dict) else str(val_entry)
                if not query_lower or query_lower in k.lower() or query_lower in str(val).lower():
                    matches.append(f"[{cat_name.title()}] {k.replace('_', ' ').title()}: {val}")

    if matches:
        return "Found in memory:\n" + "\n".join(matches)
    return f"No memory entries found for '{query}'."


def search_conversation_history(query: str = "", limit: int = 15) -> str:
    """
    Search past conversation turns from SQLite database with full date, time, and session context.
    Handles generic requests ('previous conversation', 'pichli baatein', 'what did we talk about'),
    relative/absolute date queries ('yesterday', 'kal', '2026-08-25'), and topic queries.
    """
    recent = db_search_conversations(query, limit)

    if not recent:
        return f"No past conversations found matching '{query}'."

    lines = [f"Found {len(recent)} conversation turn(s) in memory:"]
    for c in recent:
        ts = c.get("timestamp", "")
        day = c.get("day_name", "")
        date_str = c.get("date", "")
        time_str = c.get("time_str", "")
        sess = c.get("session_id", "")
        u = c.get("user_text", "")
        i = c.get("indus_text", "") or c.get("jarvis_text", "")

        header_parts = []
        if day and date_str:
            header_parts.append(f"{day}, {date_str}")
        elif ts:
            header_parts.append(ts)
        if time_str:
            header_parts.append(time_str)

        time_header = " | ".join(header_parts) or ts
        lines.append(f"- [{time_header}] User: {u}")
        if i:
            lines.append(f"  INDUS: {i[:250]}")
    return "\n".join(lines)


def flush_memory_on_shutdown() -> None:
    """
    Called on system exit/close: flushes all memory caches and state to SQLite/JSON in < 20ms.
    """
    try:
        mem = load_memory()
        save_memory(mem)
        print("[Memory] Long-term memory and conversation history flushed to SQLite on shutdown.")
    except Exception as e:
        print(f"[Memory] Shutdown flush error: {e}")


forget_memory = forget



def get_preference(key: str, default: str = None) -> str | None:
    fact = db_get_fact(key)
    if fact:
        return fact
    memory = load_memory()
    prefs  = memory.get("preferences", {})
    entry  = prefs.get(key)
    if entry and isinstance(entry, dict):
        return entry.get("value", default)
    return default


def set_preference(key: str, value: str) -> None:
    db_set_fact("preferences", key, value)
    update_memory({"preferences": {key: {"value": value}}})


def record_app_launch(app_name: str) -> None:
    if not app_name:
        return
    db_record_app_launch(app_name)


def get_startup_habits(min_launches: int = 3) -> list:
    return db_get_frequent_apps(min_count=min_launches)


def enforce_user_preferences() -> list:
    actions_taken = []
    pref = db_get_fact("theme") or db_get_fact("theme_preference")

    if pref:
        theme_pref = None
        pref_lower = pref.lower()
        if "dark" in pref_lower:
            theme_pref = "dark"
        elif "light" in pref_lower:
            theme_pref = "light"

        if theme_pref:
            try:
                from actions.computer_settings import get_theme_mode, set_theme_mode
                current_theme = get_theme_mode()
                if current_theme != theme_pref:
                    res = set_theme_mode(theme_pref)
                    actions_taken.append(f"Auto-enforced {theme_pref.capitalize()} Mode: {res}")
                    print(f"[MemoryEnforce] {res}")
            except Exception as e:
                print(f"[MemoryEnforce] Theme error: {e}")

    return actions_taken
