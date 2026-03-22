import os
import json
import tempfile
import asyncio
import time
from google import genai
from google.genai import types
from database import save_entry

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

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
        os.unlink(tmp_path)


def _analyze(raw_content: str) -> dict:
    prompt = f"""You are an assistant for organizing saved content from TikTok, Reels, and Telegram.

Content:
{raw_content}

Return a JSON with these fields:
{{
  "content_type": "book|place|recipe|philosophy|spanish|film|health|other",
  "summary": "2-4 sentence summary in English",
  "tags": ["tag1", "tag2", "tag3"],
  "folder": "Crecer|Descanso|Salud|Creatividad|Dinero|Trabajo|Personal",
  "fact_check": [
    {{"claim": "factual claim", "verdict": "True|Disputed|False|Cannot verify", "note": "explanation"}}
  ],
  "enrichment": {{}}
}}

Folder rules:
- Books, philosophy, Spanish, growth -> Crecer
- Travel, places -> Descanso
- Health, recipes, body -> Salud
- Films, creativity -> Creatividad
- Money -> Dinero
- Work -> Trabajo
- Other -> Personal

Enrichment by type:
- book: {{"author": "", "year": "", "genre": "", "goodreads_rating": ""}}
- place: {{"country": "", "city": "", "best_season": "", "approx_budget": ""}}
- recipe: {{"cook_time": "", "difficulty": "easy|medium|hard", "key_ingredients": [], "dietary": ""}}
- philosophy: {{"school": "", "key_thinker": "", "opposite_view": ""}}
- spanish: {{"level": "A1|A2|B1|B2|C1", "key_words": []}}
- film: {{"year": "", "genre": "", "imdb_rating": "", "where_to_watch": ""}}
- health: {{"topic": "", "evidence_level": "scientific|popular|anecdotal"}}

Return ONLY valid JSON. No markdown. No extra text."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _format(analysis: dict) -> str:
    ct = analysis.get("content_type", "other")
    type_label = CONTENT_TYPES.get(ct, "📌 Other")
    folder = analysis.get("folder", "Personal")
    summary = analysis.get("summary", "")
    tags = " ".join([f"#{t.replace(' ', '_').lower()}" for t in analysis.get("tags", [])])

    fc_lines = []
    for fc in analysis.get("fact_check", []):
        fc_lines.append(f"- {fc.get('verdict', '')}: {fc.get('claim', '')} — {fc.get('note', '')}")
    fact_check_text = "\n".join(fc_lines) if fc_lines else "No specific facts to verify"

    enrich = analysis.get("enrichment", {})
    enrich_lines = [
        f"- {k}: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in enrich.items()
        if v and v != "" and v != []
    ]
    enrich_text = "\n".join(enrich_lines)

    result = f"{type_label} | 📁 {folder}\n\n📝 Summary\n{summary}\n\n🏷 {tags}\n\nFact-check\n{fact_check_text}"
    if enrich_text:
        result += f"\n\nDetails\n{enrich_text}"
    return result


async def process_media(file_bytes: bytes, media_type: str) -> str:
    try:
        if media_type == "image":
            raw = await asyncio.wait_for(asyncio.to_thread(_extract_image, file_bytes), timeout=60.0)
        else:
            raw = await asyncio.wait_for(asyncio.to_thread(_extract_video, file_bytes), timeout=120.0)

        analysis = await asyncio.wait_for(asyncio.to_thread(_analyze, raw), timeout=60.0)
        save_entry(analysis.get("content_type", "other"), analysis.get("summary", ""),
                   analysis.get("tags", []), analysis.get("folder", "Personal"), raw)
        return _format(analysis)
    except asyncio.TimeoutError:
        return "Timed out — please try again"
    except Exception as e:
        return f"Something went wrong: {str(e)}"


async def process_media_group(images: list[bytes]) -> str:
    try:
        parts = []
        for i, img_bytes in enumerate(images):
            try:
                extracted = await asyncio.wait_for(asyncio.to_thread(_extract_image, img_bytes), timeout=60.0)
                parts.append(f"[Image {i+1}]: {extracted}")
            except Exception as e:
                parts.append(f"[Image {i+1}]: Could not extract ({str(e)})")

        combined = "\n\n".join(parts)
        analysis = await asyncio.wait_for(asyncio.to_thread(_analyze, combined), timeout=60.0)
        save_entry(analysis.get("content_type", "other"), analysis.get("summary", ""),
                   analysis.get("tags", []), analysis.get("folder", "Personal"), combined)
        return _format(analysis)
    except asyncio.TimeoutError:
        return "Timed out — try with fewer images"
    except Exception as e:
        return f"Something went wrong: {str(e)}"


async def process_text(text: str) -> str:
    try:
        analysis = await asyncio.wait_for(asyncio.to_thread(_analyze, text), timeout=60.0)
        save_entry(analysis.get("content_type", "other"), analysis.get("summary", ""),
                   analysis.get("tags", []), analysis.get("folder", "Personal"), text)
        return _format(analysis)
    except Exception as e:
        return f"Something went wrong: {str(e)}"
