import os
import json
import base64
import asyncio
import tempfile
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
MODEL = "mistral-small-latest"

_api_semaphore = asyncio.Semaphore(1)

DIVIDER = "━" * 40


def _extract_image(file_bytes: bytes) -> str:
    b64 = base64.b64encode(file_bytes).decode()
    response = client.chat.complete(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": (
                    "Extract content from this image in clearly labeled sections:\n\n"
                    "ON-SCREEN TEXT:\n[List all text visible]\n\n"
                    "VISUAL DESCRIPTION:\n[Brief description of what is shown]"
                )},
            ],
        }],
    )
    return response.choices[0].message.content


def _extract_video(file_bytes: bytes) -> str:
    # Mistral does not support video files — analysis will use caption/context only
    return "[Video — analysis based on caption and context]"


def _analyze(raw_content: str) -> dict:
    prompt = f"""You are an assistant for organizing saved content.
Content:
{raw_content}

Return a JSON with these fields:
{{
  "title": "short punchy title (max 10 words)",
  "summary": "2-3 sentences in English.",
  "tags": ["tag1", "tag2", "tag3"],
  "folder": "Grow|Rest|Health|Creativity|Money|Work|Curation|Personal",
  "key_points": ["concise bullet point 1", "concise bullet point 2", "concise bullet point 3"],
  "fact_check": "one sentence on accuracy or empty string",
  "enrichment": {{
    "concepts": ["Term (brief definition)", "Term2 (brief definition)"],
    "context": "one sentence on background, origin, or inspiration",
    "source": "website URL or name if found, else empty string"
  }}
}}
Return ONLY valid JSON."""

    response = client.chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(text)
    for key in ("summary", "fact_check", "enrichment", "title"):
        if isinstance(data.get(key), dict):
            data[key] = json.dumps(data[key])
    return data


def format_result(result: dict) -> str:
    folder = result.get("folder", "Personal")
    tags = result.get("tags", [])
    title = result.get("title", "Untitled")
    key_points = result.get("key_points", [])
    raw_content = result.get("raw_content", "")

    enr_raw = result.get("enrichment", "")
    concepts, context, source = "", "", ""
    if enr_raw:
        try:
            enr = json.loads(enr_raw) if isinstance(enr_raw, str) else enr_raw
            if isinstance(enr, dict):
                c = enr.get("concepts", [])
                concepts = ", ".join(c) if isinstance(c, list) else str(c)
                context = enr.get("context", "")
                source = enr.get("source", "")
        except (json.JSONDecodeError, TypeError):
            pass

    first_tag = f"#{tags[0].lstrip('#')}" if tags else ""
    header = f"📁 {folder} | {first_tag}" if first_tag else f"📁 {folder}"
    lines = [header, "", f"🤖 {title}", ""]

    lines += [DIVIDER, "📋 SUMMARY"]
    for pt in key_points[:4]:
        lines.append(f"• {pt}")

    if raw_content.strip():
        lines += ["", DIVIDER, "📝 TRANSCRIPTION (OCRs & NOTES)", raw_content.strip()]

    if concepts or context or source:
        lines += ["", DIVIDER, "🔍 NERDY METADATA"]
        if concepts:
            lines.append(f"• Concepts: {concepts}")
        if context:
            lines.append(f"• Context: {context}")
        if source:
            lines.append(f"• Source: {source}")

    if tags:
        tag_line = " ".join(f"#{t.lstrip('#')}" for t in tags[:6])
        lines += ["", DIVIDER, tag_line]

    return "\n".join(lines)


def extract_db_fields(result: dict) -> dict:
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
