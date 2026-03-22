import sqlite3
import json
import os

DB_PATH = os.getenv("DB_PATH", "listo.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            summary TEXT,
            tags TEXT,
            folder TEXT,
            raw_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_entry(content_type, summary, tags, folder, raw_content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO entries (content_type, summary, tags, folder, raw_content)
        VALUES (?, ?, ?, ?, ?)
        """,
        (content_type, summary, json.dumps(tags, ensure_ascii=False), folder, raw_content),
    )
    conn.commit()
    conn.close()


def get_entries_since(days: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT content_type, summary, tags, folder, created_at
        FROM entries
        WHERE created_at >= datetime('now', ?)
        ORDER BY folder, content_type
        """,
        (f"-{days} days",),
    )
    rows = c.fetchall()
    conn.close()
    return rows
