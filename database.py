import os
import json
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

def save_entry(user_id, content_type, summary, tags, folder, raw_content, formatted_output=""):
    payload = {
        "user_id": user_id,
        "content_type": content_type,
        "summary": summary,
        "tags": json.dumps(tags, ensure_ascii=False) if isinstance(tags, list) else tags,
        "folder": folder,
        "raw_content": raw_content[:5000],  # avoid huge payloads
        "formatted_output": formatted_output,
    }
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/entries", headers=HEADERS, json=payload, timeout=10)
    r.raise_for_status()

def get_entries_since(days: int, user_id: int = None):
    params = {
        "select": "content_type,summary,tags,folder,created_at",
        "created_at": f"gte.{_days_ago(days)}",
        "order": "folder,content_type",
    }
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/entries", headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    rows = r.json()
    return [(e["content_type"], e["summary"], e["tags"], e["folder"], e["created_at"]) for e in rows]

def _days_ago(days):
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(days=days)).isoformat()
