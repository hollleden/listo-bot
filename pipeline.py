import os
import base64
import json
import tempfile
import asyncio
import time
import google.genai as genai
from google.genai import types as genai_types
from database import save_entry

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CONTENT_TYPES = {
    "book": "📚 Book",
    "place": "🌍 Place",
    "recipe": "🍽️ Recipe",
    "philosophy": "🧠 Philosophy",
    "spanish": "💃 Spanish",
    "film": "🎬 Film / Series",
    "health": "💚 Health",
    "other": "📌 Other",
}


def _extract_image(file_bytes: bytes) -> str:
    image_part = genai.types.Part.from_bytes(
        data=file_bytes,
        mime_type="image/jpeg",
    )
    prompt = (
        "Extract ALL text from this screenshot verbatim. "
        "Then describe what is shown in the image."
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-latest",
        contents=[prompt, image_part],
    )
    return response.text


def _extract_video(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(file_bytes)
        tmp_path = f.name

    try:
        video_file = client.files.upload(path=tmp_path, config={"mime_type": "video/mp4"})
        while video_file.state.name == "PROCESSING":
            time.sleep(3)
            video_file = client.files.get(name=video_file.name)

        prompt = (
            "Extract ALL text from subtitles and overlays in this video. "
            "Transcribe all speech. Describe what is happening."
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-latest",
            contents=[prompt, video_file],
        )
        return response.text
    finally:
        os.unlink(tmp_path)


def _analyze(raw_content: str) -> dict:
    prompt = f"""You are an assistant for organizing saved content from TikTok and Reels.

Here is the media content:
{raw_content}

Analyze it and return a JSON with the following fields:
{{
  "content_type": "book|place|recipe|philosophy|spanish|film|health|other",
  "summary": "summary in English, 2-4 sentences",
  "tags": ["tag1", "tag2", "tag3"],
  "folder": "Crecer|Descanso|Salud|Creatividad|Dinero|Trabajo|Personal",
  "fact_check": [
    {{"claim": "specific factual claim from the content", "verdict": "✅ True|⚠️ Disputed|❌ False|🔍 Can't verify", "note": "brief explanation"}}
  ],
  "enrichment": {{}}
}}

Folder rules:
- Books, philosophy, Spanish, personal growth → Crecer
- Travel, places, rest → Descanso
- Health, recipes, hair, body → Salud
- Films, creativity, inspiration → Creatividad
- Money, investments → Dinero
- Work → Trabajo
- Everything else → Personal

For enrichment fill in based on type:
- book: {{"author": "", "year": "", "genre": "", "goodreads_rating": "", "available_in_russian": ""}}
- place: {{"country": "", "city": "", "best_season": "", "approx_budget": ""}}
- recipe: {{"cook_time": "", "difficulty": "easy|medium|hard", "key_ingredients": [], "dietary": ""}}
- philosophy: {{"school": "", "key_thinker": "", "opposite_view": ""}}
- spanish: {{"level": "A1|A2|B1|B2|C1", "key_words": []}}
- film: {{"year": "", "genre": "", "imdb_rating": "", "where_to_watch": ""}}
- health: {{"topic": "", "evidence_level": "scientific|popular|anecdotal"}}

Return ONLY valid JSON, no markdown, no extra text."""

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-latest",
        contents=prompt,
    )
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _format(analysis: dict) -> str:
    ct = analysis.get("content_type", "other")
    type_label = CONTENT_TYPES.get(ct, "📌 Other")
    folder = analysis.get("folder", "Personal")
    summary = analysis.get("summary", "")
    tags = " ".join([f"#{t.replace(' ', '_').lower()}" for t in analysis.get("tags", [])])

    # Fact-check
    fc_lines = []
    for fc in analysis.get("fact_check", []):
        fc_lines.append(f"{fc['verdict']} {fc['claim']} — {fc['note']}")
    fact_check_text = "\n".join(fc_lines) if fc_lines else "🔍 No specific facts to verify"

    # Обогащение
    enrich = analysis.get("enrichment", {})
    enrich_lines = []
    for k, v in enrich.items():
        if v and v != "" and v != []:
            if isinstance(v, list):
                v = ", ".join(v)
            enrich_lines.append(f"• {k}: {v}")
    enrich_text = "\n".join(enrich_lines) if enrich_lines else ""

    result = (
        f"{type_label} · 📁 {folder}\n\n"
        f"📝 Summary\n{summary}\n\n"
        f"🏷 {tags}\n\n"
        f"✅ Fact-check\n{fact_check_text}"
    )

    if enrich_text:
        result += f"\n\n🔎 Details\n{enrich_text}"

    return result


async def process_media(file_bytes: bytes, media_type: str) -> str:
    try:
        if media_type == "image":
            raw_content = await asyncio.wait_for(
                asyncio.to_thread(_extract_image, file_bytes),
                timeout=30.0
            )
        else:
            raw_content = await asyncio.wait_for(
                asyncio.to_thread(_extract_video, file_bytes),
                timeout=60.0
            )

        analysis = await asyncio.wait_for(
            asyncio.to_thread(_analyze, raw_content),
            timeout=30.0
        )

        save_entry(
            content_type=analysis.get("content_type", "other"),
            summary=analysis.get("summary", ""),
            tags=analysis.get("tags", []),
            folder=analysis.get("folder", "Personal"),
            raw_content=raw_content,
        )

        return _format(analysis)

    except asyncio.TimeoutError:
        return "❌ Timed out — please try again"
    except Exception as e:
        return f"❌ Something went wrong: {str(e)}"


async def process_media_group(images: list[bytes]) -> str:
    """Process multiple images from one post together."""
    try:
        parts = []
        for i, img_bytes in enumerate(images):
            try:
                extracted = await asyncio.wait_for(
                    asyncio.to_thread(_extract_image, img_bytes),
                    timeout=60.0
                )
                parts.append(f"[Image {i+1}]: {extracted}")
            except asyncio.TimeoutError:
                parts.append(f"[Image {i+1}]: Could not extract (timeout)")
            except Exception as e:
                parts.append(f"[Image {i+1}]: Could not extract ({str(e)})")

        combined = "\n\n".join(parts)
        analysis = await asyncio.wait_for(
            asyncio.to_thread(_analyze, combined),
            timeout=60.0
        )

        save_entry(
            content_type=analysis.get("content_type", "other"),
            summary=analysis.get("summary", ""),
            tags=analysis.get("tags", []),
            folder=analysis.get("folder", "Personal"),
            raw_content=combined,
        )

        return _format(analysis)

    except asyncio.TimeoutError:
        return "❌ Timed out — try with fewer images"
    except Exception as e:
        return f"❌ Something went wrong: {str(e)}"


async def process_text(text: str) -> str:
    """Process a forwarded text post."""
    try:
        analysis = await asyncio.to_thread(_analyze, text)

        save_entry(
            content_type=analysis.get("content_type", "other"),
            summary=analysis.get("summary", ""),
            tags=analysis.get("tags", []),
            folder=analysis.get("folder", "Personal"),
            raw_content=text,
        )

        return _format(analysis)

    except Exception as e:
        return f"❌ Something went wrong: {str(e)}"
