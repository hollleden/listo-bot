import os
from datetime import datetime, date, timedelta
from mistralai import Mistral
from database import get_entries_since, get_active_users

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
MODEL = "mistral-small-latest"


def _build_digest(entries: list[dict], digest_type: str) -> str:
    grouped = {}
    for e in entries:
        folder = e.get("folder", "Personal")
        grouped.setdefault(folder, []).append(e.get("summary", ""))

    header = f"Listo — {'weekly digest' if digest_type == 'weekly' else 'quarterly review'}\n{datetime.now().strftime('%d.%m.%Y')}\n\n"
    body = ""
    for folder, summaries in grouped.items():
        body += f"📁 {folder} — {len(summaries)} saved\n"
        for s in summaries[:5]:
            body += f"• {s}\n"
        body += "\n"

    if digest_type == "quarterly":
        all_summaries = [e.get("summary", "") for e in entries]
        insight = _get_quarterly_insight(all_summaries)
        body += f"Quarterly insight\n{insight}"

    return header + body


def _get_quarterly_insight(summaries: list) -> str:
    prompt = f"""Here is what the person saved over the last 3 months:
{chr(10).join(summaries[:30])}

Write 2-3 warm, friendly sentences about what themes stand out and what this says about their interests."""

    response = client.chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


async def send_weekly_digest(bot):
    since = str(date.today() - timedelta(days=7))
    for user_id in get_active_users():
        entries = get_entries_since(user_id, since)
        if not entries:
            continue
        await bot.send_message(chat_id=user_id, text=_build_digest(entries, "weekly"))


async def send_quarterly_digest(bot):
    since = str(date.today() - timedelta(days=90))
    for user_id in get_active_users():
        entries = get_entries_since(user_id, since)
        if not entries:
            continue
        await bot.send_message(chat_id=user_id, text=_build_digest(entries, "quarterly"))
