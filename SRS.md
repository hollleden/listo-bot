# Listo Bot — Software Requirements Specification

**Version:** 1.0  
**Last updated:** 2026-05-17  
**Status:** Active

---

## 1. Introduction

### 1.1 Purpose

This document defines the functional and non-functional requirements for Listo Bot, a personal Telegram bot that captures, processes, and organizes content using AI.

### 1.2 Scope

Listo Bot is a single-user application deployed as a Heroku worker. It receives Telegram messages, processes them through an AI pipeline, stores results in a Supabase database, and delivers scheduled digests. A companion web interface is partially supported through token-authenticated database queries.

### 1.3 Definitions

| Term | Definition |
|---|---|
| Entry | A single piece of saved content with AI-generated metadata |
| Pipeline | The sequence: extract raw content → AI analysis → database persistence |
| Digest | A scheduled summary message of recent entries |
| Folder | One of 8 organizational categories assigned by the AI |
| Content type | One of 9 content classifications assigned by the AI |
| ALLOWED_ID | The Telegram user ID of the sole authorized user |

---

## 2. Overall description

### 2.1 Product perspective

Listo is a standalone Telegram bot. It has no web frontend of its own but exposes database query functions that a companion web app can use via token authentication.

### 2.2 User profile

A single individual who:
- Uses Telegram daily
- Frequently saves content from social media (TikTok, Reels, Telegram channels)
- Wants automatic organization without manual tagging
- Reads in English and Spanish

### 2.3 Constraints

- Single-user only (enforced via `ALLOWED_ID`)
- Requires active internet connection for all AI and database operations
- AI video processing is currently dependent on Gemini File API (Mistral migration pending)
- Bot is always-on (worker dyno); no request-response web server

---

## 3. Functional requirements

### 3.1 Message handling

**FR-01 — Image processing**  
The bot MUST accept photo messages from the authorized user, extract visual and textual content using a vision AI model, analyze the content, and reply with a structured summary.

**FR-02 — Media group processing**  
The bot MUST handle albums (multiple photos in a single send). It MUST buffer photos belonging to the same `media_group_id` for 1.5 seconds, then process them together as a single entry.

**FR-03 — Video processing**  
The bot MUST accept video and document messages, extract speech, subtitles, and visual description using a video-capable AI model, analyze the content, and reply with a structured summary.

**FR-04 — Text processing**  
The bot MUST accept text messages of 20 or more characters, analyze them using an AI text model, and reply with a structured summary. Messages shorter than 20 characters MUST be silently ignored.

**FR-05 — Forward context**  
The bot MUST detect forwarded messages and prepend the source context (channel name, sender name, or "hidden user") to the content before processing.

**FR-06 — Unauthorized user rejection**  
The bot MUST silently ignore all messages from users whose Telegram ID does not match `ALLOWED_ID`.

**FR-07 — Start command**  
The bot MUST respond to `/start` with a welcome message describing its capabilities.

### 3.2 AI analysis

**FR-08 — Content classification**  
For every entry, the AI MUST assign one of the following content types: `book`, `place`, `recipe`, `philosophy`, `spanish`, `film`, `health`, `retail`, `other`.

**FR-09 — Folder assignment**  
For every entry, the AI MUST assign one of the following folders: `Crecer`, `Descanso`, `Salud`, `Creatividad`, `Dinero`, `Trabajo`, `Curación`, `Personal`.

**FR-10 — Metadata generation**  
For every entry, the AI MUST generate: a title, a 2–4 sentence summary, up to 5 tags, up to 4 key points, and a one-sentence fact-check.

**FR-11 — JSON output integrity**  
The pipeline MUST parse AI JSON output and coerce any unexpectedly nested dict values in scalar fields to JSON strings before persistence.

### 3.3 Persistence

**FR-12 — Entry saving**  
Every successfully processed message MUST be saved to the Supabase `entries` table with all AI-generated fields, raw content, media type, and user ID.

**FR-13 — Error resilience**  
If AI processing or database saving fails, the bot MUST reply to the user with an error message. It MUST NOT crash or silently drop the message.

### 3.4 Digests

**FR-14 — Weekly digest**  
Every Sunday at 10:00 the bot MUST send the authorized user a digest of entries saved in the past 7 days, grouped by content type.

**FR-15 — Quarterly digest**  
On January 1, April 1, July 1, and October 1 at 10:00 the bot MUST send a digest of entries from the past 90 days, including an AI-generated paragraph about the user's interests.

**FR-16 — Empty digest suppression**  
If there are no entries in the relevant period, the weekly digest MUST send "Nothing saved this week!" The quarterly digest MUST send nothing.

### 3.5 Web access

**FR-17 — Token generation**  
The system MUST generate a unique UUID token for each user on first access and store it in Supabase.

**FR-18 — Token validation**  
The system MUST validate tokens and return the associated user ID, enabling a companion web app to make authenticated queries.

**FR-19 — Web entry retrieval**  
The system MUST support retrieval of entries with optional folder filtering and text search.

**FR-20 — Web statistics**  
The system MUST be able to return total entry count, weekly entry count, and most-used folder for a given user.

---

## 4. Non-functional requirements

### 4.1 Performance

**NFR-01** — Single image messages MUST be acknowledged (typing indicator or "Reading…" reply) within 2 seconds of receipt.

**NFR-02** — AI analysis MUST complete within 60 seconds; calls exceeding this MUST be cancelled and return an error entry.

**NFR-03** — Video processing MAY take up to 120 seconds due to provider upload and processing time. The bot MUST inform the user ("Processing video, ~20 seconds…").

### 4.2 Reliability

**NFR-04** — The bot MUST remain running continuously as a Heroku worker dyno.

**NFR-05** — All AI pipeline entry points MUST catch all exceptions and return a valid fallback response — no unhandled exceptions that kill the polling loop.

### 4.3 Security

**NFR-06** — All handlers MUST validate `ALLOWED_ID` before any processing.

**NFR-07** — API keys (`MISTRAL_API_KEY`, `SUPABASE_KEY`, `BOT_TOKEN`) MUST be loaded from environment variables and MUST NOT be committed to the repository.

**NFR-08** — Web API access MUST require a valid token; no unauthenticated data access.

### 4.4 Maintainability

**NFR-09** — The AI model identifier MUST be defined as a single `MODEL` constant per file, not scattered across function calls.

**NFR-10** — AI provider client initialization MUST be at module level so it can be swapped in one place per file.

### 4.5 Scalability

**NFR-11** — The system is explicitly single-user. Concurrent-user scaling is out of scope. The semaphore-based serialization of AI calls is an accepted design choice.

---

## 5. Content type taxonomy

| Type | Description |
|---|---|
| `book` | Books, articles, reading recommendations |
| `place` | Restaurants, travel destinations, locations |
| `recipe` | Food recipes, cooking tips |
| `philosophy` | Ideas, quotes, personal development |
| `spanish` | Spanish-language content or language learning |
| `film` | Films, series, video content |
| `health` | Fitness, wellness, medical information |
| `retail` | Products, shopping, retail items |
| `other` | Anything that doesn't fit the above |

## 6. Folder taxonomy

| Folder | Intended use |
|---|---|
| `Crecer` | Personal growth |
| `Descanso` | Rest, leisure, travel |
| `Salud` | Health and wellness |
| `Creatividad` | Creative projects and inspiration |
| `Dinero` | Finance and money |
| `Trabajo` | Work and career |
| `Curación` | Curated content and culture |
| `Personal` | Default / personal miscellaneous |

---

## 7. Out of scope

- Multi-user support
- Web frontend (companion app is external)
- Voice message processing
- GIF processing
- Editing or deleting saved entries via Telegram
- Real-time search via Telegram commands
