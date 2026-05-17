# Listo Bot

Your personal second brain — a Telegram bot that reads, summarizes, tags, and organizes anything you save.

## What it does

Send Listo a photo, video, forwarded post, or plain text and it will:

- Transcribe speech and on-screen text from images and videos
- Generate a title, summary, tags, and key points
- Classify content into a category (book, place, recipe, film, health, etc.)
- Assign it to a folder (Crecer, Descanso, Salud, Creatividad, Dinero, Trabajo, Curación, Personal)
- Fact-check the claim in one sentence
- Save everything to your Supabase database
- Send you a weekly digest every Sunday and a quarterly insight every quarter

## Tech stack

| Layer | Technology |
|---|---|
| Bot framework | [aiogram 3](https://docs.aiogram.dev/) |
| AI model | Mistral (Pixtral for vision, text models for analysis) |
| Database | [Supabase](https://supabase.com/) (PostgreSQL via REST) |
| Web search enrichment | DuckDuckGo Search (`ddgs`) |
| Scheduler | APScheduler |
| Deployment | Heroku (worker dyno) |

## Project structure

```
listo-bot/
├── listo.py          # Bot entry point — handlers, scheduler, startup
├── pipeline.py       # AI processing — extract → analyze → format
├── digest.py         # Weekly and quarterly digest generation
├── database.py       # Supabase read/write operations
├── enrichment.py     # Web search helpers (Goodreads, IMDb, Maps, etc.)
├── requirements.txt  # Python dependencies
└── Procfile          # Heroku worker process definition
```

## Setup

### 1. Clone

```bash
git clone https://github.com/hollleden/listo-bot.git
cd listo-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment variables

Create a `.env` file in the root:

```env
BOT_TOKEN=your_telegram_bot_token
ALLOWED_ID=your_telegram_user_id
MISTRAL_API_KEY=your_mistral_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_key
```

`ALLOWED_ID` restricts the bot to a single Telegram user. Get your ID from [@userinfobot](https://t.me/userinfobot).

### 4. Supabase table

Your Supabase project needs an `entries` table with at minimum these columns:

| Column | Type |
|---|---|
| `id` | uuid (primary key) |
| `user_id` | bigint |
| `media_type` | text |
| `content_type` | text |
| `title` | text |
| `summary` | text |
| `tags` | text (JSON array as string) |
| `folder` | text |
| `fact_check` | text |
| `enrichment` | text |
| `raw_content` | text |
| `created_at` | timestamptz |

### 5. Run locally

```bash
python listo.py
```

### 6. Deploy to Heroku

```bash
heroku create your-app-name
heroku config:set BOT_TOKEN=... ALLOWED_ID=... MISTRAL_API_KEY=... SUPABASE_URL=... SUPABASE_KEY=...
git push heroku main
heroku ps:scale worker=1
```

## Usage

| Input | What Listo does |
|---|---|
| Single photo | Extracts text + visuals, analyzes, saves |
| Multiple photos (album) | Groups them, analyzes together |
| Video or document | Extracts audio + subtitles + scenes, analyzes, saves |
| Forwarded post | Prepends source context, then processes as text/media |
| Plain text (≥20 chars) | Analyzes and saves directly |
| `/start` | Shows welcome message |

## Digests

- **Weekly** — every Sunday at 10:00, grouped by content type
- **Quarterly** — Jan 1, Apr 1, Jul 1, Oct 1 at 10:00, includes an AI-generated insight about your interests

## License

MIT
