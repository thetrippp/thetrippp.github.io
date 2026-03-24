import requests
from bs4 import BeautifulSoup
from google import genai
import json
import os
from datetime import datetime

# --- 1. SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GEMINI_API_KEY)

# Expanded Data Sources categorized by topic in the names
rss_feeds = {
    # Geopolitics & World
    "BBC World (Geopolitics)": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "NPR (Context/World)": "https://feeds.npr.org/1004/rss.xml",
    "Al Jazeera (Global)": "https://www.aljazeera.com/xml/rss/all.xml",
    
    # Tech & AI
    "TechCrunch (Tech/AI)": "https://techcrunch.com/feed/",
    "Ars Technica (IT/Tech)": "http://feeds.arstechnica.com/arstechnica/index",
    
    # Gaming & Game Dev
    "Game Developer (Industry/Tech)": "https://www.gamedeveloper.com/rss.xml",
    "Polygon (Gaming)": "https://www.polygon.com/rss/index.xml",
    
    # Space & Stars
    "Space.com (Astronomy)": "https://www.space.com/feeds/all",
    "Universe Today (Space)": "https://www.universetoday.com/feed/"
}

# --- 2. SCRAPING DATA ---
print("Scraping global, tech, gaming, and space feeds...")
all_news_text = ""
for source, url in rss_feeds.items():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, features="xml")
            articles = soup.find_all("item")
            all_news_text += f"\n--- {source} ---\n"
            for article in articles[:3]: # 3 per site to keep the data rich but manageable
                title = article.title.text if article.title else ""
                desc = article.description.text if article.description else ""
                all_news_text += f"- {title}: {desc}\n"
    except Exception as e:
        print(f"Skipping {source} due to error: {e}")

# --- 3. GENERATE CURRENT BRIEFING (Categorized Prompt) ---
print("Generating multi-disciplinary briefing...")
prompt = f"""
You are a brilliant, patient tutor. Your student is a Game Developer who wants to understand geopolitics, but also needs to stay updated on Tech, AI, Gaming, and Space.
Review the following news data. Organize your briefing into four distinct sections.

For EACH section, pick the 1 or 2 most important storylines and use this exact HTML structure:

<div class="category-header"><h3>[Insert Section Emoji Here] [Section Name]</h3></div>
<div class="story-box">
    <h4>[Name of the Specific Event/Topic]</h4>
    <ul>
        <li><strong>What is happening:</strong> [1-2 simple sentences explaining the event].</li>
        <li><strong>Context & Impact:</strong> [Explain the background or why this matters. If it's tech/gaming, explain the industry impact. If geopolitics, explain the global ripple effect].</li>
    </ul>
</div>

Create these 4 sections:
1. 🌍 Global Geopolitics
2. 💻 Tech & Artificial Intelligence
3. 🎮 Gaming & Game Technology
4. 🚀 Space & Astronomy

Data: {all_news_text}
"""
current_briefing = client.models.generate_content(model='gemini-2.5-flash', contents=prompt).text

# --- 4. MEMORY & WEEKLY RECAP ---
print("Managing history...")
history_file = "history.json"
history = []

if os.path.exists(history_file):
    with open(history_file, "r") as f:
        history = json.load(f)

today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
history.append({"date": today_str, "briefing": current_briefing})

if len(history) > 28:
    history = history[-28:]

with open(history_file, "w") as f:
    json.dump(history, f)

recap_prompt = f"""
You are a tutor for a Game Developer. Review this log of the past week's news spanning Geopolitics, Tech, Gaming, and Space. 
Write a short HTML summary titled "The Weekly Thread". Highlight 3 major evolving storylines across any of these categories. 
Keep it concise. Use <p> and <ul> with <strong> tags.
History Log: {history}
"""
weekly_recap = client.models.generate_content(model='gemini-2.5-flash', contents=recap_prompt).text

# --- 5. WRITE TO INDEX.HTML (Dark Mode UI) ---
print("Writing to index.html...")
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Developer Dashboard</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --accent-purple: #bc8cff;
            --border: #30363d;
        }}
        
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            line-height: 1.7; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 40px 20px; 
            background-color: var(--bg-color); 
            color: var(--text-main); 
        }}
        
        h1 {{ text-align: center; color: #ffffff; font-size: 2.5em; margin-bottom: 5px; }}
        h2 {{ color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-top: 40px; }}
        h3 {{ color: #ffffff; margin-top: 0; padding-bottom: 5px; }}
        h4 {{ color: var(--accent-purple); margin-top: 0; margin-bottom: 10px; font-size: 1.2em; }}
        
        .header-container {{ text-align: center; margin-bottom: 40px; }}
        .date-badge {{ display: inline-block; background-color: var(--border); color: var(--text-main); padding: 5px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }}
        
        .card {{ background: var(--card-bg); padding: 30px; margin-bottom: 30px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }}
        
        .category-header {{ margin-top: 30px; border-bottom: 1px dashed var(--border); padding-bottom: 5px; margin-bottom: 15px; }}
        
        .story-box {{
            background: rgba(48, 54, 61, 0.3);
            border-left: 4px solid var(--accent);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 0 8px 8px 0;
        }}

        .ai-content ul {{ padding-left: 20px; margin-top: 10px; }}
        .ai-content li {{ margin-bottom: 12px; }}
        .ai-content strong {{ color: var(--accent-green); }}
        
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Omni-Channel Intelligence</h1>
        <p style="color: var(--text-muted);">Geopolitics, Tech, Gaming, & Space — Curated by AI</p>
        <div class="date-badge">Last Sync: {today_str}</div>
    </div>
    
    <div class="card">
        <h2>📚 The Daily Breakdown</h2>
        <div class="ai-content">
            {current_briefing}
        </div>
    </div>

    <div class="card">
        <h2>🧵 The Weekly Thread</h2>
        <div class="ai-content">
            {weekly_recap}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Done! Open index.html to see your new website.")