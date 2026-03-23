import asyncio
import logging
import os
from collections import defaultdict
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, MessageOriginUser, MessageOriginChannel, MessageOriginHiddenUser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pipeline import process_media, process_text, process_media_group
from database import init_db
from digest import send_weekly_digest, send_quarterly_digest

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_ID = int(os.getenv("ALLOWED_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Buffer for media groups
media_group_buffer = defaultdict(list)
media_group_tasks = {}


def _forward_context(message: Message) -> str:
    """Extract source context from forwarded messages to prepend to content."""
    if not message.forward_origin:
        return ""
    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        name = origin.chat.title or "unknown channel"
        return f"[Forwarded from channel: {name}]\n"
    elif isinstance(origin, MessageOriginUser):
        name = origin.sender_user.full_name or "unknown user"
        return f"[Forwarded from: {name}]\n"
    elif isinstance(origin, MessageOriginHiddenUser):
        name = origin.sender_user_name or "hidden user"
        return f"[Forwarded from: {name}]\n"
    return "[Forwarded post]\n"


@dp.message(CommandStart())
async def start(message: Message):
    if message.from_user.id != ALLOWED_ID:
        return
    await message.answer(
        "👋 Hey! I'm Listo — your second brain.\n\n"
        "Drop photos, videos or forwarded posts from TikTok/Reels/Telegram — "
        "I'll read the content, summarize it, add tags, and fact-check it.\n\n"
        "Every Sunday I'll send you a digest of everything you saved 🗞"
    )


async def flush_media_group(media_group_id: str, chat_id: int):
    """Wait briefly then process all photos in a group together."""
    await asyncio.sleep(1.5)

    messages = media_group_buffer.pop(media_group_id, [])
    media_group_tasks.pop(media_group_id, None)

    if not messages:
        return

    await bot.send_message(chat_id=chat_id, text=f"⚙️ Reading {len(messages)} images together...")

    # Caption from first message that has one
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
    await bot.send_message(chat_id=chat_id, text=result)


@dp.message(F.photo)
async def handle_photo(message: Message):
    if message.from_user.id != ALLOWED_ID:
        return

    if message.media_group_id:
        media_group_buffer[message.media_group_id].append(message)
        if message.media_group_id in media_group_tasks:
            media_group_tasks[message.media_group_id].cancel()
        task = asyncio.create_task(
            flush_media_group(message.media_group_id, message.chat.id)
        )
        media_group_tasks[message.media_group_id] = task
        return

    await message.answer("⚙️ Reading...")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    forward_prefix = _forward_context(message)
    caption = f"{forward_prefix}{message.caption or ''}".strip()

    result = await process_media(file_bytes.read(), media_type="image", caption=caption)
    await message.answer(result)


@dp.message(F.video | F.document)
async def handle_video(message: Message):
    if message.from_user.id != ALLOWED_ID:
        return
    await message.answer("⚙️ Processing video, ~20 seconds...")
    video = message.video or message.document
    file = await bot.get_file(video.file_id)
    file_bytes = await bot.download_file(file.file_path)

    forward_prefix = _forward_context(message)
    caption = f"{forward_prefix}{message.caption or ''}".strip()

    result = await process_media(file_bytes.read(), media_type="video", caption=caption)
    await message.answer(result)


@dp.message(F.text)  # F.caption removed — handled inside photo/video handlers
async def handle_text(message: Message):
    if message.from_user.id != ALLOWED_ID:
        return
    text = message.text
    if not text or len(text) < 20:
        return

    forward_prefix = _forward_context(message)
    full_text = f"{forward_prefix}{text}".strip()

    await message.answer("⚙️ Reading...")
    result = await process_text(full_text)
    await message.answer(result)


async def main():
    init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_weekly_digest,
        "cron",
        day_of_week="sun",
        hour=10,
        minute=0,
        args=[bot, ALLOWED_ID],
    )
    scheduler.add_job(
        send_quarterly_digest,
        "cron",
        month="1,4,7,10",
        day=1,
        hour=10,
        minute=0,
        args=[bot, ALLOWED_ID],
    )
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
