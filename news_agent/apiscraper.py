## AIzaSyCFY3Wpo9_EA0l3U3YilLp1XX701d8GHTY

import requests
from bs4 import BeautifulSoup
from google import genai
import json
import os
from datetime import datetime, timedelta

# --- 1. SETUP ---
# It will securely get your key from GitHub Actions later
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GEMINI_API_KEY)

rss_feeds = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=political-general&type=latest"
}

# --- 2. SCRAPING DATA ---
print("Scraping global feeds...")
all_news_text = ""
for source, url in rss_feeds.items():
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, features="xml")
            articles = soup.find_all("item")
            all_news_text += f"\n--- {source} ---\n"
            for article in articles[:3]: # Top 3 per site to avoid overwhelming the AI
                title = article.title.text if article.title else ""
                all_news_text += f"- {title}\n"
    except Exception as e:
        print(f"Skipping {source} due to error.")

# --- 3. GENERATE CURRENT BRIEFING ---
print("Generating current intelligence briefing...")
prompt = f"""
You are a Geopolitical Analyst. Based on these headlines, write a 3-paragraph executive summary of the current global situation. Use HTML tags (like <h3>, <p>, <ul>, <li>) to format your response nicely.
Data: {all_news_text}
"""
current_briefing = client.models.generate_content(model='gemini-2.5-flash', contents=prompt).text

# --- 4. MEMORY & WEEKLY RECAP ---
print("Managing history and generating weekly recap...")
history_file = "history.json"
history = []

# Load past history if it exists
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        history = json.load(f)

# Add today's briefing to history
today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
history.append({"date": today_str, "briefing": current_briefing})

# Keep only the last 28 entries (4 times a day * 7 days = 28)
if len(history) > 28:
    history = history[-28:]

# Save updated history
with open(history_file, "w") as f:
    json.dump(history, f)

# Generate Weekly Recap based on history
recap_prompt = f"""
You are a Senior Analyst. Here is a log of intelligence briefings from the last week. 
Write a high-level "Weekly Recap" summarizing the major evolving storylines. Use HTML formatting (<p>, <ul>).
History Log: {history}
"""
weekly_recap = client.models.generate_content(model='gemini-2.5-flash', contents=recap_prompt).text

# --- 5. WRITE TO INDEX.HTML ---
print("Writing to index.html...")
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My AI Intelligence Hub</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; color: #333; }}
        h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .date-badge {{ font-size: 0.9em; color: #7f8c8d; text-align: right; }}
    </style>
</head>
<body>
    <h1>🌍 Personal Intelligence Dashboard</h1>
    <p class="date-badge">Last Updated: {today_str}</p>
    
    <div class="card">
        <h2>🔥 Current Global Briefing (Updated every 6 hours)</h2>
        {current_briefing}
    </div>

    <div class="card">
        <h2>📅 The Weekly Recap (Evolving Storylines)</h2>
        {weekly_recap}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Done! Open index.html to see your new website.")