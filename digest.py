import anthropic
import os
from datetime import datetime
from database import get_entries_since

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CONTENT_TYPES = {
    "book": "📚 Книги",
    "place": "🌍 Места",
    "recipe": "🍽️ Рецепты",
    "philosophy": "🧠 Философия",
    "spanish": "💃 Испанский",
    "film": "🎬 Фильмы",
    "health": "💚 Здоровье",
    "other": "📌 Другое",
}


def _build_digest(entries, digest_type: str) -> str:
    # Группируем по типу контента
    grouped = {}
    for entry in entries:
        ct, summary, tags, folder, created_at = entry
        grouped.setdefault(ct, []).append(summary)

    if digest_type == "weekly":
        header = f"🗞 *Listo — дайджест недели*\n_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
    else:
        header = f"🌟 *Listo — квартальный обзор*\n_{datetime.now().strftime('%d.%m.%Y')}_\n\n"

    body = ""
    for ct, summaries in grouped.items():
        label = CONTENT_TYPES.get(ct, "📌 Другое")
        body += f"*{label}* — {len(summaries)} шт.\n"
        for s in summaries[:5]:  # максимум 5 на категорию
            body += f"• {s}\n"
        body += "\n"

    if digest_type == "quarterly":
        all_summaries = [e[1] for e in entries]
        insight = _get_quarterly_insight(all_summaries)
        body += f"💡 *Инсайт квартала*\n{insight}"

    return header + body


def _get_quarterly_insight(summaries: list) -> str:
    prompt = f"""Вот что человек сохранял последние 3 месяца:
{chr(10).join(summaries[:30])}

Напиши 2-3 предложения — какие темы и паттерны прослеживаются? 
Что это говорит о её интересах прямо сейчас? 
Пиши тепло, по-дружески, обращайся на "ты"."""

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def send_weekly_digest(bot, chat_id):
    entries = get_entries_since(7)
    if not entries:
        await bot.send_message(chat_id=chat_id, text="🗞 На этой неделе ничего не сохранено!")
        return
    digest = _build_digest(entries, "weekly")
    await bot.send_message(chat_id=chat_id, text=digest, parse_mode="Markdown")


async def send_quarterly_digest(bot, chat_id):
    entries = get_entries_since(90)
    if not entries:
        return
    digest = _build_digest(entries, "quarterly")
    await bot.send_message(chat_id=chat_id, text=digest, parse_mode="Markdown")
