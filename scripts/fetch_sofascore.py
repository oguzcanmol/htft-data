import urllib.request, json, os, time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

LEAGUE_IDS = {
    "TR1": 52, "EN1": 17, "ES1": 8, "DE1": 35,
    "IT1": 23, "FR1": 34, "PT1": 238, "NL1": 37,
}

def fetch(url):
    time.sleep(1.2)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("  ERR {}: {}".format(url[-60:], str(e)[:60]))
        return None

def get_current_season(league_id):
    data = fetch("https://www.sofascore.com/api/v1/unique-tournament/{}/seasons".format(league_id))
    if not data or "seasons" not in data:
        return None
    seasons = sorted(data["seasons"], key=lambda x: x.get("year",""), reverse=True)
    if seasons:
        print("    Season: {} - {}".format(seasons[0].get("id"), seasons[0].get("name")))
        return seasons[0]["id"]
    return None

def get_league_next_events(league_id, season_id):
    data = fetch("https://www.sofascore.com/api/v1/unique-tournament/{}/season/{}/events/next/0".format(
        league_id, season_id))
    if data and "events" in data:
        return data["events"]
    return []

def infer_style_from_data(stats, last5_events, formation, avg_possession):
    if not stats:
        return "balanced"
    possession        = avg_possession or stats.get("possession", 50)
    accurate_pass_pct = stats.get("accuratePassPct", 75)
    tackles_pg        = stats.get("tacklesPerGame", 15)
    inte
