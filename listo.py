import asyncio
import logging
import os
from collections import defaultdict
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, MessageOriginUser, MessageOriginChannel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pipeline import process_media, process_text, process_media_group, format_result, extract_db_fields
from database import init_db, save_entry
from digest import send_weekly_digest, send_quarterly_digest

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

media_group_buffer = defaultdict(list)
media_group_tasks = {}


def _forward_context(message: Message) -> str:
    if not message.forward_origin:
        return ""
    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        name = origin.chat.title or "unknown channel"
        return f"[Forwarded from channel: {name}]\n"
    elif isinstance(origin, MessageOriginUser):
        name = origin.sender_user.full_name or "unknown user"
        return f"[Forwarded from: {name}]\n"
    return "[Forwarded post]\n"


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Hey! I'm Listo — your second brain.\n\n"
        "Drop photos, videos or forwarded posts from TikTok/Reels/Telegram — "
        "I'll read the content, summarize it, add tags, and fact-check it.\n\n"
        "Every Sunday I'll send you a digest of everything you saved 🗞"
    )


async def flush_media_group(media_group_id: str, chat_id: int):
    await asyncio.sleep(1.5)

    messages = media_group_buffer.pop(media_group_id, [])
    media_group_tasks.pop(media_group_id, None)

    if not messages:
        return

    user_id = messages[0].from_user.id
    await bot.send_message(chat_id=chat_id, text=f"⚙️ Reading {len(messages)} images together...")

    raw_caption = next((m.caption for m in messages if m.caption), "")
    forward_prefix = _forward_context(messages[0])
    caption = f"{forward_prefix}{raw_caption}".strip()

    all_bytes = []
    for msg in messages:
        photo = msg.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        all_bytes.append(file_bytes.read())

    result = await process_media_group(all_bytes, caption=caption)
    formatted = format_result(result)
    if "error" not in result:
        fields = extract_db_fields(result)
        save_entry(user_id=user_id, media_type="image", raw_content=result.get("raw_content", ""), formatted_output=formatted, **fields)
    await bot.send_message(chat_id=chat_id, text=formatted)


@dp.message(F.photo)
async def handle_photo(message: Message):
    if message.media_group_id:
        media_group_buffer[message.media_group_id].append(message)
        if message.media_group_id in media_group_tasks:
            media_group_tasks[message.media_group_id].cancel()
        task = asyncio.create_task(flush_media_group(message.media_group_id, message.chat.id))
        media_group_tasks[message.media_group_id] = task
        return

    await message.answer("⚙️ Reading...")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    forward_prefix = _forward_context(message)
    caption = f"{forward_prefix}{message.caption or ''}".strip()

    result = await process_media(file_bytes.read(), media_type="image", caption=caption)
    formatted = format_result(result)
    if "error" not in result:
        fields = extract_db_fields(result)
        save_entry(user_id=message.from_user.id, media_type="image", raw_content=result.get("raw_content", ""), message_id=message.message_id, formatted_output=formatted, **fields)
    await message.answer(formatted)


@dp.message(F.video | F.document)
async def handle_video(message: Message):
    await message.answer("⚙️ Processing video, ~20 seconds...")
    video = message.video or message.document
    file = await bot.get_file(video.file_id)
    file_bytes = await bot.download_file(file.file_path)

    forward_prefix = _forward_context(message)
    caption = f"{forward_prefix}{message.caption or ''}".strip()

    result = await process_media(file_bytes.read(), media_type="video", caption=caption)
    formatted = format_result(result)
    if "error" not in result:
        fields = extract_db_fields(result)
        save_entry(user_id=message.from_user.id, media_type="video", raw_content=result.get("raw_content", ""), message_id=message.message_id, formatted_output=formatted, **fields)
    await message.answer(formatted)


@dp.message(F.text)
async def handle_text(message: Message):
    text = message.text
    if not text or len(text) < 20:
        return

    forward_prefix = _forward_context(message)
    full_text = f"{forward_prefix}{text}".strip()

    await message.answer("⚙️ Reading...")
    result = await process_text(full_text)
    formatted = format_result(result)
    if "error" not in result:
        fields = extract_db_fields(result)
        save_entry(user_id=message.from_user.id, media_type="text", raw_content=result.get("raw_content", full_text), message_id=message.message_id, formatted_output=formatted, **fields)
    await message.answer(formatted)


async def main():
    init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_weekly_digest, "cron", day_of_week="sun", hour=10, minute=0, args=[bot])
    scheduler.add_job(send_quarterly_digest, "cron", month="1,4,7,10", day=1, hour=10, minute=0, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
