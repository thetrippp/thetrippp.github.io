import requests
from bs4 import BeautifulSoup
from google import genai
import json
import os
import time
from datetime import datetime

# --- 1. SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GEMINI_API_KEY)

categories = {
    "🌍 Geopolitics": {
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "NPR World": "https://feeds.npr.org/1004/rss.xml",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "Reuters": "https://www.reutersagency.com/feed/?best-topics=political-general&type=latest"
    },
    "💻 Tech & AI": {
        "TechCrunch": "https://techcrunch.com/feed/",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
        "Wired": "https://www.wired.com/feed/rss"
    },
    "🎮 Gaming": {
        "Game Developer": "https://www.gamedeveloper.com/rss.xml",
        "Polygon": "https://www.polygon.com/rss/index.xml",
        "IGN": "https://feeds.feedburner.com/ign/games-all"
    },
    "🚀 Space": {
        "Space.com": "https://www.space.com/feeds/all",
        "Universe Today": "https://www.universetoday.com/feed/",
        "NASA Breaking": "https://www.nasa.gov/rss/dyn/breaking_news.rss"
    }
}

# --- 2. MEMORY SETUP ---
history_file = "history.json"
history = {cat: [] for cat in categories.keys()}

if os.path.exists(history_file):
    try:
        with open(history_file, "r") as f:
            saved_history = json.load(f)
            if isinstance(saved_history, dict):
                history = saved_history
    except Exception as e:
        print("Could not load history, starting fresh.")

today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
tab_buttons_html = ""
tab_content_html = ""

# --- 3. THE EXPANDED NEWSROOM PIPELINE ---
for cat_name, feeds in categories.items():
    print(f"\n--- Processing {cat_name} Newsroom ---")
    
    # A. Scrape Massive Data (Top 10 per site now!)
    cat_news_text = ""
    for source, url in feeds.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, features="xml")
                articles = soup.find_all("item")
                cat_news_text += f"\n--- {source} ---\n"
                for article in articles[:10]: 
                    title = article.title.text if article.title else ""
                    desc = article.description.text if article.description else ""
                    cat_news_text += f"Headline: {title} | Details: {desc}\n"
        except Exception as e:
            print(f"Skipping {source}")

    # B. The Editor Agent: Pick the top 6 stories
    print("1. Editor Agent identifying the top 6 stories...")
    editor_prompt = f"""
    You are the Managing Editor for the {cat_name} desk. Review this raw news data.
    Identify the 6 most significant, distinct events/storylines happening right now.
    Return ONLY a plain list of 6 short titles (no bullet points, no asterisks, just the titles separated by a new line).
    Data: {cat_news_text}
    """
    editor_response = client.models.generate_content(model='gemini-2.5-flash-lite', contents=editor_prompt).text
    top_stories = [line.strip() for line in editor_response.strip().split('\n') if line.strip()][:6]
    time.sleep(5) # Strict 5-second sleep to respect the 15 RPM limit

    # C. The Journalist Agents: Deep dive into ALL 6 stories
    print(f"2. Journalist Agents writing deep dives on: {top_stories}")
    daily_briefing_html = ""
    for story in top_stories:
        journalist_prompt = f"""
        You are an elite investigative analyst for {cat_name}. 
        Write a comprehensive, extended deep dive on this specific topic: "{story}".
        Use this raw data as your source: {cat_news_text}
        
        If the data lacks background, use your expert knowledge to provide the Context and Impact.
        Use this exact HTML structure:
        <div class="story-box">
            <h4>{story}</h4>
            <ul>
                <li><strong>The Situation:</strong> [A highly detailed, objective explanation of what is happening right now].</li>
                <li><strong>The Deep Context:</strong> [The history, underlying causes, or technical background necessary to truly understand this].</li>
                <li><strong>The Broader Impact:</strong> [Why this matters, the ripple effects, and what to watch for next].</li>
            </ul>
        </div>
        """
        story_coverage = client.models.generate_content(model='gemini-2.5-flash-lite', contents=journalist_prompt).text
        daily_briefing_html += story_coverage + "\n"
        time.sleep(5) # Strict 5-second sleep to respect the 15 RPM limit

    # D. Update History
    history[cat_name].append({"date": today_str, "briefing": daily_briefing_html})
    if len(history[cat_name]) > 28:
        history[cat_name] = history[cat_name][-28:]

    # E. The Historian Agent: Weekly Thread
    print("3. Historian Agent compiling the weekly thread...")
    recap_prompt = f"""
    You are the Senior Historian for {cat_name}. Review this log of the past week's coverage. 
    Write an extended HTML summary highlighting how the major storylines have evolved. 
    Make it highly engaging and informative. Use <p> and <ul> with <strong> tags.
    History Log: {history[cat_name]}
    """
    weekly_recap = client.models.generate_content(model='gemini-2.5-flash-lite', contents=recap_prompt).text
    time.sleep(5) # Strict 5-second sleep to respect the 15 RPM limit

    # F. Build UI
    safe_id = "".join(e for e in cat_name if e.isalnum())
    tab_buttons_html += f'<button class="tablinks" onclick="openTab(event, \'{safe_id}\')">{cat_name}</button>\n'
    tab_content_html += f"""
    <div id="{safe_id}" class="tabcontent">
        <div class="card">
            <h2>📚 Today's Extended Coverage</h2>
            <div class="ai-content">{daily_briefing_html}</div>
        </div>
        <div class="card">
            <h2>🧵 The Weekly Trajectory</h2>
            <div class="ai-content">{weekly_recap}</div>
        </div>
    </div>
    """

# --- 4. SAVE HISTORY & COMPILE HTML ---
print("\nSaving history and compiling final website...")
with open(history_file, "w") as f:
    json.dump(history, f)

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omni-Channel Intelligence Hub</title>
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
            line-height: 1.8; 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 40px 20px; 
            background-color: var(--bg-color); 
            color: var(--text-main); 
        }}
        
        h1 {{ text-align: center; color: #ffffff; font-size: 2.5em; margin-bottom: 5px; }}
        h2 {{ color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; }}
        h4 {{ color: #ffffff; margin-top: 0; margin-bottom: 15px; font-size: 1.4em; letter-spacing: 0.5px; }}
        
        .header-container {{ text-align: center; margin-bottom: 30px; }}
        .date-badge {{ display: inline-block; background-color: var(--border); color: var(--text-main); padding: 5px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; margin-top: 10px;}}
        
        /* TABS CSS */
        .tab {{ display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .tab button {{
            background-color: var(--card-bg); border: 1px solid var(--border); color: var(--text-muted);
            padding: 12px 24px; cursor: pointer; border-radius: 8px; font-size: 1em; font-weight: 600; transition: all 0.3s ease;
        }}
        .tab button:hover {{ background-color: #30363d; color: #fff; }}
        .tab button.active {{ background-color: var(--accent); color: #0d1117; border-color: var(--accent); box-shadow: 0 0 10px rgba(88,166,255,0.3); }}
        
        .tabcontent {{ display: none; animation: fadeEffect 0.5s; }}
        @keyframes fadeEffect {{ from {{opacity: 0; transform: translateY(10px);}} to {{opacity: 1; transform: translateY(0);}} }}
        
        .card {{ background: var(--card-bg); padding: 35px; margin-bottom: 30px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }}
        
        .story-box {{
            background: rgba(48, 54, 61, 0.4); border-left: 4px solid var(--accent); padding: 25px; margin-bottom: 25px; border-radius: 0 12px 12px 0;
        }}

        .ai-content ul {{ padding-left: 20px; margin-top: 10px; list-style-type: square; }}
        .ai-content li {{ margin-bottom: 15px; }}
        .ai-content strong {{ color: var(--accent-green); font-size: 1.05em; }}
        
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Omni-Channel Intelligence</h1>
        <p style="color: var(--text-muted);">In-depth, multi-agent analysis for the modern professional.</p>
        <div class="date-badge">Last Sync: {today_str}</div>
    </div>
    
    <div class="tab">
        {tab_buttons_html}
    </div>

    {tab_content_html}

    <script>
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {{ tabcontent[i].style.display = "none"; }}
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {{ tablinks[i].className = tablinks[i].className.replace(" active", ""); }}
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }}
        document.addEventListener("DOMContentLoaded", function() {{ document.getElementsByClassName("tablinks")[0].click(); }});
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Done! Massive-scale Newsroom website successfully created.")