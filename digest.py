import os
from datetime import datetime
from google import genai
from database import get_entries_since

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

CONTENT_TYPES = {
    "book": "📚 Books", "place": "🌍 Places", "recipe": "🍽️ Recipes",
    "philosophy": "🧠 Philosophy", "spanish": "💃 Spanish",
    "film": "🎬 Films", "health": "💚 Health", "other": "📌 Other",
}


def _build_digest(entries, digest_type: str) -> str:
    grouped = {}
    for ct, summary, tags, folder, created_at in entries:
        grouped.setdefault(ct, []).append(summary)

    header = f"Listo — {'weekly digest' if digest_type == 'weekly' else 'quarterly review'}\n{datetime.now().strftime('%d.%m.%Y')}\n\n"
    body = ""
    for ct, summaries in grouped.items():
        label = CONTENT_TYPES.get(ct, "📌 Other")
        body += f"{label} — {len(summaries)} saved\n"
        for s in summaries[:5]:
            body += f"- {s}\n"
        body += "\n"

    if digest_type == "quarterly":
        all_summaries = [e[1] for e in entries]
        insight = _get_quarterly_insight(all_summaries)
        body += f"Quarterly insight\n{insight}"

    return header + body


def _get_quarterly_insight(summaries: list) -> str:
    prompt = f"""Here is what the person saved over the last 3 months:
{chr(10).join(summaries[:30])}

Write 2-3 warm, friendly sentences about what themes stand out and what this says about their interests."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


async def send_weekly_digest(bot, chat_id):
    entries = get_entries_since(7)
    if not entries:
        await bot.send_message(chat_id=chat_id, text="Nothing saved this week!")
        return
    await bot.send_message(chat_id=chat_id, text=_build_digest(entries, "weekly"))


async def send_quarterly_digest(bot, chat_id):
    entries = get_entries_since(90)
    if not entries:
        return
    await bot.send_message(chat_id=chat_id, text=_build_digest(entries, "quarterly"))
