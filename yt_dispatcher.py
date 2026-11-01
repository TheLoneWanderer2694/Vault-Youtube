import os
import json
import time
import requests
import feedparser

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
FAVORITE_CHANNELS = os.environ.get("FAVORITE_CHANNELS", "")
CACHE_FILE = "last_seen_videos.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache: {e}")
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def send_discord_webhook(video_title, video_link, channel_name):
    payload = {
        "content": f"📢 **New Video Upload from {channel_name}!**\n\n**{video_title}**\n{video_link}"
    }
    try:
        res = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        res.raise_for_status()
        print(f"✅ Dispatched alert for: {video_title}")
    except Exception as e:
        print(f"❌ Failed to send webhook: {e}")

def main():
    if not WEBHOOK_URL:
        print("❌ Missing WEBHOOK_URL secret.")
        return

    channels = [c.strip() for c in FAVORITE_CHANNELS.split(",") if c.strip()]
    if not channels:
        print("❌ No channels provided in FAVORITE_CHANNELS.")
        return

    cache = load_cache()
    updated = False

    for channel_id in channels:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            print(f"⚠️ No entries found for channel ID: {channel_id}")
            continue

        latest_entry = feed.entries[0]
        video_id = latest_entry.yt_videoid if hasattr(latest_entry, 'yt_videoid') else latest_entry.id
        video_title = latest_entry.title
        video_link = latest_entry.link
        channel_name = feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else "YouTube Channel"

        # First-run baseline: save without alerting
        if channel_id not in cache:
            print(f"📌 Setting initial baseline for {channel_name}: {video_id}")
            cache[channel_id] = video_id
            updated = True
            continue

        # Check for genuinely new video upload
        if cache[channel_id] != video_id:
            print(f"🚨 New video detected for {channel_name}: {video_title}")
            send_discord_webhook(video_title, video_link, channel_name)
            cache[channel_id] = video_id
            updated = True
        else:
            print(f"ℹ️ No new uploads for {channel_name}.")

    if updated:
        save_cache(cache)

if __name__ == "__main__":
    main()
