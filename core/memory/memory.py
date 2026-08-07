"""
Memory - conversation history ko SQLite mein permanently save karta hai,
taaki app band karke wapas kholne par bhi purani baatein yaad rahein.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict


class Memory:
    def __init__(self, db_path: str = "indus.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def save_message(self, role: str, content: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_recent(self, n: int = 10) -> List[Dict[str, str]]:
        """Last n messages return karta hai, purane se naye order mein
        (taaki AI ko context sahi order mein mile)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (n,)
        )
        rows = cursor.fetchall()
        conn.close()
        rows.reverse()
        return [{"role": role, "content": content} for role, content in rows]

    def clear(self) -> None:
        """Poori memory delete kar deta hai (testing / reset ke liye)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
