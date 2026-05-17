import os
import json
import tempfile
import asyncio
import time
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.0-flash-lite"

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


def _extract_image(file_bytes: bytes) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg"),
            """"Extract content from this video in clearly labeled sections:

AUDIO TRANSCRIPT:
[Transcribe all spoken words verbatim]

ON-SCREEN TEXT:
[List all text overlays and captions with timestamps, format: MM:SS — text]

VISUAL DESCRIPTION:
[Brief description of what is shown]"""",
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


def _analyze(raw_content: str) -> dict:
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
  "key_points": ["point1", "point2"],
  "fact_check": "one sentence on accuracy or empty string",
  "enrichment": ""
}}
Return ONLY valid JSON. All values must be strings or arrays of strings."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(text)
    # guard: ensure no nested dicts slip through
    for key in ("summary", "fact_check", "enrichment", "title"):
        if isinstance(data.get(key), dict):
            data[key] = json.dumps(data[key])
    return data


def format_result(result: dict) -> str:
    """Format analysis dict into a human-readable bot message."""
    ct = result.get("content_type", "other")
    type_label = CONTENT_TYPES.get(ct, "📌 Other")
    title = result.get("title", "Untitled")
    summary = result.get("summary", "")
    folder = result.get("folder", "Personal")
    tags = result.get("tags", [])
    key_points = result.get("key_points", [])
    fact_check = result.get("fact_check", "")

    lines = [f"{type_label} | 📁 {folder}", "", f"**{title}**", summary]

    if key_points:
        lines.append("")
        for pt in key_points[:4]:
            lines.append(f"• {pt}")

    if fact_check:
        lines.append(f"\n🔍 {fact_check}")

    if tags:
        lines.append("\n" + " ".join(f"#{t}" for t in tags[:5]))

    return "\n".join(lines)


def extract_db_fields(result: dict) -> dict:
    """Extract fields needed for database.save_entry."""
    tags = result.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags, ensure_ascii=False)
    return {
        "summary": result.get("summary", ""),
        "tags": tags,
        "folder": result.get("folder", "Personal"),
        "fact_check": result.get("fact_check", ""),
        "enrichment": result.get("enrichment", ""),
        "title": result.get("title", ""),
    }


async def _run_pipeline(raw_content: str, is_video: bool = False) -> dict:
    """Run analysis and return result dict (saving is handled by listo.py)."""
    analysis = await asyncio.wait_for(
        asyncio.to_thread(_analyze, raw_content), timeout=60.0
    )
    analysis["raw_content"] = raw_content
    return analysis


async def process_media(file_bytes: bytes, media_type: str, caption: str = "") -> dict:
    async with _api_semaphore:
        try:
            if media_type == "image":
                raw_media = await asyncio.to_thread(_extract_image, file_bytes)
            else:
                raw_media = await asyncio.to_thread(_extract_video, file_bytes)
            raw = f"{caption}\n\n{raw_media}" if caption else raw_media
            return await _run_pipeline(raw, is_video=(media_type == "video"))
        except Exception as e:
            return {"error": str(e), "raw_content": "", "content_type": "other",
                    "title": "Error", "summary": str(e), "tags": [], "folder": "Personal",
                    "fact_check": "", "enrichment": ""}


async def process_media_group(images: list[bytes], caption: str = "") -> dict:
    async with _api_semaphore:
        try:
            parts = []
            for i, img in enumerate(images):
                text = await asyncio.to_thread(_extract_image, img)
                parts.append(f"[Image {i+1}]: {text}")
            raw = f"{caption}\n\n" + "\n".join(parts)
            return await _run_pipeline(raw)
        except Exception as e:
            return {"error": str(e), "raw_content": "", "content_type": "other",
                    "title": "Error", "summary": str(e), "tags": [], "folder": "Personal",
                    "fact_check": "", "enrichment": ""}


async def process_text(text: str) -> dict:
    async with _api_semaphore:
        try:
            return await _run_pipeline(text)
        except Exception as e:
            return {"error": str(e), "raw_content": text, "content_type": "other",
                    "title": "Error", "summary": str(e), "tags": [], "folder": "Personal",
                    "fact_check": "", "enrichment": ""}
