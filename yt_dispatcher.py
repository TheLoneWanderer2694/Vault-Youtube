import os
import requests
import feedparser

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
FAVORITE_CHANNELS = os.environ.get("FAVORITE_CHANNELS", "")

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

    for channel_id in channels:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            print(f"⚠️ No entries found for channel ID: {channel_id}")
            continue

        # Inspect the latest uploaded video
        latest_entry = feed.entries[0]
        video_title = latest_entry.title
        video_link = latest_entry.link
        channel_name = feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else "YouTube Channel"

        print(f"📺 Checked {channel_name}: Latest is '{video_title}'")
        
        # Dispatch notification (Note: Without a local cache file, this will alert on the current latest video every time it runs. Use this to verify your webhook instantly!)
        send_discord_webhook(video_title, video_link, channel_name)

if __name__ == "__main__":
    main()
