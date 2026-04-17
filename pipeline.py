import os
import json
import tempfile
import asyncio
import time
import requests
from google import genai
from google.genai import types
from database import save_entry
from enrichment import (
    search_goodreads,
    search_press_reviews,
    search_imdb,
    search_exhibition,
    search_youtube,
    google_maps_link,
)

# --- 1. Настройки и Клиенты ---
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
# Используем стабильную бесплатную модель
MODEL = "gemini-2.0-flash-lite" 

# Ограничение: 1 запрос за раз, чтобы не превышать лимиты (15 RPM)
_api_semaphore = asyncio.Semaphore(1)

CONTENT_TYPES = {
    "book": "📚 Book",
    "place": "🌍 Place",
    "recipe": "🍽️ Recipe",
    "philosophy": "🧠 Philosophy",
    "spanish": "💃 Spanish",
    "film": "🎬 Film / Series",
    "health": "💚 Health",
    "retail": "🛍️ Retail",
    "other": "📌 Other",
}

# ---------------------------------------------------------------------------
# 2. Извлечение (OCR / Видео)
# ---------------------------------------------------------------------------

def _extract_image(file_bytes: bytes) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg"),
            "Extract ALL text from this screenshot verbatim. Then describe what is shown in the image.",
        ],
    )
    return response.text


def _extract_video(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(file_bytes)
        tmp_path = f.name

    try:
        video_file = client.files.upload(file=tmp_path, config={"mime_type": "video/mp4"})
        while video_file.state.name == "PROCESSING":
            time.sleep(3)
            video_file = client.files.get(name=video_file.name)

        response = client.models.generate_content(
            model=MODEL,
            contents=[
                video_file,
                "Extract ALL text from subtitles and overlays. Transcribe all speech. Describe what is happening.",
            ],
        )
        return response.text
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# 3. Анализ и Логика
# ---------------------------------------------------------------------------

def _analyze(raw_content: str, is_video: bool = False) -> dict:
    prompt = f"""You are an assistant for organizing saved content.
Content:
{raw_content}

Return a JSON with these fields:
{{
  "content_type": "book|place|recipe|philosophy|spanish|film|health|retail|other",
  "title": "short punchy title",
  "summary": "2-4 sentences in English.",
  "tags": ["tag1", "tag2"],
  "folder": "Crecer|Descanso|Salud|Creatividad|Dinero|Trabajo|Curación|Personal",
  "key_points": [],
  "enrichment": {{ "items": [] }},
  "youtube_videos": [],
  "is_exhibition": false,
  "exhibition_name": "",
  "exhibition_venue": "",
  "exhibition_url": ""
}}
Return ONLY valid JSON."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _push_to_airtable(items: list) -> list[str]:
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        return ["⚠️ Airtable credentials missing"]

    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }
    created = []

    for item in items:
        name = (item.get("name") or "").strip()
        if not name: continue

        # Важно: Поля "Name", "About", "Instagram" должны быть в вашей таблице "Brands"
        fields = {
            "Name": name,
            "About": item.get("about") or "",
            "Instagram": item.get("instagram") or "",
        }
        
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Brands"
        try:
            resp = requests.post(url, headers=headers, json={"fields": fields}, timeout=10)
            if resp.ok:
                created.append(f"Brand: {name}")
            else:
                created.append(f"⚠️ {name}: {resp.text[:50]}")
        except Exception as e:
            created.append(f"⚠️ {name}: Connection error")

    return created


def _enrich(analysis: dict) -> dict:
    ct = analysis.get("content_type", "other")
    enrich = analysis.get("enrichment", {})
    
    # Если это шоппинг/ретейл, отправляем в Airtable
    if ct == "retail":
        items = enrich.get("items", [])
        if items:
            analysis["airtable_created"] = _push_to_airtable(items)
            
    # Здесь можно добавить поиск ссылок (Goodreads, IMDB и т.д.)
    return analysis


def _format(analysis: dict) -> str:
    ct = analysis.get("content_type", "other")
    type_label = CONTENT_TYPES.get(ct, "📌 Other")
    title = analysis.get("title", "Untitled")
    summary = analysis.get("summary", "")
    folder = analysis.get("folder", "Personal")
    
    res = f"{type_label} | 📁 {folder}\n\n**{title}**\n{summary}"
    
    airtable = analysis.get("airtable_created", [])
    if airtable:
        res += "\n\n✅ Airtable:\n" + "\n".join(airtable)
        
    return res


# ---------------------------------------------------------------------------
# 4. Основные функции для запуска (Exports)
# ---------------------------------------------------------------------------

async def _run_pipeline(raw_content: str, is_video: bool = False) -> str:
    # Запускаем тяжелые задачи в потоках, чтобы не блокировать бота
    analysis = await asyncio.wait_for(asyncio.to_thread(_analyze, raw_content, is_video=is_video), timeout=60.0)
    analysis = await asyncio.wait_for(asyncio.to_thread(_enrich, analysis), timeout=60.0)
    formatted = _format(analysis)
    
    # Сохраняем в локальную БД (sqlite)
    save_entry(
        analysis.get("content_type", "other"),
        analysis.get("summary", ""),
        analysis.get("tags", []),
        analysis.get("folder", "Personal"),
        raw_content,
    )
    return formatted


async def process_media(file_bytes: bytes, media_type: str, caption: str = "") -> str:
    async with _api_semaphore:
        try:
            if media_type == "image":
                raw_media = await asyncio.to_thread(_extract_image, file_bytes)
            else:
                raw_media = await asyncio.to_thread(_extract_video, file_bytes)
            
            raw = f"{caption}\n\n{raw_media}" if caption else raw_media
            return await _run_pipeline(raw, is_video=(media_type == "video"))
        except Exception as e:
            return f"⚠️ Ошибка медиа: {str(e)}"


async def process_media_group(images: list[bytes], caption: str = "") -> str:
    async with _api_semaphore:
        try:
            parts = []
            for i, img in enumerate(images):
                text = await asyncio.to_thread(_extract_image, img)
                parts.append(f"[Image {i+1}]: {text}")
            
            raw = f"{caption}\n\n" + "\n".join(parts)
            return await _run_pipeline(raw)
        except Exception as e:
            return f"⚠️ Ошибка группы фото: {str(e)}"


async def process_text(text: str) -> str:
    async with _api_semaphore:
        try:
            return await _run_pipeline(text)
        except Exception as e:
            return f"⚠️ Ошибка текста: {str(e)}"
