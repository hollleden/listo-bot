import re
import urllib.parse
from ddgs import DDGS


def search_goodreads(title: str, author: str = "") -> dict:
    query = f"{title} {author} goodreads".strip()
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            if "goodreads.com/book" in r.get("href", ""):
                rating = None
                match = re.search(r"(\d\.\d+)\s*(avg|rating|out of 5)", r.get("body", ""), re.IGNORECASE)
                if match:
                    rating = match.group(1)
                return {"url": r["href"], "rating": rating}
    except Exception:
        pass
    return {}


def search_press_reviews(title: str, author: str = "") -> list:
    query = f"{title} {author} review".strip()
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))
        links = []
        for r in results:
            href = r.get("href", "")
            if any(d in href for d in ["newyorker.com", "nytimes.com", "theatlantic.com", "theguardian.com"]):
                links.append(href)
        return links[:2]
    except Exception:
        return []


def search_imdb(title: str, year: str = "") -> dict:
    query = f"{title} {year} imdb".strip()
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            if "imdb.com/title" in r.get("href", ""):
                rating = None
                match = re.search(r"(\d\.\d)/10", r.get("body", ""))
                if match:
                    rating = match.group(1)
                return {"url": r["href"], "rating": rating}
    except Exception:
        pass
    return {}


def search_exhibition(name: str, venue: str = "", direct_url: str = "") -> dict:
    # If post already contains a direct URL, use it — skip search entirely
    if direct_url and direct_url.startswith("http"):
        return {"url": direct_url, "snippet": ""}

    query = f"{name} {venue} official".strip()
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))

        # Hard skip: noise domains and non-Latin sites
        skip = [
            "wikipedia", "facebook", "instagram", "twitter", "tiktok",
            "zhihu", "weibo", "baidu", "vk.com", "ok.ru",
            "tripadvisor", "yelp", "eventbrite",
        ]
        for r in results:
            href = r.get("href", "")
            if not href:
                continue
            if any(s in href for s in skip):
                continue
            # Prefer results where exhibition name appears in the URL or title
            title_lower = r.get("title", "").lower()
            name_words = [w.lower() for w in name.split() if len(w) > 3]
            if any(w in href.lower() or w in title_lower for w in name_words):
                return {"url": href, "snippet": r.get("body", "")}

        # Fallback: first non-skip result
        for r in results:
            href = r.get("href", "")
            if href and not any(s in href for s in skip):
                return {"url": href, "snippet": r.get("body", "")}
    except Exception:
        pass
    return {}


def search_youtube(title: str) -> dict:
    query = f"{title} site:youtube.com"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            if "youtube.com/watch" in r.get("href", ""):
                return {
                    "url": r["href"],
                    "title": r.get("title", title),
                    "confident": True,
                }
        # fallback — no youtube.com/watch found, return best guess
        if results:
            return {
                "url": results[0].get("href", ""),
                "title": results[0].get("title", title),
                "confident": False,
            }
    except Exception:
        pass
    return {}


def google_maps_link(place) -> str:
    if not place:
        return ""
    if isinstance(place, list):
        place = place[0] if place else ""
    place = str(place).strip()
    if not place:
        return ""
    return f"https://maps.google.com/?q={urllib.parse.quote(place)}"
