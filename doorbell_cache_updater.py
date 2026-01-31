#!/usr/bin/env python3

import os
import json
import datetime
import requests
import subprocess
import re

# ---------------- CONFIG ----------------

HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(HOME, "doorbell_cache")

META_FILE = os.path.join(CACHE_DIR, "songs.json")

DOWNLOAD_HOUR = 12       # 12:00 noon
DOWNLOAD_WEEKDAY = 4     # Friday (Mon=0)

CLIP_LENGTH = 15         # seconds for WAV clip

# ---------------- INIT ----------------

os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------- FUNCTIONS ----------------

def fetch_top10():
    """Fetch Billboard Hot 100 Top 10 songs from JSON mirror"""
    print("Fetching Billboard Top 10...")

    url = "https://raw.githubusercontent.com/KoreanThinker/billboard-json/main/billboard-hot-100/recent.json"
    r = requests.get(url, timeout=15)
    data = r.json()

    songs = []
    for i in range(10):
        entry = data["data"][i]
        title = entry.get("name")      # Fixed: use 'name' instead of 'song' or 'title'
        artist = entry.get("artist")
        if not title or not artist:
            print(f"Skipping entry {i+1} due to missing title or artist")
            continue
        songs.append({
            "rank": i + 1,
            "title": title,
            "artist": artist
        })

    return songs


def get_preview_url(title, artist):
    """Query iTunes Search API to get 30s preview URL"""
    query = f"{title} {artist}".replace(" ", "+")
    url = f"https://itunes.apple.com/search?term={query}&media=music&limit=1"

    r = requests.get(url, timeout=10)
    data = r.json()

    if data["resultCount"] == 0:
        return None

    return data["results"][0].get("previewUrl")


def load_meta():
    """Load previously cached song metadata"""
    if not os.path.exists(META_FILE):
        return {}
    with open(META_FILE) as f:
        return json.load(f)


def save_meta(meta):
    """Save metadata to JSON"""
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)


def download_and_convert(song, filename):
    """Download preview and convert to 15s WAV"""
    preview_url = get_preview_url(song['title'], song['artist'])
    if not preview_url:
        print(f"No preview found for: {song['title']} - {song['artist']}")
        return False

    temp_file = filename + ".m4a"
    # Download preview
    r = requests.get(preview_url, stream=True)
    with open(temp_file, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)

    # Convert to WAV and trim to CLIP_LENGTH
    subprocess.run([
        "ffmpeg", "-y",
        "-i", temp_file,
        "-t", str(CLIP_LENGTH),
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        filename
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove(temp_file)
    print(f"Saved WAV: {filename}")
    return True


def update_cache():
    """Check top 10 songs, download new/changed songs, store as WAV"""
    meta = load_meta()
    cached_titles = set(meta.keys())

    top10 = fetch_top10()
    updated = False

    for song in top10:
        key = f"{song['title']}|{song['artist']}"

        # Sanitize title for filename
        safe_title = re.sub(r'[^\w\d-]', '_', song['title'])
        filename = os.path.join(CACHE_DIR, f"{song['rank']}_{safe_title}.wav")

        if key in cached_titles and os.path.exists(meta[key]):
            print(f"Already cached: {song['title']} - {song['artist']}")
            continue  # Skip duplicates

        if download_and_convert(song, filename):
            meta[key] = filename
            updated = True

    if updated:
        meta['last_update'] = datetime.datetime.now().isoformat()
        save_meta(meta)
        print("Cache updated successfully!")
    else:
        print("No new songs to update.")


def should_update():
    """Return True if it's time to update (weekly)"""
    meta = load_meta()
    last_update = meta.get("last_update")
    if not last_update:
        return True

    last = datetime.datetime.fromisoformat(last_update)
    now = datetime.datetime.now()

    # Update only once per week at configured hour
    return now.weekday() == DOWNLOAD_WEEKDAY and now.hour >= DOWNLOAD_HOUR and last.date() != now.date()


# ---------------- MAIN ----------------

if __name__ == "__main__":

    if should_update():
        print("Updating doorbell audio cache...")
        update_cache()
    else:
        print("No update needed this week.")

