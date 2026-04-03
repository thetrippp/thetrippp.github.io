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

# Helper function to convert markdown bold/italics to HTML
def markdown_to_html(text):
    # Replace bold first: **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Replace italics next: *text* -> <em>text</em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    return text

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
        
        # Apply markdown to HTML conversion
        daily_briefing_html = markdown_to_html(daily_briefing_html)
        weekly_recap_html = markdown_to_html(weekly_recap_html)
        history[cat_name].append({"date": today_str, "briefing": daily_briefing_html})
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
    <title>Daily Briefing</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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

        /* Header */
        header {{
            margin-bottom: 48px;
            padding-bottom: 32px;
            border-bottom: 1px solid var(--border-color);
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
            color: var(--text-color);
        }}

        .subtitle {{
            font-size: 1.125rem;
            color: var(--text-muted);
            font-weight: 400;
        }}

        .date {{
            font-size: 0.8rem;
            color: var(--text-light);
            margin-top: 20px;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        /* Navigation Tabs */
        nav {{
            display: flex;
            gap: 12px;
            margin-bottom: 56px;
            flex-wrap: wrap;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
        }}

        nav button {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 14px 28px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 8px;
            transition: all 0.2s ease;
        }}

        nav button:hover {{
            color: var(--text-color);
            border-color: var(--accent-primary);
            transform: translateY(-2px);
        }}

        nav button.active {{
            color: var(--bg-color);
            background: var(--accent-primary);
            border-color: var(--accent-primary);
        }}

        /* Tab Content */
        .tabcontent {{
            display: none;
            animation: fadeIn 0.4s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Section Headings */
        .section-heading {{
            font-size: 0.875rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 3px solid;
        }}

        .section-heading.daily {{
            color: var(--accent-primary);
            border-color: var(--accent-primary);
        }}

        .section-heading.macro {{
            color: var(--accent-secondary);
            border-color: var(--accent-secondary);
        }}

        /* Content Container */
        .content-section {{
            margin-bottom: 64px;
        }}

        /* Seamless Content */
        .ai-content {{
            font-size: 1.125rem;
            line-height: 1.9;
            color: var(--text-color);
        }}

        .ai-content p {{
            margin-bottom: 0;
            text-indent: 2em;
        }}

        .ai-content p:first-of-type {{
            text-indent: 0;
        }}

        .ai-content p:first-of-type::first-letter {{
            font-size: 3.5rem;
            font-weight: 700;
            float: left;
            line-height: 1;
            padding-right: 12px;
            padding-top: 8px;
            color: var(--accent-primary);
        }}

        /* Headings within content */
        .ai-content h3 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-color);
            margin: 48px 0 24px 0;
            padding-left: 20px;
            border-left: 4px solid var(--accent-warm);
            line-height: 1.3;
        }}

        .ai-content h4 {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--accent-tertiary);
            margin: 36px 0 16px 0;
        }}

        /* Lists */
        .ai-content ul,
        .ai-content ol {{
            margin: 24px 0;
            padding-left: 0;
            list-style: none;
        }}

        .ai-content li {{
            position: relative;
            padding-left: 28px;
            margin-bottom: 16px;
            font-size: 1.0625rem;
            line-height: 1.8;
        }}

        .ai-content ul li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 12px;
            width: 8px;
            height: 8px;
            background: var(--accent-primary);
            border-radius: 50%;
        }}

        .ai-content ol {{
            counter-reset: item;
        }}

        .ai-content ol li {{
            counter-increment: item;
        }}

        .ai-content ol li::before {{
            content: counter(item);
            position: absolute;
            left: 0;
            top: 2px;
            width: 24px;
            height: 24px;
            background: var(--accent-secondary);
            color: var(--bg-color);
            border-radius: 50%;
            font-size: 0.75rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        /* Strong text */
        .ai-content strong {{
            color: var(--text-color);
            font-weight: 600;
        }}

        /* Links */
        .ai-content a {{
            color: var(--accent-primary);
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }}

        .ai-content a:hover {{
            border-bottom-color: var(--accent-primary);
        }}

        /* Horizontal rule between major sections */
        .section-divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border-color), transparent);
            margin: 64px 0;
            border: none;
        }}

        /* Responsive */
        @media (max-width: 640px) {{
            body {{
                padding: 48px 24px;
            }}

            h1 {{
                font-size: 2rem;
            }}

            .subtitle {{
                font-size: 1rem;
            }}

            nav button {{
                padding: 12px 20px;
                font-size: 0.875rem;
            }}

            .ai-content {{
                font-size: 1rem;
            }}

            .ai-content h3 {{
                font-size: 1.25rem;
            }}

            .ai-content p:first-of-type::first-letter {{
                font-size: 2.5rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Daily Briefing</h1>
        <p class="subtitle">Curated news analysis</p>
        <p class="date">{today_str}</p>
    </header>

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

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)