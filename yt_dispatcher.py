import os
import json
import requests
import feedparser

# Load Configuration from Environment / GitHub Secrets
WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1565748100042068110/1vGcgrVBHmmRN4UHGeAMOYc26WFHMRQpSIrYARv6R0VC8qjDiJJn8ro9ahoY2LKhdFqQ")
CHANNELS_RAW = os.getenv("FAVORITE_CHANNELS", "NightMind")
API_KEY = os.getenv("YOUTUBE_API_KEY", "")
KEYWORD_FILTER = os.getenv("KEYWORD_FILTER", "")
PING_OPTION = os.getenv("PING_OPTION", "none")
BOT_NAME = os.getenv("BOT_NAME", "YouTube Dispatcher Bot")
BOT_AVATAR = os.getenv("BOT_AVATAR", "https://cdn-icons-png.flaticon.com/512/1384/1384060.png")
EMBED_COLOR = int(os.getenv("EMBED_COLOR", "16711680"))
TITLE_CASE = os.getenv("TITLE_CASE", "original").lower()

# Cache file to remember previously posted video IDs across workflow runs
CACHE_FILE = "last_seen_videos.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning reading cache file: {e}")
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving cache: {e}")

def fetch_latest_video_rss(channel_id):
    """Fetch latest video for a channel using YouTube RSS XML feeds."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    
    if feed.entries:
        latest = feed.entries[0]
        video_id = latest.yt_videoid if hasattr(latest, 'yt_videoid') else latest.id.split(":")[-1]
        
        title = latest.title
        if TITLE_CASE == "uppercase":
            title = title.upper()
        elif TITLE_CASE == "lowercase":
            title = title.lower()

        return {
            "id": video_id,
            "title": title,
            "url": latest.link,
            "author": feed.feed.title if hasattr(feed.feed, 'title') else "YouTube Creator",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        }
    return None

def send_discord_webhook(video):
    """Send styled notification embed to Discord Webhook URL."""
    if not WEBHOOK_URL:
        print("❌ Error: WEBHOOK_URL environment variable is missing.")
        return

    mention = ""
    if PING_OPTION == "everyone":
        mention = "@everyone "
    elif PING_OPTION == "here":
        mention = "@here "

    payload = {
        "username": BOT_NAME,
        "avatar_url": BOT_AVATAR,
        "content": mention.strip() if mention else None,
        "embeds": [
            {
                "title": video["title"],
                "url": video["url"],
                "color": EMBED_COLOR,
                "author": {"name": video["author"]},
                "image": {"url": video["thumbnail"]},
                "footer": {"text": "24/7 Webhook Dispatcher Engine"}
            }
        ]
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print(f"✅ Successfully dispatched alert for: '{video['title']}'")
        else:
            print(f"❌ Failed to dispatch webhook (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Exception when sending webhook: {e}")

def main():
    if not CHANNELS_RAW:
        print("⚠️ No channels specified in FAVORITE_CHANNELS secret. (Format: UC1234...,UC5678...)")
        return

    channels = [c.strip() for c in CHANNELS_RAW.split(",") if c.strip()]
    cache = load_cache()
    keywords = [k.strip().lower() for k in KEYWORD_FILTER.split(",") if k.strip()]

    print(f"🔍 Checking {len(channels)} channel(s) for new uploads...")

    for channel_id in channels:
        video = fetch_latest_video_rss(channel_id)
        if not video:
            print(f"⚠️ Could not fetch feed for channel ID: {channel_id}")
            continue

        prev_id = cache.get(channel_id)
        
        # If channel is seen for the first time, set baseline without alerting
        if prev_id is None:
            print(f"📌 Initialized baseline for {video['author']} ('{video['title']}'). Future new uploads will alert.")
            cache[channel_id] = video["id"]
            continue

        if prev_id == video["id"]:
            print(f"ℹ️ {video['author']}: No new uploads.")
            continue

        # Keyword filtering check
        if keywords:
            title_lower = video["title"].lower()
            if not any(k in title_lower for k in keywords):
                print(f"⏭️ Skipped '{video['title']}' (Keyword filter mismatch)")
                cache[channel_id] = video["id"]
                continue

        # Trigger notification and update cache for genuine new upload
        send_discord_webhook(video)
        cache[channel_id] = video["id"]

    save_cache(cache)

if __name__ == "__main__":
    main()
