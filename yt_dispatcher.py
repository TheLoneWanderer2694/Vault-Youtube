import os
import json
import requests
import feedparser

# GitHub Secrets / Environment Variables
WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1565748100042068110/1vGcgrVBHmmRN4UHGeAMOYc26WFHMRQpSIrYARv6R0VC8qjDiJJn8ro9ahoY2LKhdFqQ", "").strip()
CHANNELS_RAW = os.getenv("FAVORITE_CHANNELS", "UCihko5ga4v76RMM7ppF_XpA").strip()
CACHE_FILE = "last_seen.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Cache load warning: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Cache save error: {e}")

def get_latest_video(channel_id):
    """Fetches video data directly from YouTube's public XML RSS feed."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    
    if feed.entries:
        entry = feed.entries[0]
        video_id = entry.yt_videoid if hasattr(entry, 'yt_videoid') else entry.id.split(":")[-1]
        channel_name = feed.feed.title if hasattr(feed.feed, 'title') else "YouTube Creator"
        
        return {
            "id": video_id,
            "title": entry.title,
            "url": entry.link,
            "channel_name": channel_name,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        }
    return None

def send_discord_webhook(video):
    """Posts a rich embed alert to your Discord channel."""
    if not WEBHOOK_URL:
        print("❌ ERROR: WEBHOOK_URL environment variable is missing!")
        return False

    payload = {
        "username": "YouTube Dispatcher",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/1384/1384060.png",
        "embeds": [
            {
                "title": video["title"],
                "url": video["url"],
                "color": 16711680, # Red hex
                "author": { "name": video["channel_name"] },
                "image": { "url": video["thumbnail"] },
                "footer": { "text": "24/7 Automated Webhook Bot" }
            }
        ]
    }

    try:
        res = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if res.status_code in [200, 204]:
            print(f"✅ Dispatched alert: {video['channel_name']} - {video['title']}")
            return True
        else:
            print(f"❌ Webhook failed (HTTP {res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"❌ Webhook request exception: {e}")
        return False

def main():
    if not WEBHOOK_URL:
        print("❌ ERROR: Missing WEBHOOK_URL secret in GitHub Secrets.")
        return

    if not CHANNELS_RAW:
        print("❌ ERROR: Missing FAVORITE_CHANNELS secret in GitHub Secrets.")
        return

    channels = [c.strip() for c in CHANNELS_RAW.split(",") if c.strip()]
    cache = load_cache()

    print(f"🚀 Running 24/7 Feed Check for {len(channels)} channels...")

    for channel_id in channels:
        video = get_latest_video(channel_id)
        if not video:
            print(f"⚠️ Could not read RSS feed for channel: {channel_id}")
            continue

        prev_id = cache.get(channel_id)

        # Baseline logic: If first time checking channel, record latest video without sending alert
        if prev_id is None:
            print(f"📌 Established baseline for {video['channel_name']}: '{video['title']}'. (Next upload will trigger alert)")
            cache[channel_id] = video["id"]
            continue

        # If latest video matches cache, no new upload
        if prev_id == video["id"]:
            print(f"ℹ️ {video['channel_name']}: No new videos.")
            continue

        # New video detected!
        if send_discord_webhook(video):
            cache[channel_id] = video["id"]

    save_cache(cache)

if __name__ == "__main__":
    main()
