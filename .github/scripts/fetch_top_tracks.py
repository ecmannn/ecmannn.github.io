"""Fetches Evan's top Spotify tracks over two rolling windows -- the last
~4 weeks (short_term, "this month") and the last year (long_term, "this
year") -- resolving a YouTube video for each and writing both lists to
_data/spotify.json for the spotify-top-tracks.html include to render.

Runs in GitHub Actions (see .github/workflows/spotify-top-tracks.yml).
Required env: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
Optional env: YOUTUBE_API_KEY - if set, YouTube lookups use the official
Data API v3 instead of scraping the search page (more reliable).

The file is only rewritten when the track list or video IDs actually change,
so the workflow's commit-if-changed step skips no-op weeks.

Uses only the Python standard library; can also run locally from the repo
root with the three env vars exported.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

OUT_PATH = "_data/spotify.json"

# Two rolling Spotify windows. short_term is roughly the last 4 weeks
# ("this month"); long_term is roughly the last year ("this year").
MONTH_RANGE = "short_term"
MONTH_LIMIT = 10
YEAR_RANGE = "long_term"
YEAR_LIMIT = 25


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"Missing required env var: {name}")
    return value


def http_json(request: urllib.request.Request, context: str) -> dict:
    """Perform a request and parse the JSON body, exiting with a readable
    message on HTTP errors."""
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"{context} failed: {error.status} {error.read().decode(errors='replace')}")


def get_access_token() -> str:
    """Trade the long-lived refresh token for a short-lived access token."""
    client_id = require_env("SPOTIFY_CLIENT_ID")
    client_secret = require_env("SPOTIFY_CLIENT_SECRET")
    refresh_token = require_env("SPOTIFY_REFRESH_TOKEN")

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        },
    )
    return http_json(request, "Token refresh")["access_token"]


def get_top_tracks(access_token: str, time_range: str, limit: int) -> list:
    url = (
        "https://api.spotify.com/v1/me/top/tracks?"
        + urllib.parse.urlencode({"time_range": time_range, "limit": limit})
    )
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    return http_json(request, "Top-tracks request").get("items", [])


def youtube_id_via_api(query: str, api_key: str):
    """Official lookup: first video hit in YouTube's music category."""
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode({
        "part": "snippet",
        "type": "video",
        "videoCategoryId": "10",
        "maxResults": "1",
        "q": query,
        "key": api_key,
    })
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            items = json.load(response).get("items", [])
        return items[0]["id"]["videoId"] if items else None
    except (urllib.error.URLError, KeyError, IndexError):
        print("YouTube API lookup failed; falling back to scrape.")
        return None


def youtube_id_via_scrape(query: str):
    """Fallback lookup: first videoId embedded in the public search page."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    request = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": "CONSENT=YES+1",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode(errors="replace")
    except urllib.error.URLError:
        return None
    match = re.search(r'"videoId":"([\w-]{11})"', html)
    return match.group(1) if match else None


def resolve_youtube(artist: str, track: str) -> dict:
    query = f"{artist} - {track}"
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    video_id = youtube_id_via_api(query, api_key) if api_key else None
    if not video_id:
        video_id = youtube_id_via_scrape(query)

    # A search link keeps the widget useful when no video ID could be resolved
    if video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    else:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    return {"video_id": video_id, "url": url}


def build_track_list(items: list) -> list:
    """Shape Spotify track items into render-ready dicts, resolving a YouTube
    video for each."""
    tracks = []
    for rank, item in enumerate(items, start=1):
        artist = ", ".join(a["name"] for a in item["artists"])
        images = item.get("album", {}).get("images", [])
        youtube = resolve_youtube(item["artists"][0]["name"], item["name"])
        tracks.append({
            "rank": rank,
            "name": item["name"],
            "artist": artist,
            "album": item.get("album", {}).get("name", ""),
            # images arrive largest-first; index 1 is the 300px rendition
            "album_art": (images[1] if len(images) > 1 else images[0])["url"] if images else "",
            "spotify_url": item.get("external_urls", {}).get("spotify", ""),
            "youtube_video_id": youtube["video_id"],
            "youtube_url": youtube["url"],
        })
        note = f"(yt:{youtube['video_id']})" if youtube["video_id"] else "(no video match)"
        print(f"#{rank} {artist} - {item['name']} {note}")
    return tracks


def build_section(access_token: str, time_range: str, limit: int, label: str, required: bool) -> dict:
    """Fetch and shape one time-range section. An empty required section aborts
    the run (leaving existing data untouched); an empty optional one yields an
    empty list, which the include simply skips."""
    print(f"\n{label} ({time_range}):")
    items = get_top_tracks(access_token, time_range, limit)
    if not items and required:
        sys.exit(f"Spotify returned no {label} tracks; leaving existing data untouched.")
    return {"time_range": time_range, "tracks": build_track_list(items)}


def build_payload() -> dict:
    access_token = get_access_token()
    return {
        "fetched_at": date.today().isoformat(),
        "month": build_section(access_token, MONTH_RANGE, MONTH_LIMIT, "this month", required=True),
        "year": build_section(access_token, YEAR_RANGE, YEAR_LIMIT, "this year", required=False),
    }


payload = build_payload()

# Compare against the existing file with fetched_at masked, so an unchanged
# top 5 produces no diff and the workflow skips its commit
stable = lambda p: json.dumps({**p, "fetched_at": None}, sort_keys=True)
previous = None
if os.path.exists(OUT_PATH):
    try:
        with open(OUT_PATH) as handle:
            previous = json.load(handle)
    except (OSError, json.JSONDecodeError):
        previous = None

if previous is not None and stable(previous) == stable(payload):
    print(f"Top tracks unchanged since last run; not rewriting {OUT_PATH}")
    sys.exit(0)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print(f"Wrote {OUT_PATH}")
