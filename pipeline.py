import os
import base64
import json
import tempfile
import asyncio
import time
import google.generativeai as genai
import anthropic
from database import save_entry

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
    model = genai.GenerativeModel("gemini-2.0-flash")
    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(file_bytes).decode(),
    }
    prompt = (
        "Extract ALL text from this screenshot verbatim. "
        "Then describe what is shown in the image."
    )
    response = model.generate_content([prompt, image_part])
    return response.text


def _extract_video(file_bytes: bytes) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(file_bytes)
        tmp_path = f.name

    try:
        video_file = genai.upload_file(tmp_path, mime_type="video/mp4")
        while video_file.state.name == "PROCESSING":
            time.sleep(3)
            video_file = genai.get_file(video_file.name)

        prompt = (
            "Extract ALL text from subtitles and overlays in this video. "
            "Transcribe all speech. Describe what is happening."
        )
        response = model.generate_content([prompt, video_file])
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

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # На случай если Claude всё же добавил markdown блоки
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
        fc_lines.append(f"{fc['verdict']} _{fc['claim']}_ — {fc['note']}")
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
        f"📝 *Summary*\n{summary}\n\n"
        f"🏷 {tags}\n\n"
        f"✅ *Fact-check*\n{fact_check_text}"
    )

    if enrich_text:
        result += f"\n\n🔎 *Details*\n{enrich_text}"

    return result


async def process_media(file_bytes: bytes, media_type: str) -> str:
    try:
        if media_type == "image":
            raw_content = await asyncio.to_thread(_extract_image, file_bytes)
        else:
            raw_content = await asyncio.to_thread(_extract_video, file_bytes)

        analysis = await asyncio.to_thread(_analyze, raw_content)

        save_entry(
            content_type=analysis.get("content_type", "other"),
            summary=analysis.get("summary", ""),
            tags=analysis.get("tags", []),
            folder=analysis.get("folder", "Personal"),
            raw_content=raw_content,
        )

        return _format(analysis)

    except Exception as e:
        return f"❌ Something went wrong: {str(e)}"
