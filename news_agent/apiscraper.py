import requests
from bs4 import BeautifulSoup
from google import genai
import json
import os
from datetime import datetime

# --- 1. SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GEMINI_API_KEY)

# A curated list of highly reliable, context-heavy global sources
rss_feeds = {
    "BBC World (UK/Global)": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "NPR (US/Context)": "https://feeds.npr.org/1004/rss.xml",
    "Al Jazeera (Middle East/Global)": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Guardian (Europe/Global)": "https://www.theguardian.com/world/rss",
    "Deutsche Welle (Germany)": "https://rss.dw.com/rdf/rss-en-world",
    "United Nations News": "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
}

# --- 2. SCRAPING DATA ---
print("Scraping global feeds...")
all_news_text = ""
for source, url in rss_feeds.items():
    try:
        # Added a browser header so news sites don't block our scraper
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, features="xml")
            articles = soup.find_all("item")
            all_news_text += f"\n--- {source} ---\n"
            for article in articles[:4]: # Pulling 4 per site for more data
                title = article.title.text if article.title else ""
                desc = article.description.text if article.description else ""
                all_news_text += f"- {title}: {desc}\n"
    except Exception as e:
        print(f"Skipping {source} due to error: {e}")

# --- 3. GENERATE CURRENT BRIEFING (The "Teacher" Prompt) ---
print("Generating educational briefing...")
prompt = f"""
You are a brilliant, patient geopolitics teacher. Your student is a smart adult who has not followed politics closely and wants to understand what their friends are talking about. 
Review the following global news data. Choose the 3 or 4 most important global storylines.

For each storyline, use this exact HTML structure to explain it simply and clearly, avoiding unnecessary jargon:

<div class="story-box">
    <h3>🌍 [Name of the Topic/Conflict/Event]</h3>
    <ul>
        <li><strong>What is happening right now:</strong> [Explain the current event in 1-2 simple sentences].</li>
        <li><strong>The Background Context:</strong> [Explain the history or WHY this is happening. Assume the user knows nothing about it].</li>
        <li><strong>Why it matters (The Ripple Effect):</strong> [Explain how this impacts the wider world, the economy, or why people are talking about it].</li>
    </ul>
</div>

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
You are a patient geopolitics teacher. Review this log of the past week's news. 
Write a short HTML summary titled "The Weekly Thread". Explain how the biggest story of the week evolved from Monday to today. 
Keep it under 3 paragraphs. Use <p> and <strong> tags.
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
    <title>AI Intelligence Hub</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --border: #30363d;
        }}
        
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            line-height: 1.7; 
            max-width: 850px; 
            margin: 0 auto; 
            padding: 40px 20px; 
            background-color: var(--bg-color); 
            color: var(--text-main); 
        }}
        
        h1 {{ text-align: center; color: #ffffff; font-size: 2.5em; margin-bottom: 5px; }}
        h2 {{ color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-top: 40px; }}
        h3 {{ color: #ffffff; margin-top: 0; padding-bottom: 5px; border-bottom: 1px dashed var(--border); }}
        
        .header-container {{ text-align: center; margin-bottom: 40px; }}
        .date-badge {{ display: inline-block; background-color: var(--border); color: var(--text-main); padding: 5px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }}
        
        .card {{ background: var(--card-bg); padding: 30px; margin-bottom: 30px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }}
        
        .story-box {{
            background: rgba(48, 54, 61, 0.3);
            border-left: 4px solid var(--accent);
            padding: 20px;
            margin-bottom: 25px;
            border-radius: 0 8px 8px 0;
        }}

        .ai-content ul {{ padding-left: 20px; margin-top: 10px; }}
        .ai-content li {{ margin-bottom: 12px; }}
        .ai-content strong {{ color: var(--accent-green); }}
        
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Global Context Dashboard</h1>
        <p style="color: var(--text-muted);">Curated & Explained by AI</p>
        <div class="date-badge">Last Sync: {today_str}</div>
    </div>
    
    <div class="card">
        <h2>📚 The Daily Breakdown</h2>
        <p style="color: var(--text-muted); font-size: 0.9em;"><em>The most important stories today, explained from the ground up.</em></p>
        <div class="ai-content">
            {current_briefing}
        </div>
    </div>

    <div class="card">
        <h2>🧵 The Weekly Thread</h2>
        <p style="color: var(--text-muted); font-size: 0.9em;"><em>How the major narratives are evolving over time.</em></p>
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