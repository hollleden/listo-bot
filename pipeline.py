import os
import json
import base64
import asyncio
import tempfile
import time
from urllib.parse import quote_plus
from mistralai import Mistral
from google import genai

mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_MISTRAL = "mistral-small-latest"
MODEL_GEMINI = "gemini-2.5-flash"

_api_semaphore = asyncio.Semaphore(1)

DIVIDER = "━" * 16

FOLDER_EMOJI = {
    "Grow": "🌱", "Rest": "😴", "Health": "💚", "Creativity": "🎨",
    "Money": "💰", "Work": "💼", "Curation": "🗂", "Personal": "💫",
    "Beauty": "💄", "Food": "🍽", "Travel": "✈️", "Sport": "🏃",
}


def _extract_image(file_bytes: bytes) -> str:
    b64 = base64.b64encode(file_bytes).decode()
    response = mistral.chat.complete(
        model=MODEL_MISTRAL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": (
                    "Extract all content from this image. "
                    "Return plain text only — no markdown, no headers, no bold, no bullet symbols.\n\n"
                    "First list every word of text visible in the image, line by line.\n"
                    "Then write one short paragraph describing what is shown visually."
                )},
            ],
        }],
    )
    return response.choices[0].message.content


def _extract_video(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(file_bytes)
        tmp_path = f.name
    try:
        video_file = gemini.files.upload(file=tmp_path, config={"mime_type": "video/mp4"})
        while video_file.state.name == "PROCESSING":
            time.sleep(3)
            video_file = gemini.files.get(name=video_file.name)
        for attempt in range(5):
            try:
                response = gemini.models.generate_content(
                    model=MODEL_GEMINI,
                    contents=[
                        video_file,
                        "Extract ALL text from subtitles and overlays. Transcribe all speech verbatim with timestamps (MM:SS). Describe what is happening.",
                    ],
                )
                return response.text
            except Exception as e:
                if "429" in str(e) and attempt < 4:
                    time.sleep(10 * (2 ** attempt))  # 10s, 20s, 40s, 80s
                    continue
                raise
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _analyze(raw_content: str) -> dict:
    prompt = f"""You are an assistant for organizing saved content.
Content:
{raw_content}

Return a JSON with these fields:
{{
  "title": "short punchy title (max 10 words)",
  "tags": ["tag1", "tag2", "tag3"],
  "folder": "Grow|Rest|Health|Creativity|Money|Work|Curation|Personal|Beauty|Food|Travel|Sport",
  "key_points": ["concise bullet point 1", "concise bullet point 2", "concise bullet point 3"],
  "products": [{{"name": "product or item name", "brand": "brand name or empty string"}}],
  "fact_check": "one sentence on accuracy or empty string",
  "enrichment": {{
    "concepts": ["Term (brief definition)"],
    "context": "one sentence on background or origin",
    "source": "website or channel name if found, else empty string"
  }}
}}
Return ONLY valid JSON."""

    response = mistral.chat.complete(
        model=MODEL_MISTRAL,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(text)
    for key in ("fact_check", "enrichment", "title"):
        if isinstance(data.get(key), dict):
            data[key] = json.dumps(data[key])
    return data


def format_result(result: dict) -> str:
    folder = result.get("folder", "Personal")
    title = result.get("title", "Untitled")
    key_points = result.get("key_points", [])
    raw_content = result.get("raw_content", "")
    tags = result.get("tags", [])
    products = result.get("products", [])

    emoji = FOLDER_EMOJI.get(folder, "📁")
    lines = [f"{emoji} {folder.upper()} · {title}", ""]

    # SUMMARY
    lines += [DIVIDER, "📋 SUMMARY"]
    for pt in key_points[:4]:
        lines.append(f"▪ {pt}")

    # TRANSCRIPTION
    if raw_content.strip():
        lines += ["", DIVIDER, "📝 TRANSCRIPTION"]
        for line in raw_content.strip().split("\n"):
            if line.strip():
                lines.append(f"┆ {line}")

    # EXTRACTED products
    if products:
        lines += ["", DIVIDER, "🔍 EXTRACTED"]
        lines.append(f"▪ {folder.upper()}")
        for p in products:
            name = p.get("name", "")
            brand = p.get("brand", "")
            if not name:
                continue
            query = quote_plus(f"{name} {brand}".strip())
            google = f"https://www.google.com/search?q={query}"
            entry = f"  • {name}"
            if brand:
                entry += f" by {brand}"
            entry += f" → {google}"
            lines.append(entry)

    # TAGS
    if tags:
        lines += ["", DIVIDER, "📁 FOLDER & TAGS"]
        lines.append(f"#{folder}")
        clean = [t.lstrip("#") for t in tags[:5]]
        for i, t in enumerate(clean):
            prefix = "└─" if i == len(clean) - 1 else "├─"
            lines.append(f"{prefix} #{t}")

    return "\n".join(lines)


def extract_db_fields(result: dict) -> dict:
    tags = result.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags, ensure_ascii=False)
    return {
        "summary": " | ".join(result.get("key_points", [])),
        "tags": tags,
        "folder": result.get("folder", "Personal"),
        "fact_check": result.get("fact_check", ""),
        "enrichment": result.get("enrichment", ""),
        "title": result.get("title", ""),
    }


async def _run_pipeline(raw_content: str, is_video: bool = False) -> dict:
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
                    "fact_check": "", "enrichment": "", "products": []}


async def process_media_group(images: list[bytes], caption: str = "") -> dict:
    async with _api_semaphore:
        try:
            parts = []
            for i, img in enumerate(images):
                text = await asyncio.to_thread(_extract_image, img)
                parts.append(f"-- Image {i+1} --\n{text}")
            raw = f"{caption}\n\n" + "\n\n".join(parts) if caption else "\n\n".join(parts)
            return await _run_pipeline(raw)
        except Exception as e:
            return {"error": str(e), "raw_content": "", "content_type": "other",
                    "title": "Error", "summary": str(e), "tags": [], "folder": "Personal",
                    "fact_check": "", "enrichment": "", "products": []}


async def process_text(text: str) -> dict:
    async with _api_semaphore:
        try:
            return await _run_pipeline(text)
        except Exception as e:
            return {"error": str(e), "raw_content": text, "content_type": "other",
                    "title": "Error", "summary": str(e), "tags": [], "folder": "Personal",
                    "fact_check": "", "enrichment": "", "products": []}
