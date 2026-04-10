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
    "Global Geopolitics": {
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
    "Tech & AI": {
        "TechCrunch (US)": "https://techcrunch.com/feed/",
        "Ars Technica (US)": "http://feeds.arstechnica.com/arstechnica/index",
        "Wired (Global)": "https://www.wired.com/feed/rss",
        "Rest of World (Global Tech)": "https://restofworld.org/feed/"
    },
    "Gaming": {
        "Game Developer (Industry)": "https://www.gamedeveloper.com/rss.xml",
        "Polygon (Culture/News)": "https://www.polygon.com/rss/index.xml",
        "Eurogamer (Europe)": "https://www.eurogamer.net/feed/news",
        "IGN (Mainstream)": "https://feeds.feedburner.com/ign/games-all"
    },
    "Space": {
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
                    if key in saved_history:
                        history[key] = saved_history[key]
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
    <div class="global-warning" style="background-color: #fff3cd; color: #856404; padding: 15px; text-align: center; font-size: 0.9rem; margin-bottom: 20px;">
        ⚠️ <strong>Notice:</strong> One or more categories could not be updated today due to high AI server demand. You are viewing cached data for those sections.
    </div>
    """

# Repurpose the old buttons into the new div format required by the mockup styles/JS
processed_tabs = tab_buttons_html.replace('<button onclick="openTab(event, \'', '<div class="cat-item" data-target="').replace('\')">', '">').replace('</button>', '</div>')

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Briefing | Premium Intelligence</title>

    <link rel="preconnect" href="[https://fonts.googleapis.com](https://fonts.googleapis.com)">
    <link href="[https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap](https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap)" rel="stylesheet">
    <link href="[https://fonts.googleapis.com/css2?family=Poppins&display=swap](https://fonts.googleapis.com/css2?family=Poppins&display=swap)" rel="stylesheet">

    <style>
        :root {{
            --ink: #0a0a0a;
            --paper: #f5f0e8;
            --accent: #c8102e;
            --muted: #6b6459;
            --rule: #c9bfaf;
            --max-width: 800px;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
            background: var(--paper);
            color: var(--ink);
            font-family: 'Poppins', sans-serif;
            line-height: 1.6;
        }}

        /* Progress Bar */
        .progress-container {{
            position: fixed;
            top: 0;
            z-index: 100;
            width: 100%;
            height: 3px;
            background: transparent;
        }}

        .progress-bar {{
            height: 3px;
            background: var(--accent);
            width: 0%;
        }}

        /* Masthead */
        header {{
            border-bottom: 3px double var(--ink);
            padding: 18px 40px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
        }}

        h1 {{
            font-family: 'Poppins', sans-serif;
            font-size: clamp(5rem, 7vw, 7rem);
            letter-spacing: 0.04em;
            text-align: center;
            flex: 1;
        }}

        .subtitle {{
            font-size: 1rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
            text-align: right;
        }}

        .date {{
            font-size: 0.9rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
        }}

        /* Category carousel */
        .category-stage {{
            position: relative;
            overflow: hidden;
            padding: 32px 0 18px;
            border-bottom: 2px solid var(--ink);
            -webkit-mask-image: linear-gradient(to right, transparent 0%, black 16%, black 84%, transparent 100%);
            mask-image: linear-gradient(to right, transparent 0%, black 16%, black 84%, transparent 100%);
            cursor: grab;
        }}

        .category-stage:active {{
            cursor: grabbing;
        }}

        .category-track {{
            display: flex;
            align-items: center;
            will-change: transform;
            transition: transform 0.45s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}

        .category-track.no-transition {{
            transition: none;
        }}

        .cat-item {{
            font-family: 'Poppins', sans-serif;
            font-size: clamp(3rem, 8vw, 6rem);
            letter-spacing: -0.1em;
            line-height: 1;
            white-space: nowrap;
            padding: 0 36px;
            color: var(--muted);
            opacity: 0.15;
            transform: scale(0.6);
            filter: blur(1px);
            transition: opacity 0.4s, transform 0.4s, color 0.4s, filter 0.4s;
            cursor: pointer;
            flex-shrink: 0;
        }}

        .cat-item.active {{
            color: var(--ink);
            opacity: 1;
            transform: scale(1.05);
            filter: blur(0);
        }}

        .cat-item.adjacent {{
            opacity: 0.35;
            transform: scale(0.75);
            filter: blur(0.5px);
        }}

        .category-indicator {{
            display: flex;
            justify-content: center;
            padding: 10px 0 0;
        }}

        .category-indicator span {{
            width: 32px;
            height: 3px;
            background: var(--accent);
            border-radius: 2px;
        }}

        /* Main */
        main {{
            max-width: var(--max-width);
            margin: 0 auto;
            padding: 0 40px 80px;
        }}

        .tabcontent {{
            display: none;
        }}

        /* Section label */
        .section-heading {{
            font-family: 'Poppins', sans-serif;
            font-size: 0.85rem;
            letter-spacing: 0.18em;
            color: var(--muted);
            padding: 32px 0 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .section-heading::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: var(--rule);
        }}

        .section-divider {{
            margin: 32px 0;
            border: none;
            border-top: 1px solid var(--rule);
        }}

        /* Article style */
        .ai-content {{
            -webkit-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
            user-select: text;
            margin-top: 24px;
        }}

        .ai-content p {{
            font-size: 0.98rem;
            line-height: 1.8;
            color: #2a2520;
            margin-bottom: 16px;
            max-width: 620px;
        }}

        .ai-content h3 {{
            font-family: 'Poppins', sans-serif;
            font-size: 1.8rem;
            margin: 28px 0 12px;
        }}
        
        .ai-content h4 {{
            font-family: 'Poppins', sans-serif;
            font-size: 1.2rem;
            margin: 20px 0 8px;
        }}

        .ai-content ul {{
            margin: 20px 0;
            padding-left: 20px;
        }}

        .ai-content li {{
            margin-bottom: 8px;
        }}

        /* Responsive */
        @media (max-width: 600px) {{
            header {{
                padding: 14px 20px;
                flex-direction: column;
                align-items: center;
            }}

            main {{
                padding: 0 20px 60px;
            }}
        }}
    </style>
</head>

<body>
    <div class="progress-container">
        <div class="progress-bar" id="myBar"></div>
    </div>

    <header>
        <div class="date" id="last-sync-date">{today_str}</div>
        <h1>Daily Briefing</h1><br>
        <p class="subtitle">What's going on today?</p>
    </header>
    
    <div class="category-stage" id="category-stage">
        <div class="category-track" id="category-track">
            {processed_tabs}
        </div>
    </div>
    <div class="category-indicator"><span></span></div>

    {global_warning_html}

    <main id="tab-contents">
        {tab_content_html}
    </main>

    <script>
        // Scroll Progress
        window.onscroll = function () {{
            let winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            let height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            let scrolled = (winScroll / height) * 100;
            document.getElementById("myBar").style.width = scrolled + "%";
        }};

        // Logic Initialization
        document.addEventListener("DOMContentLoaded", () => {{
            const categoryTrack = document.getElementById('category-track');
            const stage = document.getElementById('category-stage');
            const items = categoryTrack.querySelectorAll('.cat-item');
            let currentIndex = 0;

            function getOffset(idx) {{
                const stageW = stage.offsetWidth;
                const item = items[idx];
                if (!item) return 0;
                return stageW / 2 - (item.offsetLeft + item.offsetWidth / 2);
            }}

            function updateCats(idx) {{
                items.forEach((el, i) => {{
                    el.classList.remove('active', 'adjacent');
                    const d = Math.abs(i - idx);
                    if (d === 0) el.classList.add('active');
                    else if (d === 1) el.classList.add('adjacent');
                }});
            }}

            function goTo(idx, instant = false) {{
                if (items.length === 0) return;
                
                currentIndex = Math.max(0, Math.min(idx, items.length - 1));
                updateCats(currentIndex);

                if (instant) categoryTrack.classList.add('no-transition');
                categoryTrack.style.transform = `translateX(${{getOffset(currentIndex)}}px)`;
                if (instant) requestAnimationFrame(() => categoryTrack.classList.remove('no-transition'));

                document.querySelectorAll('.tabcontent').forEach(el => el.style.display = 'none');
                const activeId = items[currentIndex].dataset.target;
                const activeContent = document.getElementById(activeId);
                if (activeContent) activeContent.style.display = 'block';
            }}

            // Setup click listeners on category items
            items.forEach((item, i) => {{
                item.addEventListener('click', () => goTo(i));
            }});

            // Initialize position and content
            if (items.length > 0) {{
                goTo(0, true);
            }}

            // Resize handling
            window.addEventListener('resize', () => goTo(currentIndex, true));

            // Drag / swipe interactions
            let startX = 0, delta = 0, down = false;

            stage.addEventListener('pointerdown', e => {{
                down = true;
                startX = e.clientX;
                delta = 0;
                categoryTrack.classList.add('no-transition');
                stage.setPointerCapture(e.pointerId);
            }});

            stage.addEventListener('pointermove', e => {{
                if (!down) return;
                delta = e.clientX - startX;
                categoryTrack.style.transform = `translateX(${{getOffset(currentIndex) + delta}}px)`;
            }});

            stage.addEventListener('pointerup', () => {{
                if (!down) return;
                down = false;
                categoryTrack.classList.remove('no-transition');
                if (delta < -60 && currentIndex < items.length - 1) goTo(currentIndex + 1);
                else if (delta > 60 && currentIndex > 0) goTo(currentIndex - 1);
                else goTo(currentIndex);
                delta = 0;
            }});
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