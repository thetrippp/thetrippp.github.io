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
    <title>Daily Intelligence Briefing</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;700&family=Inter:wght@400;600&display=swap');

        :root {{
            --bg-color: hsl(210, 36%, 96%);
            /* Very light blue-grey */
            --text-color: hsl(210, 10%, 20%);
            /* Dark grey */
            --muted-text-color: hsl(210, 5%, 45%);
            /* Medium grey */
            --accent-color: hsl(200, 70%, 40%);
            /* Professional blue */
            --card-bg: hsl(0, 0%, 100%);
            /* White */
            --border-color: hsl(210, 15%, 88%);
            /* Light grey border */
            --shadow-light: 0 2px 8px rgba(0, 0, 0, 0.05);
            --shadow-medium: 0 5px 15px rgba(0, 0, 0, 0.08);
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            /* Slightly tighter line height for readability */
            max-width: 960px;
            /* Slightly wider content area */
            margin: 0 auto;
            padding: 50px 25px;
            /* More padding */
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        h1,
        h2,
        .story-title {{
            font-family: 'Lora', serif;
            font-weight: 700;
            color: var(--text-color);
        }}

        h1 {{
            font-size: 3.2rem;
            /* Larger main title */
            text-align: center;
            margin-bottom: 0.2em;
            color: var(--text-color);
            line-height: 1.1;
        }}

        h2 {{
            font-size: 1.8rem;
            /* Larger section titles */
            color: var(--text-color);
            border-bottom: 2px solid var(--border-color);
            /* Thicker border */
            padding-bottom: 12px;
            margin-top: 40px;
            /* More space above h2 */
            margin-bottom: 25px;
            margin-top: 0;
        }}

        .header-container {{
            text-align: center;
            margin-bottom: 50px;
            /* More space below header */
            padding-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
        }}

        .header-container p {{
            color: var(--muted-text-color);
            font-size: 1.2rem;
            /* Slightly larger tagline */
            margin: 0.5em 0 0;
        }}

        .date-badge {{
            display: inline-block;
            background-color: var(--border-color);
            color: var(--muted-text-color);
            padding: 8px 16px;
            border-radius: 20px;
            /* More rounded badge */
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 15px;
            letter-spacing: 0.5px;
        }}

        .tab {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            /* More space between tabs */
            margin-bottom: 40px;
            /* More space below tabs */
            border-bottom: 1px solid var(--border-color);
            /* Subtle line below tabs */
            padding-bottom: 10px;
        }}

        .tab button {{
            background: none;
            border: none;
            border-bottom: 3px solid transparent;
            /* Thicker active border */
            color: var(--muted-text-color);
            padding: 12px 10px;
            /* Adjusted padding */
            cursor: pointer;
            font-size: 1.05rem;
            /* Slightly larger font */
            font-weight: 600;
            transition: all 0.2s ease;
            margin-bottom: -1px;
            text-transform: uppercase;
            /* Uppercase tabs */
            letter-spacing: 0.8px;
        }}

        .tab button:hover {{
            color: var(--accent-color);
            border-bottom-color: var(--accent-color);
            /* Highlight on hover */
        }}

        .tab button.active {{
            color: var(--text-color);
            border-bottom-color: var(--accent-color);
        }}

        .tabcontent {{
            display: none;
            animation: fadeEffect 0.5s;
        }}

        @keyframes fadeEffect {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}

            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .card {{
            background: var(--card-bg);
            padding: 35px 45px;
            /* More internal padding */
            margin-bottom: 40px;
            /* More space between cards */
            border-radius: 10px;
            /* Slightly more rounded corners */
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-medium);
            /* More pronounced shadow */
        }}

        .story-box {{
            padding: 30px 0;
            /* More vertical padding */
            margin-bottom: 30px;
            border-bottom: 1px dashed var(--border-color);
            /* Dashed separator */
        }}

        .story-box:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}

        .story-title {{
            color: var(--accent-color);
            /* Story title in accent color */
            font-size: 2.2rem;
            /* Larger story title */
            margin-top: 0;
            margin-bottom: 10px;
            line-height: 1.2;
        }}

        .section-head {{
            font-family: 'Inter', sans-serif;
            color: var(--muted-text-color);
            font-size: 0.9rem;
            /* Slightly larger section head */
            font-weight: 700;
            /* Bolder */
            text-transform: uppercase;
            letter-spacing: 1px;
            /* More letter spacing */
            margin-top: 20px;
            margin-bottom: 8px;
        }}

        .ai-content p {{
            margin-bottom: 1.2em;
            /* More space between paragraphs */
            font-size: 1.05rem;
            /* Slightly larger body text */
            color: hsl(210, 8%, 30%);
            /* Slightly darker body text for contrast */
        }}

        .ai-content strong {{
            color: var(--text-color);
            font-weight: 700;
            /* Bolder strong text */
        }}

        /* Responsive adjustments */
        @media (max-width: 768px) {{
            body {{
                padding: 30px 15px;
            }}

            h1 {{
                font-size: 2.5rem;
            }}

            h2 {{
                font-size: 1.4rem;
                margin-top: 30px;
                margin-bottom: 20px;
            }}

            .header-container {{
                margin-bottom: 30px;
            }}

            .card {{
                padding: 25px 20px;
                margin-bottom: 30px;
            }}

            .story-title {{
                font-size: 1.7rem;
            }}

            .tab button {{
                font-size: 0.95rem;
                padding: 10px 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Daily Intelligence Briefing</h1>
        <p>An AI-Powered Global News Analysis</p>
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
        document.addEventListener("DOMContentLoaded", function() {{
            const firstTab = document.getElementsByClassName("tablinks")[0];
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