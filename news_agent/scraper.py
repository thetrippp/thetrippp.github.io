import requests
from bs4 import BeautifulSoup
import ollama

# --- 1. THE DATA SOURCES (Top 20 Global Feeds) ---
rss_feeds = {
    # Europe & UK
    "BBC World (UK)": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "The Guardian (UK)": "https://www.theguardian.com/world/rss",
    "Sky News World (UK)": "https://feeds.skynews.com/feeds/rss/world.xml",
    "Deutsche Welle (Germany)": "https://rss.dw.com/rdf/rss-en-world",
    "France 24 (France)": "https://www.france24.com/en/rss",
    "Der Spiegel (Germany)": "https://www.spiegel.de/international/index.rss",
    
    # Middle East & Global
    "Al Jazeera (Qatar)": "https://www.aljazeera.com/xml/rss/all.xml",
    "United Nations News": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    
    # North America
    "New York Times (US)": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Washington Post (US)": "https://feeds.washingtonpost.com/rss/world",
    "CNN World (US)": "http://rss.cnn.com/rss/edition_world.rss",
    "Wall Street Journal (US)": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "NPR World (US)": "https://feeds.npr.org/1004/rss.xml",
    "CBS News World (US)": "https://www.cbsnews.com/latest/rss/world",
    "ABC News International (US)": "https://abcnews.go.com/abcnews/internationalheadlines",
    "Politico (Politics)": "https://rss.politico.com/politics-news.xml",
    "CNBC (World Economy)": "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000&id=100727362",
    
    # Asia 
    "South China Morning Post (Hong Kong)": "https://www.scmp.com/rss/91/feed",
    "The Hindu International (India)": "https://www.thehindu.com/news/international/feeder/default.rss",
    "CNA Asia (Singapore)": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511"
}

print("Initiating global data sweep...\n")

all_news_text = ""

# --- 2. MULTI-SOURCE SCRAPING ---
# Loop through each news source in our dictionary
for source_name, url in rss_feeds.items():
    print(f"📡 Fetching intelligence from: {source_name}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, features="xml")
            articles = soup.find_all("item")
            
            # Grab the top 5 from EACH source (15 total articles)
            all_news_text += f"\n--- Source: {source_name} ---\n"
            for article in articles[:5]:
                title = article.title.text if article.title else "No Title"
                description = article.description.text if article.description else "No Description"
                all_news_text += f"Headline: {title}\nSummary: {description}\n\n"
        else:
            print(f"⚠️ Failed to reach {source_name}")
    except Exception as e:
        print(f"⚠️ Error scraping {source_name}: {e}")

print("\nData gathered successfully. Compiling Intelligence Briefing...\n")

# --- 3. THE UPGRADED AI ANALYST ---
# We use Prompt Engineering to force a deeper, structured analysis
prompt = f"""
You are a Senior Geopolitical Analyst creating a daily intelligence briefing for a policymaker. 
I am providing you with today's top news from multiple global sources.

Your goal is to synthesize this raw data into a deep, insightful analysis of current affairs. Do not just repeat the headlines. Look for the underlying narrative.

Please structure your briefing exactly like this using Markdown formatting:

## 🌍 Executive Global Overview
(Provide a cohesive paragraph summarizing the global temperature today based on the provided news.)

## 🔍 Key Strategic Themes
(Group the events by major themes or regions. E.g., 'Middle East Tensions', 'European Politics', 'Economic Shifts'. Use bullet points to explain what is happening within these themes.)

## 🧠 Analyst's Implications (The "So What?")
(Explain why these events matter. What are the potential ripple effects or future consequences of these combined events?)

## 📊 Data-Driven Insights
(If there are any clear trends or patterns across the news, highlight them here. For example, "Increased diplomatic activity in the Middle East" or "Rising economic tensions between major powers".)

## 🔮 Forecasting & Recommendations
(Based on the current intelligence, provide a forecast for the next 1-3 months. What should policymakers be watching for? What actions might be advisable?)

## Detailed account of the news

Here is the raw intelligence data:
{all_news_text}
"""

# Send to Llama 3
response = ollama.chat(model='llama3', messages=[
  {
    'role': 'user',
    'content': prompt
  }
])

# Print the rich briefing
print("\n" + "="*50)
print(" 🕵️‍♂️ DAILY GEOPOLITICAL INTELLIGENCE BRIEFING")
print("="*50 + "\n")
print(response['message']['content'])