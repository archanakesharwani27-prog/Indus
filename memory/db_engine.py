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

def init_db():
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_text TEXT NOT NULL,
                indus_text TEXT NOT NULL,
                intent TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                tags TEXT DEFAULT ''
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
        conn.commit()
        conn.close()

init_db()

def db_save_conversation(user_text: str, indus_text: str, intent: str = "", summary: str = "", tags: str = "") -> None:
    if not user_text and not indus_text:
        return
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO conversations (timestamp, user_text, indus_text, intent, summary, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (now_str, user_text.strip(), indus_text.strip(), intent, summary, tags)
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
                "SELECT timestamp, user_text, indus_text, intent, summary FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in reversed(rows)]
        except Exception as e:
            print(f"[DB] Error getting recent conversations: {e}")
            return []

def db_search_conversations(query: str, limit: int = 10) -> list:
    with _db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute(
                "SELECT timestamp, user_text, indus_text, summary FROM conversations WHERE user_text LIKE ? OR indus_text LIKE ? ORDER BY id DESC LIMIT ?",
                (search_pattern, search_pattern, limit)
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
