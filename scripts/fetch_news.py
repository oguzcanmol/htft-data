import urllib.request, json, os, re
from datetime import datetime
from xml.etree import ElementTree as ET

TEAM_KEYWORDS = {
    "Galatasaray": ["galatasaray", "cimbom"],
    "Fenerbahce": ["fenerbahce", "fener"],
    "Besiktas": ["besiktas", "kartal"],
    "Trabzonspor": ["trabzonspor", "trabzon"],
    "Arsenal": ["arsenal"],
    "Chelsea": ["chelsea"],
    "Liverpool": ["liverpool"],
    "Man City": ["manchester city", "man city"],
    "Real Madrid": ["real madrid"],
    "Barcelona": ["barcelona", "barca"],
    "Bayern Munich": ["bayern munich", "bayern"],
}

INJURY_KEYWORDS = ["sakat", "injury", "injured", "out", "doubt", "sakatlık", "ameliyat"]
CRISIS_KEYWORDS = ["kriz", "crisis", "kavga", "fight", "gerilim", "tension", "ihraç", "fired"]
POSITIVE_KEYWORDS = ["geri döndü", "returned", "fit", "hazır", "ready", "form"]

def fetch_news(team_name, keywords):
    query = "+".join(keywords[:2])
    url = "https://news.google.com/rss/search?q={}&hl=tr&gl=TR&ceid=TR:tr".format(
        urllib.request.quote(query)
    )
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read().decode("utf-8")
        
        root = ET.fromstring(content)
        items = root.findall(".//item")
        
        news = []
        morale_score = 0
        
        for item in items[:5]:
            title = item.findtext("title", "")
            title_lower = title.lower()
            
            sentiment = "neutral"
            if any(k in title_lower for k in INJURY_KEYWORDS):
                sentiment = "negative"
                morale_score -= 1
            elif any(k in title_lower for k in CRISIS_KEYWORDS):
                sentiment = "negative"
                morale_score -= 2
            elif any(k in title_lower for k in POSITIVE_KEYWORDS):
                sentiment = "positive"
                morale_score += 1
            
            news.append({
                "title": title[:100],
                "sentiment": sentiment,
                "date": item.findtext("pubDate", "")[:16],
            })
        
        return {
            "news": news,
            "moraleScore": max(-5, min(5, morale_score)),
        }
    except Exception as e:
        return {"news": [], "moraleScore": 0}

def main():
    try:
        with open("data/odds.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = {}

    news_data = {}
    upcoming = existing.get("upcoming", [])
    processed = set()

    for match in upcoming[:20]:
        for team in [match.get("home",""), match.get("away","")]:
            if team in processed or team not in TEAM_KEYWORDS:
                continue
            processed.add(team)
            print("  Haberler: {}...".format(team))
            news_data[team] = fetch_news(team, TEAM_KEYWORDS[team])

    existing["news"] = news_data
    existing["news_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open("data/odds.json", "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print("Haberler kaydedildi: {} takim".format(len(news_data)))

if __name__ == "__main__":
    main()
