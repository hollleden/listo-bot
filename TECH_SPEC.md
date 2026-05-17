# Listo Bot — Technical Design Document

**Version:** 1.0  
**Last updated:** 2026-05-17  
**Status:** Active development

---

## 1. Overview

Listo is a single-user Telegram bot that functions as a personal knowledge capture and organization tool. Users forward or send media (images, videos) and text; the bot uses an AI pipeline to extract, summarize, classify, and persist that content, then surfaces it through scheduled digests.

---

## 2. Architecture

```
Telegram
   │
   ▼
listo.py  (aiogram dispatcher + APScheduler)
   │
   ├── pipeline.py  (AI extraction + analysis)
   │      ├── _extract_image()   → Mistral vision
   │      ├── _extract_video()   → Mistral vision (frames) or Gemini File API
   │      └── _analyze()         → Mistral text → JSON
   │
   ├── enrichment.py  (DuckDuckGo web search helpers)
   │
   ├── database.py  (Supabase REST via httpx)
   │
   └── digest.py  (weekly + quarterly summaries via Mistral text)
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| `listo.py` | Receives Telegram updates, routes by message type, buffers media groups, runs scheduler |
| `pipeline.py` | Orchestrates AI calls: extract raw content → analyze → format for Telegram + DB |
| `database.py` | All Supabase reads and writes via httpx REST client |
| `enrichment.py` | Optional DuckDuckGo lookups (Goodreads, IMDb, Maps, YouTube, press reviews) |
| `digest.py` | Pulls entries from DB, builds digest text, calls AI for quarterly insight |

---

## 3. Data flow

### 3.1 Image message

```
User sends photo
  → handle_photo()
  → download file bytes via Bot.download_file()
  → _extract_image(bytes)  →  Mistral vision: transcribe + describe
  → _analyze(raw_text)     →  Mistral text: classify + summarize → JSON
  → database.save_entry()  →  POST to Supabase
  → format_result()        →  send formatted message to user
```

### 3.2 Media group (album)

```
Multiple photos arrive within ~1.5 s
  → buffered in media_group_buffer{}
  → flush_media_group() fires after 1.5 s delay
  → _extract_image() called per photo → texts concatenated
  → single _analyze() call on combined text
  → save + reply
```

### 3.3 Video / document

```
User sends video
  → handle_video()
  → download bytes
  → _extract_video(bytes)
      → write to tmp .mp4
      → upload to AI provider File API (currently Gemini; Mistral TBD)
      → poll until PROCESSING complete
      → generate_content with video file object
  → _analyze() → JSON → save → reply
```

> **Note:** Video is the one pipeline stage still dependent on Gemini's File API. Mistral has no native video understanding. Options: keep Gemini for video only, or extract frames via ffmpeg and pass as images (loses audio transcription).

### 3.4 Text message

```
User sends text (≥ 20 chars)
  → handle_text()
  → prepend forward context if forwarded
  → _analyze(full_text) → JSON → save → reply
```

### 3.5 Digest

```
APScheduler fires (Sunday 10:00 or quarterly)
  → get_entries_since(7 | 90) from Supabase
  → _build_digest() groups entries by content_type
  → quarterly only: _get_quarterly_insight() → Mistral text
  → bot.send_message()
```

---

## 4. AI pipeline detail

### 4.1 Extraction (`pipeline.py`)

**Image extraction prompt** — instructs the model to return three labeled sections:
- `AUDIO TRANSCRIPT` — spoken words verbatim
- `ON-SCREEN TEXT` — text overlays with timestamps
- `VISUAL DESCRIPTION` — brief scene description

**Video extraction prompt** — similar intent; uses provider File API to pass video natively.

### 4.2 Analysis (`_analyze`)

Sends raw extracted content to the model with a strict JSON schema:

```json
{
  "content_type": "book|place|recipe|philosophy|spanish|film|health|retail|other",
  "title": "string",
  "summary": "2-4 sentences",
  "tags": ["string"],
  "folder": "Crecer|Descanso|Salud|Creatividad|Dinero|Trabajo|Curación|Personal",
  "key_points": ["string"],
  "fact_check": "string",
  "enrichment": "string"
}
```

Response is stripped of markdown fences before `json.loads()`. Nested dict values in scalar fields are coerced to JSON strings as a safety guard.

### 4.3 Concurrency control

A single `asyncio.Semaphore(1)` (`_api_semaphore`) serializes all AI calls. This avoids rate-limit errors at the cost of queuing — acceptable for a single-user bot.

---

## 5. Database schema

All persistence is in Supabase (PostgreSQL). The bot communicates via Supabase REST API using `httpx` with bearer auth.

### `entries` table

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key, auto-generated |
| `user_id` | bigint | Telegram user ID |
| `media_type` | text | `image`, `video`, `text` |
| `content_type` | text | One of 9 AI-classified types |
| `title` | text | AI-generated |
| `summary` | text | AI-generated, 2–4 sentences |
| `tags` | text | JSON array serialized as string |
| `folder` | text | One of 8 folder names |
| `fact_check` | text | One-sentence AI fact-check |
| `enrichment` | text | Optional external data |
| `raw_content` | text | Full extracted text |
| `created_at` | timestamptz | Auto-set by Supabase |

### `users` table (inferred)

| Column | Type | Notes |
|---|---|---|
| `user_id` | bigint | Primary key |
| `token` | text | Auth token for web access |

---

## 6. Authentication & access control

- The bot enforces `ALLOWED_ID` at every handler entry point — all messages from other users are silently dropped.
- Web API access uses token-based auth: `ensure_user_token()` generates a UUID token stored in Supabase; `get_user_by_token()` validates it on each request.

---

## 7. Scheduling

APScheduler runs in-process alongside the bot polling loop.

| Job | Trigger | Args |
|---|---|---|
| `send_weekly_digest` | Every Sunday at 10:00 | `bot`, `ALLOWED_ID` |
| `send_quarterly_digest` | Jan 1, Apr 1, Jul 1, Oct 1 at 10:00 | `bot`, `ALLOWED_ID` |

---

## 8. Error handling

- All three `process_*` functions catch all exceptions and return a fallback dict with `"error"` key and `content_type: "other"` — the bot always replies, never silently fails.
- AI analysis has a 60-second timeout via `asyncio.wait_for`.
- Video extraction has a polling loop with 3-second sleep intervals until the provider signals processing complete.

---

## 9. Environment variables

| Variable | Used in | Purpose |
|---|---|---|
| `BOT_TOKEN` | `listo.py` | Telegram bot token |
| `ALLOWED_ID` | `listo.py` | Single authorized Telegram user ID |
| `MISTRAL_API_KEY` | `pipeline.py`, `digest.py` | Mistral API authentication |
| `SUPABASE_URL` | `database.py` | Supabase project REST endpoint |
| `SUPABASE_KEY` | `database.py` | Supabase anon or service role key |

---

## 10. Known limitations & open issues

| Issue | Impact | Status |
|---|---|---|
| Video depends on Gemini File API | Cannot migrate fully to Mistral without workaround | Open |
| Single semaphore serializes all AI calls | Latency under concurrent use (no real issue for single-user bot) | Accepted |
| `MessageOriginHiddenUser` import missing in `listo.py` | Will raise `NameError` at runtime if a hidden-user forward is received | Bug — needs fix |
| Tags stored as JSON string, not native array | Complicates search queries | Accepted |
| No retry logic on Supabase calls | Transient failures return empty results silently | Open |
