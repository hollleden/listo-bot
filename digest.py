import os
from datetime import datetime
from database import get_entries_since
import google.genai as genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CONTENT_TYPES = {
    "book": "📚 Books",
    "place": "🌍 Places",
    "recipe": "🍽️ Recipes",
    "philosophy": "🧠 Philosophy",
    "spanish": "💃 Spanish",
    "film": "🎬 Films",
    "health": "💚 Health",
    "other": "📌 Other",
}


def _build_digest(entries, digest_type: str) -> str:
    # Группируем по типу контента
    grouped = {}
    for entry in entries:
        ct, summary, tags, folder, created_at = entry
        grouped.setdefault(ct, []).append(summary)

    if digest_type == "weekly":
        header = f"🗞 *Listo — weekly digest*\n_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
    else:
        header = f"🌟 *Listo — quarterly review*\n_{datetime.now().strftime('%d.%m.%Y')}_\n\n"

    body = ""
    for ct, summaries in grouped.items():
        label = CONTENT_TYPES.get(ct, "📌 Other")
        body += f"*{label}* — {len(summaries)} saved\n"
        for s in summaries[:5]:
            body += f"• {s}\n"
        body += "\n"

    if digest_type == "quarterly":
        all_summaries = [e[1] for e in entries]
        insight = _get_quarterly_insight(all_summaries)
        body += f"💡 *Quarterly insight*\n{insight}"

    return header + body


def _get_quarterly_insight(summaries: list) -> str:
    prompt = f"""Here is what the person saved over the last 3 months:
{chr(10).join(summaries[:30])}

Write 2-3 sentences — what themes and patterns stand out? 
What does this say about their interests right now? 
Be warm and friendly."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


async def send_weekly_digest(bot, chat_id):
    entries = get_entries_since(7)
    if not entries:
        await bot.send_message(chat_id=chat_id, text="🗞 Nothing saved this week!")
        return
    digest = _build_digest(entries, "weekly")
    await bot.send_message(chat_id=chat_id, text=digest)


async def send_quarterly_digest(bot, chat_id):
    entries = get_entries_since(90)
    if not entries:
        return
    digest = _build_digest(entries, "quarterly")
    await bot.send_message(chat_id=chat_id, text=digest)
