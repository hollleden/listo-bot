import os
import json
import tempfile
import asyncio
import time
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

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

# Only 1 request at a time to stay within 15 RPM free tier
_api_semaphore = asyncio.Semaphore(1)

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


# ---------------------------------------------------------------------------
# Extraction
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
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Step 1: Analyze — Gemini reads content, returns structured JSON
# ---------------------------------------------------------------------------

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
  "enrichment": {{}},
  "youtube_videos": [],
  "is_exhibition": false,
  "exhibition_name": "",
  "exhibition_venue": "",
  "exhibition_url": ""
}}

Folder rules:
- Books, philosophy, Spanish, growth -> Crecer
- Travel, places -> Descanso
- Health, recipes, body -> Salud
- Films, creativity -> Creatividad
- Money -> Dinero
- Work -> Trabajo
- Other -> Personal

Enrichment by type — extract from content only, do NOT invent external data like ratings or URLs:
- book: {{"title": "", "author": "", "year": "", "genre": ""}}
- place: {{"places": [{{"name": "", "city": "", "country": ""}}], "best_season": "", "approx_budget": ""}}
  If multiple places are mentioned, list ALL of them in "places". Always use a list, even for a single place.
- recipe: {{"cook_time": "", "difficulty": "easy|medium|hard", "key_ingredients": [], "dietary": ""}}
- philosophy: {{"school": "", "key_thinker": "", "opposite_view": ""}}
- spanish: {{"level": "A1|A2|B1|B2|C1", "key_words": []}}
- film: {{"title": "", "year": "", "genre": ""}}
- health: {{"topic": "", "evidence_level": "scientific|popular|anecdotal"}}

IMPORTANT for recipes: convert ALL measurements to metric. Use grams, ml, °C only. Never output cups, oz, °F, tbsp, tsp as final units.

youtube_videos: list any YouTube video titles mentioned or visible in the content. Empty array if none.
is_exhibition: true if content is about an art exhibition, museum show, gallery, or cultural event with a venue.
exhibition_name / exhibition_venue: fill if is_exhibition is true.
exhibition_url: if the post contains a direct URL to the event/exhibition website, put it here. Otherwise leave empty.

Return ONLY valid JSON. No markdown. No extra text."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Step 2: Enrich — real web lookups based on type and detected entities
# ---------------------------------------------------------------------------

def _enrich(analysis: dict) -> dict:
    ct = analysis.get("content_type", "other")
    enrich = analysis.get("enrichment", {})
    links = {}

    # Books
    if ct == "book":
        title = enrich.get("title", "")
        author = enrich.get("author", "")
        if title:
            gr = search_goodreads(title, author)
            if gr:
                links["goodreads"] = gr["url"]
                if gr.get("rating"):
                    enrich["goodreads_rating"] = gr["rating"]
            reviews = search_press_reviews(title, author)
            if reviews:
                links["press_reviews"] = reviews

    # Films
    elif ct == "film":
        title = enrich.get("title", "")
        year = enrich.get("year", "")
        if title:
            imdb = search_imdb(title, year)
            if imdb:
                links["imdb"] = imdb["url"]
                if imdb.get("rating"):
                    enrich["imdb_rating"] = imdb["rating"]

    # Places — generate a Maps link for each place mentioned
    elif ct == "place":
        places = enrich.get("places", [])
        # Fallback: old schema or plain string
        if not places:
            fallback = enrich.get("place_name") or enrich.get("city", "")
            if fallback:
                places = [{"name": str(fallback)}]
        maps_links = []
        for p in places:
            if isinstance(p, dict):
                name = p.get("name") or p.get("city", "")
            else:
                name = str(p)
            name = name.strip() if name else ""
            if name:
                url = google_maps_link(name)
                if url:
                    maps_links.append({"name": name, "url": url})
        if maps_links:
            links["google_maps"] = maps_links

    # YouTube videos
    youtube_titles = analysis.get("youtube_videos", [])
    if youtube_titles:
        found_videos = []
        for title in youtube_titles[:5]:
            result = search_youtube(title)
            if result and result.get("url"):
                found_videos.append({
                    "title": result.get("title", title),
                    "url": result["url"],
                    "confident": result.get("confident", False),
                })
            else:
                found_videos.append({
                    "title": title,
                    "url": None,
                    "confident": False,
                })
        analysis["found_youtube"] = found_videos

    # Exhibition / event
    if analysis.get("is_exhibition"):
        ex_name = analysis.get("exhibition_name", "")
        ex_venue = analysis.get("exhibition_venue", "")
        if ex_name:
            ex_url = analysis.get("exhibition_url", "")
            ex_result = search_exhibition(ex_name, ex_venue, direct_url=ex_url)
            if ex_result:
                analysis["exhibition_link"] = ex_result["url"]
                analysis["exhibition_snippet"] = ex_result.get("snippet", "")

    analysis["enrichment"] = enrich
    analysis["links"] = links
    return analysis


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

def _format_value(v):
    """Convert a value to a string representation suitable for display."""
    if isinstance(v, list):
        # For lists, convert each element to string.
        formatted_items = []
        for item in v:
            if isinstance(item, dict):
                # Format dict as key: value, key: value
                formatted_items.append("; ".join(f"{k}: {item[k]}" for k in item))
            else:
                formatted_items.append(str(item))
        return ", ".join(formatted_items)
    elif isinstance(v, dict):
        return "; ".join(f"{k}: {v[k]}" for k in v)
    else:
        return str(v)

def _format(analysis: dict) -> str:
    ct = analysis.get("content_type", "other")
    type_label = CONTENT_TYPES.get(ct, "📌 Other")
    folder = analysis.get("folder", "Personal")
    summary = analysis.get("summary", "")
    tags = " ".join([f"#{t.replace(' ', '_').lower()}" for t in analysis.get("tags", [])])

    fc_lines = []
    for fc in analysis.get("fact_check", []):
        verdict = fc.get("verdict", "")
        claim = fc.get("claim", "")
        note = fc.get("note", "")
        fc_lines.append(f"- {verdict}: {claim} — {note}")
    fact_check_text = "\n".join(fc_lines) if fc_lines else "No specific facts to verify"

    enrich = analysis.get("enrichment", {})
    enrich_lines = []
    for k, v in enrich.items():
        if v and v != "" and v != [] and k not in ("goodreads_rating", "imdb_rating"):
            formatted_v = _format_value(v)
            enrich_lines.append(f"- {k}: {formatted_v}")

    enrich_text = "\n".join(enrich_lines)

    # Links
    links = analysis.get("links", {})
    link_lines = []

    if "goodreads" in links:
        rating = enrich.get("goodreads_rating", "")
        rating_str = f" · {rating}/5" if rating else ""
        link_lines.append(f"📖 Goodreads{rating_str}: {links['goodreads']}")
    if "press_reviews" in links:
        for url in links["press_reviews"]:
            link_lines.append(f"📰 Press: {url}")
    if "imdb" in links:
        rating = enrich.get("imdb_rating", "")
        rating_str = f" · {rating}/10" if rating else ""
        link_lines.append(f"🎬 IMDb{rating_str}: {links['imdb']}")
    if "google_maps" in links:
        maps_data = links["google_maps"]
        if isinstance(maps_data, list):
            for m in maps_data:
                link_lines.append(f"📍 {m['name']}: {m['url']}")
        else:
            link_lines.append(f"📍 Maps: {maps_data}")

    # Exhibition
    if analysis.get("is_exhibition") and analysis.get("exhibition_link"):
        snippet = analysis.get("exhibition_snippet", "")
        dates_note = " *(даты не подтверждены)*" if not snippet else ""
        link_lines.append(f"🎨 Exhibition{dates_note}: {analysis['exhibition_link']}")
        if snippet:
            link_lines.append(f"   ↳ {snippet[:120]}")

    # YouTube
    youtube_videos = analysis.get("found_youtube", [])
    yt_lines = []
    for v in youtube_videos:
        if v.get("url"):
            conf_note = " *(возможно, это оно)*" if not v.get("confident") else ""
            yt_lines.append(f"🎥 {v['title']}{conf_note}\n→ {v['url']}")
        else:
            yt_lines.append(f"🎥 {v['title']} — не найдено на YouTube")

    result = f"{type_label} | 📁 {folder}\n\n📝 Summary\n{summary}\n\n🏷 {tags}\n\nFact-check\n{fact_check_text}"
    if enrich_text:
        result += f"\n\nDetails\n{enrich_text}"
    if link_lines:
        result += f"\n\n🔗 Links\n" + "\n".join(link_lines)
    if yt_lines:
        result += f"\n\n🎬 YouTube\n" + "\n\n".join(yt_lines)

    return result


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

async def _run_pipeline(raw_content: str) -> str:
    analysis = await asyncio.wait_for(asyncio.to_thread(_analyze, raw_content), timeout=60.0)
    if isinstance(analysis, list):
        analysis = analysis[0] if analysis else {}
    # Enrich runs outside the semaphore implicitly since it's IO-bound web search
    analysis = await asyncio.wait_for(asyncio.to_thread(_enrich, analysis), timeout=60.0)
    formatted = _format(analysis)
    # Save only after successful format
    save_entry(
        analysis.get("content_type", "other"),
        analysis.get("summary", ""),
        analysis.get("tags", []),
        analysis.get("folder", "Personal"),
        raw_content,
    )
    return formatted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process_media(file_bytes: bytes, media_type: str, caption: str = "") -> str:
    async with _api_semaphore:
        try:
            if media_type == "image":
                raw_media = await asyncio.wait_for(
                    asyncio.to_thread(_extract_image, file_bytes), timeout=60.0
                )
            else:
                raw_media = await asyncio.wait_for(
                    asyncio.to_thread(_extract_video, file_bytes), timeout=120.0
                )

            if caption:
                raw = f"[Post text — primary source]:\n{caption}\n\n[Media content — additional context]:\n{raw_media}"
            else:
                raw = raw_media

            return await _run_pipeline(raw)
        except asyncio.TimeoutError:
            return "⏱ Timed out — please try again"
        except Exception as e:
            return f"⚠️ Something went wrong: {str(e)}"


async def process_media_group(images: list[bytes], caption: str = "") -> str:
    async with _api_semaphore:
        try:
            total_calls = len(images) + 1
            if total_calls > 9:
                wait_minutes = (total_calls // 9) + 1
                return f"Too many images at once ({len(images)}). Please wait {wait_minutes} minute(s) and try again, or send fewer images."

            parts = []
            for i, img_bytes in enumerate(images):
                try:
                    extracted = await asyncio.wait_for(
                        asyncio.to_thread(_extract_image, img_bytes), timeout=60.0
                    )
                    parts.append(f"[Image {i+1}]: {extracted}")
                except Exception as e:
                    parts.append(f"[Image {i+1}]: Could not extract ({str(e)})")

            combined = "\n\n".join(parts)
            if caption:
                raw = f"[Post text — primary source]:\n{caption}\n\n[Media content — additional context]:\n{combined}"
            else:
                raw = combined

            return await _run_pipeline(raw)
        except asyncio.TimeoutError:
            return "⏱ Timed out — please try again"
        except Exception as e:
            return f"⚠️ Something went wrong: {str(e)}"


async def process_text(text: str) -> str:
    async with _api_semaphore:
        try:
            return await _run_pipeline(text)
        except Exception as e:
            return f"⚠️ Something went wrong: {str(e)}"
