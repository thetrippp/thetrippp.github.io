import requests
from bs4 import BeautifulSoup
from google import genai
import json
import os
from datetime import datetime, timedelta

# --- 1. SETUP ---
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
            for article in articles[:3]: 
                title = article.title.text if article.title else ""
                all_news_text += f"- {title}\n"
    except Exception as e:
        print(f"Skipping {source} due to error.")

# --- 3. GENERATE CURRENT BRIEFING (Upgraded Prompt) ---
print("Generating current intelligence briefing...")
prompt = f"""
You are a Geopolitical Analyst. Review the following global news headlines.
Instead of a wall of text, structure your briefing using HTML tags with clear demarcation.
Use this exact structure:
<h3>🌍 Top Global Priorities</h3>
<ul>
  <li><strong>[Topic 1]:</strong> [1-2 sentences explaining what is happening and why it matters]</li>
  <li><strong>[Topic 2]:</strong> [1-2 sentences explaining what is happening and why it matters]</li>
  <li><strong>[Topic 3]:</strong> [1-2 sentences explaining what is happening and why it matters]</li>
</ul>
<h3>🔍 Emerging Threads</h3>
<p>[A brief paragraph noting any interesting underlying connections between the news items.]</p>

Data: {all_news_text}
"""
current_briefing = client.models.generate_content(model='gemini-2.5-flash', contents=prompt).text

# --- 4. MEMORY & WEEKLY RECAP (Upgraded Prompt) ---
print("Managing history and generating weekly recap...")
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
You are a Senior Analyst. Review this log of intelligence briefings from the past week. 
Write a high-level "Weekly Recap". Do not write a massive paragraph. 
Use HTML formatting. Start with a brief <p> summarizing the week's tone, then use an <ul> with <li> tags for the 3-4 major evolving storylines. Use <strong> tags for emphasis.
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
        /* Modern Dark Mode Theme */
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
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
        
        h1 {{ 
            text-align: center; 
            color: #ffffff; 
            font-size: 2.5em;
            margin-bottom: 5px;
        }}
        
        h2 {{ color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; }}
        h3 {{ color: #ffffff; margin-top: 25px; }}
        
        .header-container {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .date-badge {{ 
            display: inline-block;
            background-color: var(--border);
            color: var(--text-main);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .card {{ 
            background: var(--card-bg); 
            padding: 30px; 
            margin-bottom: 30px; 
            border-radius: 12px; 
            border: 1px solid var(--border);
            box-shadow: 0 8px 24px rgba(0,0,0,0.2); 
        }}
        
        /* Styling the AI's generated HTML */
        .ai-content ul {{
            padding-left: 20px;
        }}
        
        .ai-content li {{
            margin-bottom: 15px;
            padding-left: 5px;
        }}
        
        .ai-content strong {{
            color: var(--accent);
        }}
        
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Global Intelligence Matrix</h1>
        <div class="date-badge">Last Sync: {today_str}</div>
    </div>
    
    <div class="card">
        <h2>⚡ Live Briefing</h2>
        <div class="ai-content">
            {current_briefing}
        </div>
    </div>

    <div class="card">
        <h2>🗓️ 7-Day Context & Trajectory</h2>
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