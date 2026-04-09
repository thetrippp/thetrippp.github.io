import requests
from bs4 import BeautifulSoup
from google import genai
import json
import re
import os
import time
from datetime import datetime

# --- 1. SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GEMINI_API_KEY)

possible_models = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash', 'gemini-flash-latest', 'gemini-pro-latest']
MODEL_NAME = None

print("Detecting available Gemini models...")
try:
    models_list = client.models.list()
    available_models_str = [m.name for m in models_list]
    print(f"Available models from API: {available_models_str}")
    
    cleaned_available = [m.replace('models/', '') for m in available_models_str]
    for model in possible_models:
        if model in cleaned_available:
            MODEL_NAME = model
            print(f"Selected model: {MODEL_NAME}")
            break
    
    if not MODEL_NAME:
        for m in cleaned_available:
            if 'flash' in m or 'pro' in m:
                MODEL_NAME = m
                print(f"Selected available model: {MODEL_NAME}")
                break
except Exception as e:
    print(f"Warning: Could not list models: {e}")

if not MODEL_NAME:
    MODEL_NAME = 'gemini-2.5-flash'
    print(f"Using fallback model: {MODEL_NAME}")

# --- MASSIVE GLOBAL EXPANSION ---
categories = {
    "🌍 Global Geopolitics": {
        "Reuters (Global)": "https://www.reutersagency.com/feed/?best-topics=political-general&type=latest",
        "BBC World (UK)": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Al Jazeera (Middle East)": "https://www.aljazeera.com/xml/rss/all.xml",
        "France 24 (Europe)": "https://www.france24.com/en/rss",
        "Deutsche Welle (Germany)": "https://rss.dw.com/rdf/rss-en-world",
        "South China Morning Post (Asia)": "https://www.scmp.com/rss/91/feed",
        "CNA (Singapore/Asia)": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511",
        "The Hindu (India)": "https://www.thehindu.com/news/international/feeder/default.rss",
        "ABC News (Australia)": "https://www.abc.net.au/news/feed/52278/rss.xml",
        "UN News (Global)": "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
    },
    "💻 Tech & AI": {
        "TechCrunch (US)": "https://techcrunch.com/feed/",
        "Ars Technica (US)": "http://feeds.arstechnica.com/arstechnica/index",
        "Wired (Global)": "https://www.wired.com/feed/rss",
        "Rest of World (Global Tech)": "https://restofworld.org/feed/"
    },
    "🎮 Gaming": {
        "Game Developer (Industry)": "https://www.gamedeveloper.com/rss.xml",
        "Polygon (Culture/News)": "https://www.polygon.com/rss/index.xml",
        "Eurogamer (Europe)": "https://www.eurogamer.net/feed/news",
        "IGN (Mainstream)": "https://feeds.feedburner.com/ign/games-all"
    },
    "🚀 Space": {
        "Space.com": "https://www.space.com/feeds/all",
        "Universe Today": "https://www.universetoday.com/feed/",
        "NASA Breaking": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "ESA (Europe Space)": "https://www.esa.int/rssfeed/Our_Activities/Space_News"
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
                # Safely merge old history into the new structure
                for key in history.keys():
                    # If the exact category name exists in the old file, keep it
                    if key in saved_history:
                        history[key] = saved_history[key]
                    # Data Migration: If we renamed Geopolitics to Global Geopolitics, map it over!
                    elif key == "🌍 Global Geopolitics" and "🌍 Geopolitics" in saved_history:
                        history[key] = saved_history["🌍 Geopolitics"]
    except Exception as e:
        print("Could not load history, starting fresh.")

today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
tab_buttons_html = ""
tab_content_html = ""
global_sync_success = True

def markdown_to_html(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    return text

# --- 3. THE MASTERCLASS NEWSROOM ---
for cat_name, feeds in categories.items():
    print(f"\n--- Processing {cat_name} Deep Dive ---")
    
    cat_news_text = ""
    for source, url in feeds.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, features="xml")
                articles = soup.find_all("item")
                cat_news_text += f"\n--- {source} ---\n"
                # Pull top 6 from each site to balance the massive new source list
                for article in articles[:6]: 
                    title = article.title.text if article.title else ""
                    desc = article.description.text if article.description else ""
                    cat_news_text += f"Headline: {title} | Details: {desc}\n"
        except Exception as e:
            print(f"Skipping {source}")

    print("Generating Long-Form Analysis...")
    prompt = f"""
    You are an elite, award-winning investigative journalist for {cat_name}. 
    Your reader is a highly intelligent professional who only checks the news once a day and wants deep, exhaustive explanations rather than quick summaries.
    Because your data comes from global sources, actively synthesize differing regional perspectives when explaining global events.
    
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
        response_text = client.models.generate_content(model=MODEL_NAME, contents=prompt).text
    except Exception as e:
        error_msg = str(e).lower()
        fallback_triggers = ["not found", "not supported", "resource_exhausted", "quota", "503", "unavailable", "high demand", "servererror", "internal"]
        
        if any(trigger in error_msg for trigger in fallback_triggers):
            print(f"  Model {MODEL_NAME} failed ({type(e).__name__}), trying alternatives...")
            response_text = None
            for fallback_model in possible_models:
                if fallback_model == MODEL_NAME:
                    continue
                try:
                    print(f"  Trying {fallback_model}...")
                    response_text = client.models.generate_content(model=fallback_model, contents=prompt).text
                    print(f"  Success with {fallback_model}!")
                    break
                except Exception as e2:
                    print(f"    {fallback_model} failed: {type(e2).__name__}")
                    continue
            if not response_text:
                raise Exception("All fallback models failed.") 
        else:
            raise

    try:
        parts = response_text.split("|||DIVIDER|||")
        daily_briefing_html = parts[0].replace("```html", "").replace("```", "").strip()
        weekly_recap_html = parts[1].replace("```html", "").replace("```", "").strip() if len(parts) > 1 else "<p>Recap generating...</p>"
        
        daily_briefing_html = markdown_to_html(daily_briefing_html)
        weekly_recap_html = markdown_to_html(weekly_recap_html)
        
        history[cat_name].append({"date": today_str, "briefing": daily_briefing_html, "recap": weekly_recap_html})
        if len(history[cat_name]) > 28:
            history[cat_name] = history[cat_name][-28:]
            
        safe_id = "".join(e for e in cat_name if e.isalnum())
        tab_buttons_html += f'<button onclick="openTab(event, \'{safe_id}\')">{cat_name}</button>\n'
        tab_content_html += f"""
        <div id="{safe_id}" class="tabcontent">
            <section class="content-section">
                <h2 class="section-heading daily">Daily Analysis</h2>
                <div class="ai-content">{daily_briefing_html}</div>
            </section>
            <hr class="section-divider">
            <section class="content-section">
                <h2 class="section-heading macro">Macro Trends</h2>
                <div class="ai-content">{weekly_recap_html}</div>
            </section>
        </div>
        """
        print(f"Success! Generated content for {cat_name}")

    except Exception as e:
        global_sync_success = False
        print(f"ERROR: Complete failure generating content for {cat_name}. Attempting to recover from history...")
        
        safe_id = "".join(e for e in cat_name if e.isalnum())
        tab_buttons_html += f'<button onclick="openTab(event, \'{safe_id}\')">{cat_name}</button>\n'
        
        if len(history[cat_name]) > 0:
            last_good = history[cat_name][-1]
            old_briefing = last_good.get("briefing", "<p>No prior daily briefing found.</p>")
            old_recap = last_good.get("recap", "<p>No prior macro trend found.</p>")
            old_date = last_good.get("date", "a previous session")
            
            tab_content_html += f"""
            <div id="{safe_id}" class="tabcontent">
                <div class="sync-warning">
                    ⚠️ <strong>API Overwhelmed:</strong> Unable to sync new {cat_name} data today. Displaying the most recent available data from {old_date}.
                </div>
                <section class="content-section">
                    <h2 class="section-heading daily">Daily Analysis</h2>
                    <div class="ai-content">{old_briefing}</div>
                </section>
                <hr class="section-divider">
                <section class="content-section">
                    <h2 class="section-heading macro">Macro Trends</h2>
                    <div class="ai-content">{old_recap}</div>
                </section>
            </div>
            """
        else:
            tab_content_html += f"""
            <div id="{safe_id}" class="tabcontent">
                 <div class="sync-warning" style="background-color: #f8d7da; color: #721c24; border-color: #f5c6cb;">
                    ❌ <strong>Sync Failed:</strong> The AI models are currently overwhelmed, and no previous history exists for this category. Please try again later.
                </div>
            </div>
            """
        
    time.sleep(3) 

# --- 4. SAVE HISTORY & COMPILE HTML ---
print("\nSaving history and compiling final website...")
with open(history_file, "w") as f:
    json.dump(history, f)

global_warning_html = ""
if not global_sync_success:
    global_warning_html = """
    <div class="global-warning">
        ⚠️ <strong>Notice:</strong> One or more categories could not be updated today due to high AI server demand. You are viewing cached data for those sections.
    </div>
    """

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Briefing</title>
    <style>
        @import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap)');

        :root {{
            --bg-color: #ffffff;
            --surface-color: #f8f9fa;
            --text-color: #1a1a1a;
            --text-muted: #4a4a4a;
            --text-light: #6b6b6b;
            --accent-primary: #2563eb;
            --accent-secondary: #059669;
            --accent-tertiary: #dc2626;
            --accent-warm: #ea580c;
            --border-color: #e5e5e5;
            --border-light: #f0f0f0;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.85;
            max-width: 1100px;
            margin: 0 auto;
            padding: 60px 48px;
            -webkit-font-smoothing: antialiased;
        }}

        header {{
            margin-bottom: 30px;
            padding-bottom: 32px;
            border-bottom: 1px solid var(--border-color);
        }}

        h1 {{ font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 8px; color: var(--text-color); }}
        .subtitle {{ font-size: 1.125rem; color: var(--text-muted); font-weight: 400; }}
        .date {{ font-size: 0.8rem; color: var(--text-light); margin-top: 20px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; }}

        .global-warning {{
            background-color: #fff3cd; color: #856404; padding: 16px; border-radius: 8px; 
            margin-bottom: 40px; border: 1px solid #ffeeba; font-weight: 500; text-align: center;
        }}
        .sync-warning {{
            background-color: #fff3cd; color: #856404; padding: 12px 20px; border-radius: 8px; 
            margin-bottom: 32px; border: 1px solid #ffeeba; font-weight: 500;
        }}

        nav {{ display: flex; gap: 12px; margin-bottom: 56px; flex-wrap: wrap; padding-bottom: 24px; border-bottom: 1px solid var(--border-color); }}
        nav button {{ background: var(--surface-color); border: 1px solid var(--border-color); color: var(--text-muted); padding: 14px 28px; cursor: pointer; font-size: 1rem; font-weight: 600; border-radius: 8px; transition: all 0.2s ease; }}
        nav button:hover {{ color: var(--text-color); border-color: var(--accent-primary); transform: translateY(-2px); }}
        nav button.active {{ color: var(--bg-color); background: var(--accent-primary); border-color: var(--accent-primary); }}

        .tabcontent {{ display: none; animation: fadeIn 0.4s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .section-heading {{ font-size: 0.875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 32px; padding-bottom: 16px; border-bottom: 3px solid; }}
        .section-heading.daily {{ color: var(--accent-primary); border-color: var(--accent-primary); }}
        .section-heading.macro {{ color: var(--accent-secondary); border-color: var(--accent-secondary); }}

        .content-section {{ margin-bottom: 64px; }}
        .ai-content {{ font-size: 1.125rem; line-height: 1.9; color: var(--text-color); }}
        .ai-content p {{ margin-bottom: 0; text-indent: 2em; }}
        .ai-content p:first-of-type {{ text-indent: 0; }}
        .ai-content p:first-of-type::first-letter {{ font-size: 3.5rem; font-weight: 700; float: left; line-height: 1; padding-right: 12px; padding-top: 8px; color: var(--accent-primary); }}

        .ai-content h3 {{ font-size: 1.5rem; font-weight: 700; color: var(--text-color); margin: 48px 0 24px 0; padding-left: 20px; border-left: 4px solid var(--accent-warm); line-height: 1.3; }}
        .ai-content h4 {{ font-size: 1.25rem; font-weight: 600; color: var(--accent-tertiary); margin: 36px 0 16px 0; }}
        
        .ai-content ul, .ai-content ol {{ margin: 24px 0; padding-left: 0; list-style: none; }}
        .ai-content li {{ position: relative; padding-left: 28px; margin-bottom: 16px; font-size: 1.0625rem; line-height: 1.8; }}
        .ai-content ul li::before {{ content: ''; position: absolute; left: 0; top: 12px; width: 8px; height: 8px; background: var(--accent-primary); border-radius: 50%; }}

        .ai-content strong {{ color: var(--text-color); font-weight: 600; }}
        .ai-content a {{ color: var(--accent-primary); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.2s; }}
        .ai-content a:hover {{ border-bottom-color: var(--accent-primary); }}

        .section-divider {{ height: 1px; background: linear-gradient(90deg, transparent, var(--border-color), transparent); margin: 64px 0; border: none; }}

        @media (max-width: 640px) {{
            body {{ padding: 48px 24px; }}
            h1 {{ font-size: 2rem; }}
            .subtitle {{ font-size: 1rem; }}
            nav button {{ padding: 12px 20px; font-size: 0.875rem; }}
            .ai-content {{ font-size: 1rem; }}
            .ai-content h3 {{ font-size: 1.25rem; }}
            .ai-content p:first-of-type::first-letter {{ font-size: 2.5rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Daily Briefing</h1>
        <p class="subtitle">Curated global news analysis</p>
        <p class="date">{today_str}</p>
    </header>

    {global_warning_html}

    <nav>{tab_buttons_html}</nav>
    <main>{tab_content_html}</main>

    <script>
        function openTab(evt, tabName) {{
            document.querySelectorAll('.tabcontent').forEach(el => el.style.display = 'none');
            document.querySelectorAll('nav button').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).style.display = 'block';
            evt.currentTarget.classList.add('active');
        }}
        document.addEventListener("DOMContentLoaded", function() {{
            const firstTab = document.querySelector('nav button');
            if(firstTab) {{
                firstTab.click();
            }}
        }});
    </script>
</body>
</html>
"""

print(f"\nFinal HTML generation:")
print(f"  - Categories processed: {len([k for k in categories.keys()])}")
print(f"  - Tab buttons generated: {len(tab_buttons_html) > 0}")
print(f"  - Tab content generated: {len(tab_content_html) > 0}")
print(f"  - History entries: {sum(len(v) for v in history.values())}")

if not tab_buttons_html or not tab_content_html:
    print("WARNING: No content was generated! Check API key and Gemini API availability.")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
    print(f"HTML written to index.html ({len(html_content)} bytes)")