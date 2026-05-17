# Listo Bot — API Documentation

**Version:** 1.0  
**Last updated:** 2026-05-17

This document covers the internal Python API — the public-facing functions across each module that other modules or a companion web app can call.

---

## `database.py`

All functions communicate with Supabase via `httpx`. Authentication uses the `SUPABASE_KEY` environment variable as a bearer token.

---

### `save_entry(user_id, media_type, result)`

Persists a processed entry to the `entries` table.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |
| `media_type` | `str` | `"image"`, `"video"`, or `"text"` |
| `result` | `dict` | Full analysis dict from `pipeline._analyze()` |

**`result` keys used**

| Key | Type | Description |
|---|---|---|
| `content_type` | `str` | AI-classified type (e.g. `"book"`) |
| `title` | `str` | AI-generated title |
| `summary` | `str` | 2–4 sentence summary |
| `tags` | `str` | JSON-serialized list of tag strings |
| `folder` | `str` | Assigned folder name |
| `fact_check` | `str` | One-sentence fact-check |
| `enrichment` | `str` | Optional enrichment data |
| `raw_content` | `str` | Full extracted text |

**Returns:** `None`  
**Raises:** `httpx.HTTPStatusError` on Supabase error

---

### `get_today_count(user_id)`

Returns the number of entries saved today by the user.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |

**Returns:** `int`

---

### `get_entries_since(days)`

Returns all entries created within the last `days` days.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `days` | `int` | Number of days to look back |

**Returns:** `list[tuple]` — each tuple: `(content_type, summary, tags, folder, created_at)`

---

### `get_recent_entries(user_id)`

Returns the 10 most recent entries for the user.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |

**Returns:** `list[dict]` — full entry rows from Supabase

---

### `search_entries(user_id, query)`

Full-text search across `summary`, `tags`, and `raw_content` fields.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |
| `query` | `str` | Search string |

**Returns:** `list[dict]` — matching entry rows

---

### `delete_entry(entry_id, user_id)`

Deletes a single entry, scoped to the user.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `entry_id` | `str` | UUID of the entry |
| `user_id` | `int` | Telegram user ID (used as ownership check) |

**Returns:** `None`  
**Raises:** `httpx.HTTPStatusError` on failure

---

### `ensure_user_token(user_id)`

Returns the existing auth token for a user, or generates and stores a new UUID token if none exists.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |

**Returns:** `str` — UUID token

---

### `get_user_by_token(token)`

Validates a token and returns the associated user ID.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `token` | `str` | UUID token |

**Returns:** `int | None` — user ID if valid, `None` if not found

---

### `get_entries_web(user_id, folder, search)`

Retrieves entries for web display, with optional filtering.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |
| `folder` | `str \| None` | Filter by folder name, or `None` for all |
| `search` | `str \| None` | Search string, or `None` for no search |

**Returns:** `list[dict]` — entry rows

---

### `get_web_stats(user_id)`

Returns aggregate statistics for the web dashboard.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID |

**Returns:** `dict`

```json
{
  "total": 142,
  "this_week": 7,
  "top_folder": "Creatividad"
}
```

---

## `pipeline.py`

The AI processing pipeline. All `process_*` functions are async and return a dict. They never raise — exceptions are caught and returned as an error dict.

---

### `process_media(file_bytes, media_type, caption)`

Main entry point for image and video messages.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `file_bytes` | `bytes` | Raw file content downloaded from Telegram |
| `media_type` | `str` | `"image"` or `"video"` |
| `caption` | `str` | Optional caption or forward context (default `""`) |

**Returns:** `dict` — analysis result (see [Analysis result schema](#analysis-result-schema))

**Example**
```python
result = await process_media(file_bytes, media_type="image", caption="Forwarded from: MyChannel")
```

---

### `process_media_group(images, caption)`

Processes multiple images as a single entry.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `images` | `list[bytes]` | List of raw image byte arrays |
| `caption` | `str` | Optional caption (default `""`) |

**Returns:** `dict` — analysis result

---

### `process_text(text)`

Processes a plain text message.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `text` | `str` | Full text content including any forward context prefix |

**Returns:** `dict` — analysis result

---

### `format_result(result)`

Formats an analysis dict into a human-readable Telegram message string.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `result` | `dict` | Analysis result dict |

**Returns:** `str` — formatted message with emoji labels and hashtags

**Example output**
```
📚 Book | 📁 Crecer

**How to Think Better**
A practical guide to improving decision-making by slowing down System 1 thinking.

• Recognise cognitive biases before acting
• Use pre-mortems for important decisions

🔍 Claims align with mainstream behavioural economics research.

#thinking #decisions #psychology
```

---

### `extract_db_fields(result)`

Extracts only the fields needed for `database.save_entry()`.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `result` | `dict` | Full analysis result dict |

**Returns:** `dict` with keys: `summary`, `tags`, `folder`, `fact_check`, `enrichment`, `title`

---

### Analysis result schema

All `process_*` functions return a dict with these keys:

| Key | Type | Description |
|---|---|---|
| `content_type` | `str` | One of 9 content types |
| `title` | `str` | Short punchy title |
| `summary` | `str` | 2–4 sentence summary |
| `tags` | `list[str]` | Up to 5 tags |
| `folder` | `str` | One of 8 folder names |
| `key_points` | `list[str]` | Up to 4 key points |
| `fact_check` | `str` | One-sentence accuracy note |
| `enrichment` | `str` | Optional external data |
| `raw_content` | `str` | Full extracted text |

**Error result** (returned when pipeline fails):

| Key | Value |
|---|---|
| `error` | Exception message string |
| `content_type` | `"other"` |
| `title` | `"Error"` |
| `summary` | Exception message string |
| `tags` | `[]` |
| `folder` | `"Personal"` |
| `fact_check` | `""` |
| `enrichment` | `""` |
| `raw_content` | `""` or original text |

---

## `enrichment.py`

Utility functions for fetching external metadata. All functions are synchronous and return empty results on failure rather than raising.

---

### `search_goodreads(title)`

Finds a Goodreads page for a book and extracts its rating.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `title` | `str` | Book title |

**Returns:** `dict` — `{"url": str, "rating": str}` or `{}`

---

### `search_press_reviews(title)`

Searches for press reviews from major publications.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `title` | `str` | Content title |

**Returns:** `list[dict]` — each item `{"title": str, "url": str}`, up to 3 results, or `[]`

---

### `search_imdb(title)`

Finds an IMDb page and rating for a film or series.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `title` | `str` | Film or series title |

**Returns:** `dict` — `{"url": str, "rating": str}` or `{}`

---

### `search_exhibition(title)`

Searches for exhibition information for art/cultural content.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `title` | `str` | Exhibition or artwork title |

**Returns:** `dict` — `{"url": str}` or `{}`

---

### `search_youtube(title)`

Finds a YouTube video link with a confidence score.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `title` | `str` | Video title |

**Returns:** `dict` — `{"url": str, "confidence": float}` or `{}`

---

### `google_maps_link(location)`

Generates a Google Maps search URL for a location string.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `location` | `str` | Place name or address |

**Returns:** `str` — URL-encoded Google Maps search link

---

## `digest.py`

Digest generation and delivery. Functions are called by APScheduler in `listo.py`.

---

### `send_weekly_digest(bot, chat_id)` *(async)*

Fetches entries from the past 7 days and sends a grouped digest.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `bot` | `aiogram.Bot` | Active bot instance |
| `chat_id` | `int` | Telegram user ID to send to |

**Returns:** `None`  
Sends "Nothing saved this week!" if no entries exist.

---

### `send_quarterly_digest(bot, chat_id)` *(async)*

Fetches entries from the past 90 days, builds a digest, and appends an AI-generated insight paragraph.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `bot` | `aiogram.Bot` | Active bot instance |
| `chat_id` | `int` | Telegram user ID to send to |

**Returns:** `None`  
Sends nothing if no entries exist.

---

## `listo.py`

Entry point — not intended to be imported. Exposes no public API. Registers handlers on the aiogram Dispatcher and starts polling.

### Bot handlers

| Handler | Trigger | Condition |
|---|---|---|
| `start()` | `/start` command | ALLOWED_ID only |
| `handle_photo()` | `F.photo` | ALLOWED_ID only |
| `handle_video()` | `F.video \| F.document` | ALLOWED_ID only |
| `handle_text()` | `F.text` | ALLOWED_ID only, ≥ 20 chars |

### Internal helpers

| Function | Description |
|---|---|
| `_forward_context(message)` | Extracts source label from forwarded messages |
| `flush_media_group(media_group_id, chat_id)` | Async task that fires 1.5 s after the first photo in a group arrives |
