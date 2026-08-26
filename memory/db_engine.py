# memory/db_engine.py
# INDUS PERMANENT LONG-TERM MEMORY DATABASE (SQLite Engine)

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
DB_DIR = BASE_DIR / "memory"
DB_PATH = DB_DIR / "indus_memory.db"
_db_lock = Lock()

def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

CURRENT_SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

GENERIC_HISTORY_PHRASES = [
    "previous conversation", "pichli conversation", "past conversation",
    "last conversation", "previous session", "pichla session", "last session",
    "recent chats", "history", "kya baatein hui thi", "kya baat kri thi",
    "kya baat hui thi", "all conversations", "purani baatein", "pehle kya baat",
    "what did we talk about", "what were we talking about", "previous chats",
    "conversation history", "chat history", "pichli baatein", "pehle wali baat",
]


def is_generic_history_query(q: str) -> bool:
    if not q or not q.strip():
        return True
    q_low = q.lower().strip()
    return any(phrase in q_low or q_low in phrase for phrase in GENERIC_HISTORY_PHRASES)


def init_db():
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT DEFAULT '',
                date TEXT DEFAULT '',
                time_str TEXT DEFAULT '',
                day_name TEXT DEFAULT '',
                year TEXT DEFAULT '',
                month TEXT DEFAULT '',
                user_text TEXT NOT NULL,
                indus_text TEXT NOT NULL,
                intent TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                tags TEXT DEFAULT ''
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'direct',
                last_updated TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL UNIQUE,
                launch_count INTEGER DEFAULT 1,
                last_launched TEXT NOT NULL,
                usual_hours TEXT DEFAULT '[]',
                is_startup_habit INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS autonomous_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL UNIQUE,
                rule_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_triggered TEXT DEFAULT '',
                trigger_count INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS autonomous_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_name TEXT NOT NULL,
                details TEXT NOT NULL,
                status TEXT NOT NULL
            )
        ''')

        # Auto-migrate columns if table already existed
        cursor.execute("PRAGMA table_info(conversations)")
        cols = [row[1] for row in cursor.fetchall()]
        new_cols = {
            "session_id": "TEXT DEFAULT ''",
            "date": "TEXT DEFAULT ''",
            "time_str": "TEXT DEFAULT ''",
            "day_name": "TEXT DEFAULT ''",
            "year": "TEXT DEFAULT ''",
            "month": "TEXT DEFAULT ''",
        }
        for col_name, col_type in new_cols.items():
            if col_name not in cols:
                try:
                    cursor.execute(f"ALTER TABLE conversations ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        conn.commit()
        conn.close()

init_db()


# ── Cumulative System Uptime Management ─────────────────────────────────────

def db_get_cumulative_uptime() -> float:
    """Retrieve cumulative system uptime in seconds across all sessions."""
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_state WHERE key = 'cumulative_uptime_seconds'")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return float(row[0])
        except Exception as e:
            print(f"[DB] Error getting cumulative uptime: {e}")
    return 0.0


def db_save_cumulative_uptime(uptime_seconds: float) -> None:
    """Persist cumulative system uptime in seconds to SQLite system_state."""
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO system_state (key, value, updated_at)
                VALUES ('cumulative_uptime_seconds', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (str(uptime_seconds), now_str))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error saving cumulative uptime: {e}")


# ── Conversation Turn Storage & Search ──────────────────────────────────────

def db_save_conversation(
    user_text: str,
    indus_text: str,
    intent: str = "",
    summary: str = "",
    tags: str = "",
    session_id: str = "",
) -> None:
    if not user_text and not indus_text:
        return
    sess = session_id or CURRENT_SESSION_ID
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    day_name = now.strftime("%A")
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO conversations (
                    timestamp, session_id, date, time_str, day_name, year, month,
                    user_text, indus_text, intent, summary, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now_str, sess, date_str, time_str, day_name, year_str, month_str,
                    user_text.strip(), indus_text.strip(), intent, summary, tags
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error saving conversation: {e}")


def db_get_recent_conversations(limit: int = 20) -> list:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT timestamp, session_id, date, time_str, day_name, year, month,
                          user_text, indus_text, intent, summary
                   FROM conversations ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in reversed(rows)]
        except Exception as e:
            print(f"[DB] Error getting recent conversations: {e}")
            return []


def db_search_conversations(query: str = "", limit: int = 15) -> list:
    """
    Intelligent conversation search supporting:
    1. Generic history requests ('previous conversation', 'pichli baatein') -> returns recent chronological turns
    2. Relative/Absolute date queries ('yesterday', 'kal', '2026-08-25') -> filters by date
    3. Topic / Keyword queries ('WO Mic', 'volume', 'python') -> matches text or summary
    """
    from datetime import timedelta

    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            q_clean = (query or "").strip()

            # 1. Generic History Query
            if is_generic_history_query(q_clean):
                cursor.execute(
                    """SELECT id, timestamp, session_id, date, time_str, day_name,
                              user_text, indus_text, intent, summary
                       FROM conversations ORDER BY id DESC LIMIT ?""",
                    (limit,)
                )
                rows = cursor.fetchall()
                conn.close()
                return [dict(r) for r in reversed(rows)]

            # 2. Date Filtering (kal, yesterday, today, YYYY-MM-DD, Month)
            q_low = q_clean.lower()
            date_pat = None
            if "yesterday" in q_low or "kal" in q_low:
                date_pat = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") + "%"
            elif "today" in q_low or "aaj" in q_low:
                date_pat = datetime.now().strftime("%Y-%m-%d") + "%"

            if date_pat:
                cursor.execute(
                    """SELECT id, timestamp, session_id, date, time_str, day_name,
                              user_text, indus_text, intent, summary
                       FROM conversations WHERE timestamp LIKE ? ORDER BY id ASC LIMIT ?""",
                    (date_pat, limit)
                )
                rows = cursor.fetchall()
                if rows:
                    conn.close()
                    return [dict(r) for r in rows]

            # 3. Topic / Keyword matching
            search_pattern = f"%{q_clean}%"
            cursor.execute(
                """SELECT id, timestamp, session_id, date, time_str, day_name,
                          user_text, indus_text, intent, summary
                   FROM conversations
                   WHERE user_text LIKE ? OR indus_text LIKE ? OR summary LIKE ? OR session_id LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (search_pattern, search_pattern, search_pattern, search_pattern, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[DB] Error searching conversations: {e}")
            return []

def db_set_fact(category: str, key: str, value: str, confidence: float = 1.0, source: str = "direct") -> None:
    if not key or not value:
        return
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO user_profile (category, key, value, confidence, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    category = excluded.category,
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    last_updated = excluded.last_updated
            """, (category, key.strip().lower(), str(value).strip(), confidence, source, now_str))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error setting fact: {e}")


def db_set_facts_batch(facts_dict: dict, confidence: float = 1.0, source: str = "direct") -> None:
    """High-speed batch insert/update for all facts in a single SQLite transaction."""
    if not facts_dict or not isinstance(facts_dict, dict):
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params = []
    for cat, items in facts_dict.items():
        if isinstance(items, dict):
            for k, val_entry in items.items():
                val = val_entry.get("value") if isinstance(val_entry, dict) else str(val_entry)
                if k and val:
                    params.append((cat, k.strip().lower(), str(val).strip(), confidence, source, now_str))

    if not params:
        return

    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO user_profile (category, key, value, confidence, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    category = excluded.category,
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    last_updated = excluded.last_updated
            """, params)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error setting facts batch: {e}")

def db_get_all_facts() -> dict:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, value, confidence, last_updated FROM user_profile")
            rows = cursor.fetchall()
            conn.close()

            result = {
                "identity": {},
                "preferences": {},
                "habits": {},
                "projects": {},
                "relationships": {},
                "wishes": {},
                "notes": {}
            }
            for r in rows:
                cat = r["category"]
                if cat not in result:
                    result[cat] = {}
                result[cat][r["key"]] = {
                    "value": r["value"],
                    "confidence": r["confidence"],
                    "updated": r["last_updated"]
                }
            return result
        except Exception as e:
            print(f"[DB] Error getting facts: {e}")
            return {}

def db_get_fact(key: str) -> str:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_profile WHERE key = ?", (key.strip().lower(),))
            row = cursor.fetchone()
            conn.close()
            return row["value"] if row else None
        except Exception as e:
            print(f"[DB] Error getting fact '{key}': {e}")
            return None

def db_get_category_facts(category: str) -> dict:
    """Returns all key-value pairs stored in a given category."""
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_profile WHERE category = ?", (category.strip().lower(),))
            rows = cursor.fetchall()
            conn.close()
            return {r["key"]: r["value"] for r in rows}
        except Exception as e:
            print(f"[DB] Error getting category facts '{category}': {e}")
            return {}

def db_get_fact_by_category(category: str, key: str) -> str | None:
    """Returns a specific fact value under a category."""
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_profile WHERE category = ? AND key = ?", (category.strip().lower(), key.strip().lower()))
            row = cursor.fetchone()
            conn.close()
            return row["value"] if row else None
        except Exception as e:
            print(f"[DB] Error getting fact '{key}' in category '{category}': {e}")
            return None

def db_delete_fact(key: str) -> bool:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profile WHERE key = ?", (key.strip().lower(),))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            print(f"[DB] Error deleting fact '{key}': {e}")
            return False

def db_delete_fact_by_category(category: str, key: str) -> bool:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profile WHERE category = ? AND key = ?", (category.strip().lower(), key.strip().lower()))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            print(f"[DB] Error deleting fact '{key}' in category '{category}': {e}")
            return False


def db_record_app_launch(app_name: str) -> None:
    if not app_name:
        return
    app_clean = app_name.strip().lower()
    current_hour = datetime.now().hour
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT launch_count, usual_hours FROM app_habits WHERE app_name = ?", (app_clean,))
            row = cursor.fetchone()
            if row:
                count = row["launch_count"] + 1
                try:
                    hours = json.loads(row["usual_hours"] or "[]")
                except Exception:
                    hours = []
                hours.append(current_hour)
                hours = hours[-50:]
                is_startup = 1 if count >= 3 else 0
                cursor.execute("""
                    UPDATE app_habits 
                    SET launch_count = ?, last_launched = ?, usual_hours = ?, is_startup_habit = ?
                    WHERE app_name = ?
                """, (count, now_str, json.dumps(hours), is_startup, app_clean))
            else:
                cursor.execute("""
                    INSERT INTO app_habits (app_name, launch_count, last_launched, usual_hours, is_startup_habit)
                    VALUES (?, 1, ?, ?, 0)
                """, (app_clean, now_str, json.dumps([current_hour])))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error recording app launch: {e}")

def db_get_frequent_apps(min_count: int = 3) -> list:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT app_name, launch_count FROM app_habits WHERE launch_count >= ? ORDER BY launch_count DESC",
                (min_count,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [r["app_name"] for r in rows]
        except Exception as e:
            print(f"[DB] Error getting frequent apps: {e}")
            return []

def db_set_rule(rule_name: str, rule_type: str, parameters: dict, enabled: bool = True) -> None:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO autonomous_rules (rule_name, rule_type, parameters, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(rule_name) DO UPDATE SET
                    rule_type = excluded.rule_type,
                    parameters = excluded.parameters,
                    enabled = excluded.enabled
            """, (rule_name, rule_type, json.dumps(parameters), 1 if enabled else 0))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error setting rule: {e}")

def db_get_active_rules() -> list:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autonomous_rules WHERE enabled = 1")
            rows = cursor.fetchall()
            conn.close()
            res = []
            for r in rows:
                item = dict(r)
                try:
                    item["parameters"] = json.loads(item["parameters"])
                except Exception:
                    item["parameters"] = {}
                res.append(item)
            return res
        except Exception as e:
            print(f"[DB] Error getting active rules: {e}")
            return []

def db_log_autonomous_action(action_name: str, details: str, status: str = "success") -> None:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO autonomous_log (timestamp, action_name, details, status) VALUES (?, ?, ?, ?)",
                (now_str, action_name, details, status)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Error logging autonomous action: {e}")
