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

# --- 3. THE MASTERCLASS NEWSROOM ---
for cat_name, feeds in categories.items():
    print(f"\n--- Processing {cat_name} Deep Dive ---")
    
    # Scrape massive amounts of data (Top 12 from each site)
    cat_news_text = ""
    for source, url in feeds.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, features="xml")
                articles = soup.find_all("item")
                cat_news_text += f"\n--- {source} ---\n"
                for article in articles[:12]: 
                    title = article.title.text if article.title else ""
                    desc = article.description.text if article.description else ""
                    cat_news_text += f"Headline: {title} | Details: {desc}\n"
        except Exception as e:
            print(f"Skipping {source}")

    print("Generating Long-Form Analysis...")
    prompt = f"""
    You are an elite, award-winning investigative journalist for {cat_name}. 
    Your reader is a highly intelligent professional who only checks the news once a day and wants deep, exhaustive explanations rather than quick summaries.
    
    TASK 1: THE DAILY MASTERCLASS
    Identify the 4 most complex and important events from the News Data. Write a long-form, magazine-style deep dive for each.
    Use EXACTLY this HTML structure to format your response:
    
    <div class="story-box">
        <h3 class="story-title">[Specific Event Name]</h3>
        
        <h4 class="section-head">The Current Situation</h4>
        <p>[A detailed, multi-sentence paragraph explaining exactly what is happening right now].</p>
        
        <h4 class="section-head">Historical & Technical Context</h4>
        <p>[A deep paragraph explaining the history leading up to this, the underlying causes, or the complex technical background. Assume the reader needs the foundational knowledge].</p>
        
        <h4 class="section-head">Key Players & Motivations</h4>
        <p>[Identify the main countries, companies, or individuals involved and explain *why* they are taking these actions. What do they stand to gain or lose?].</p>
        
        <h4 class="section-head">The Ripple Effect</h4>
        <p>[Explain the broader impact on the global economy, the specific industry, or everyday life. What is the worst-case and best-case scenario moving forward?].</p>
    </div>
    
    TASK 2: THE WEEKLY TRAJECTORY
    Review the History Log. Write a multi-paragraph synthesis analyzing how the macro-trends in this industry/domain have shifted over the last week. Use <p> and <strong> tags.
    
    CRITICAL INSTRUCTION:
    Separate your response for Task 1 and Task 2 with exactly this text: |||DIVIDER|||
    Do not use markdown blocks like ```html. Just return raw text/HTML.
    
    News Data: {cat_news_text}
    
    History Log: {history[cat_name]}
    """
    
    try:
        response_text = client.models.generate_content(model='gemini-2.5-flash', contents=prompt).text
        parts = response_text.split("|||DIVIDER|||")
        
        daily_briefing_html = parts[0].replace("```html", "").replace("```", "").strip()
        weekly_recap_html = parts[1].replace("```html", "").replace("```", "").strip() if len(parts) > 1 else "<p>Recap generating...</p>"
        
        history[cat_name].append({"date": today_str, "briefing": daily_briefing_html})
        if len(history[cat_name]) > 28:
            history[cat_name] = history[cat_name][-28:]
            
        safe_id = "".join(e for e in cat_name if e.isalnum())
        tab_buttons_html += f'<button class="tablinks" onclick="openTab(event, \'{safe_id}\')">{cat_name}</button>\n'
        tab_content_html += f"""
        <div id="{safe_id}" class="tabcontent">
            <div class="card">
                <h2>📚 The Daily Masterclass</h2>
                <div class="ai-content">{daily_briefing_html}</div>
            </div>
            <div class="card">
                <h2>🧵 Macro-Trend Analysis</h2>
                <div class="ai-content">{weekly_recap_html}</div>
            </div>
        </div>
        """
        print("Success!")
    except Exception as e:
        print(f"Failed to generate content for {cat_name}: {e}")
        
    time.sleep(3) 

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
        :root {{ --bg-color: #0d1117; --card-bg: #161b22; --text-main: #c9d1d9; --text-muted: #8b949e; --accent: #58a6ff; --accent-green: #3fb950; --border: #30363d; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.8; max-width: 1000px; margin: 0 auto; padding: 40px 20px; background-color: var(--bg-color); color: var(--text-main); }}
        h1 {{ text-align: center; color: #ffffff; font-size: 2.5em; margin-bottom: 5px; }}
        h2 {{ color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-top: 30px;}}
        
        .header-container {{ text-align: center; margin-bottom: 30px; }}
        .date-badge {{ display: inline-block; background-color: var(--border); color: var(--text-main); padding: 5px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; margin-top: 10px;}}
        
        .tab {{ display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .tab button {{ background-color: var(--card-bg); border: 1px solid var(--border); color: var(--text-muted); padding: 12px 24px; cursor: pointer; border-radius: 8px; font-size: 1em; font-weight: 600; transition: all 0.3s ease; }}
        .tab button:hover {{ background-color: #30363d; color: #fff; }}
        .tab button.active {{ background-color: var(--accent); color: #0d1117; border-color: var(--accent); box-shadow: 0 0 10px rgba(88,166,255,0.3); }}
        .tabcontent {{ display: none; animation: fadeEffect 0.5s; }}
        @keyframes fadeEffect {{ from {{opacity: 0; transform: translateY(10px);}} to {{opacity: 1; transform: translateY(0);}} }}
        
        .card {{ background: var(--card-bg); padding: 40px; margin-bottom: 30px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }}
        
        /* New Deep-Dive Styling */
        .story-box {{ background: rgba(48, 54, 61, 0.4); border-left: 5px solid var(--accent); padding: 30px; margin-bottom: 40px; border-radius: 0 12px 12px 0; }}
        .story-title {{ color: #ffffff; font-size: 1.8em; margin-top: 0; margin-bottom: 20px; border-bottom: 1px dashed var(--border); padding-bottom: 10px; }}
        .section-head {{ color: var(--accent-green); font-size: 1.1em; text-transform: uppercase; letter-spacing: 1px; margin-top: 25px; margin-bottom: 10px; }}
        
        .ai-content p {{ margin-bottom: 20px; font-size: 1.05em; color: #e6edf3; }}
        .ai-content strong {{ color: var(--accent); }}
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Omni-Channel Intelligence</h1>
        <p style="color: var(--text-muted);">Your Daily Executive Masterclass.</p>
        <div class="date-badge">Last Sync: {today_str}</div>
    </div>
    <div class="tab">{tab_buttons_html}</div>
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