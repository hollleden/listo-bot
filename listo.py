import logging
import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from dotenv import load_dotenv
from pipeline import process_media
from database import init_db
from digest import send_weekly_digest, send_quarterly_digest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
YOUR_CHAT_ID = os.getenv("ALLOWED_ID")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola! Я Listo — твой второй мозг.\n\n"
        "Скидывай мне фото или видео из TikTok/Reels — "
        "я прочитаю, разберу и сохраню.\n\n"
        "Каждое воскресенье пришлю дайджест всего сохранённого 🗞"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ Читаю...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()

    result = await process_media(bytes(file_bytes), media_type="image")
    await update.message.reply_text(result, parse_mode="Markdown")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ Обрабатываю видео, займёт ~20 секунд...")

    video = update.message.video or update.message.document
    file = await context.bot.get_file(video.file_id)
    file_bytes = await file.download_as_bytearray()

    result = await process_media(bytes(file_bytes), media_type="video")
    await update.message.reply_text(result, parse_mode="Markdown")


def main():
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    scheduler = AsyncIOScheduler()

    # Еженедельный дайджест — каждое воскресенье в 10:00
    scheduler.add_job(
        send_weekly_digest,
        "cron",
        day_of_week="sun",
        hour=10,
        minute=0,
        args=[app.bot, YOUR_CHAT_ID],
    )

    # Квартальный дайджест — 1 января, апреля, июля, октября
    scheduler.add_job(
        send_quarterly_digest,
        "cron",
        month="1,4,7,10",
        day=1,
        hour=10,
        minute=0,
        args=[app.bot, YOUR_CHAT_ID],
    )

    scheduler.start()
    app.run_polling()


if __name__ == "__main__":
    main()
