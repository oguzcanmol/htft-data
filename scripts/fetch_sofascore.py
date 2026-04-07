import urllib.request, json, os, time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "x-requested-with": "XMLHttpRequest",
}

# Super Lig ID: 52, season: 63814
# Premier League ID: 17, season: 61627
# La Liga: 8, season: 61643
# Bundesliga: 35, season: 63635
# Serie A: 23, season: 63515
# Ligue 1: 34, season: 63513

LEAGUES = {
    "TR1": (52, 63814),
    "EN1": (17, 61627),
    "ES1": (8, 61643),
    "DE1": (35, 63635),
    "IT1": (23, 63515),
    "FR1": (34, 63513),
}

def fetch(url):
    time.sleep(1.5)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("  HATA: {} -> {}".format(url.split("/api")[1][:50], e))
        return None

def get_next_event_id(league_id, season_id):
    """Bir sonraki maçın event ID'sini bul"""
    data = fetch("https://www.sofascore.com/api/v1/unique-tournament/{}/season/{}/events/next/0".format(league_id, season_id))
    if data and "events" in data and data["events"]:
        return data["events"][0]["id"], data["events"][0]
    return None, None

def get_team_last5(team_id):
    """Son 5 maç formu"""
    data = fetch("https://www.sofascore.com/api/v1/team/{}/events/last/0".format(team_id))
    if not data or "events" not in data:
        return ["?","?","?","?","?"]
    form = []
    for ev in sorted(data["events"], key=lambda x: x.get("startTimestamp",0), reverse=True)[:5]:
        ht = ev.get("homeTeam",{}).get("id")
        hw = ev.get("homeScore",{}).get("current",0) or 0
        aw = ev.get("awayScore",{}).get("current",0) or 0
        if ht == team_id:
            form.append("W" if hw>aw else "D" if hw==aw else "L")
        else:
            form.append("W" if aw>hw else "D" if hw==aw else "L")
    while len(form) < 5:
        form.append("?")
    return form

def get_team_info(team_id):
    """Takım bilgisi - hoca, rating"""
    data = fetch("https://www.sofascore.com/api/v1/team/{}".format(team_id))
    if not data or "team" not in data:
        return {}
    t = data["team"]
    mgr = t.get("manager", {})
    return {
        "manager": mgr.get("name", ""),
        "ranking": t.get("ranking", 0),
    }

def get_lineup(event_id):
    """Maç kadrosu ve diziliş"""
    data = fetch("https://www.sofascore.com/api/v1/event/{}/lineups".format(event_id))
    if not data:
        return None
    result = {}
    for side in ["home", "away"]:
        if side not in data:
            continue
        side_data = data[side]
        formation = side_data.get("formation", "")
        players = []
        for p in side_data.get("players", []):
            player = p.get("player", {})
            stats = p.get("statistics", {})
            players.append({
                "name": player.get("name", ""),
                "position": p.get("position", ""),
                "rating": stats.get("rating", 0),
                "jerseyNumber": p.get("jerseyNumber", ""),
            })
        result[side] = {
            "formation": formation,
            "players": players,
        }
    return result

def get_pregame_form(event_id):
    """Maç öncesi form istatistikleri"""
    data = fetch("https://www.sofascore.com/api/v1/event/{}/pregame-form".format(event_id))
    if not data:
        return {}
    result = {}
    for side in ["homeTeam", "awayTeam"]:
        if side not in data:
            continue
        d = data[side]
        result[side] = {
            "avgRating": d.get("avgRating", 0),
            "position": d.get("position", 0),
            "value": d.get("value", ""),
            "form": d.get("form", []),
        }
    return result

def main():
    os.makedirs("data", exist_ok=True)
    
    try:
        with open("data/odds.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = {}

    upcoming = existing.get("upcoming", [])
    sofascore_data = {}

    print("SofaScore maç verileri cekiliyor...")
    print("Toplam upcoming mac: {}".format(len(upcoming)))

    # Her upcoming maç için SofaScore'da eşleştir
    matched = 0
    for match in upcoming[:30]:  # İlk 30 maç
        home = match.get("home", "")
        away = match.get("away", "")
        league = match.get("league", "")
        
        if league not in LEAGUES:
            continue
            
        league_id, season_id = LEAGUES[league]
        
        # Bir sonraki maçları çek ve eşleştir
        data = fetch("https://www.sofascore.com/api/v1/unique-tournament/{}/season/{}/events/next/0".format(league_id, season_id))
        if not data or "events" not in data:
            continue
            
        for ev in data["events"]:
            ev_home = ev.get("homeTeam", {}).get("name", "")
            ev_away = ev.get("awayTeam", {}).get("name", "")
            
            # İsim benzerliği kontrolü
            home_match = home[:5].lower() in ev_home.lower() or ev_home[:5].lower() in home.lower()
            away_match = away[:5].lower() in ev_away.lower() or ev_away[:5].lower() in away.lower()
            
            if home_match and away_match:
                event_id = ev["id"]
                home_id = ev.get("homeTeam", {}).get("id")
                away_id = ev.get("awayTeam", {}).get("id")
                
                print("  ESLESTI: {} vs {} (ID: {})".format(ev_home, ev_away, event_id))
                
                # Form
                h_form = get_team_last5(home_id) if home_id else ["?","?","?","?","?"]
                a_form = get_team_last5(away_id) if away_id else ["?","?","?","?","?"]
                
                # Takım bilgisi
                h_info = get_team_info(home_id) if home_id else {}
                a_info = get_team_info(away_id) if away_id else {}
                
                # Pregame form
                pgf = get_pregame_form(event_id)
                
                key = "{}_vs_{}".format(home, away)
                sofascore_data[key] = {
                    "eventId": event_id,
                    "home": {
                        "id": home_id,
                        "name": ev_home,
                        "form": h_form,
                        "manager": h_info.get("manager", ""),
                        "ranking": h_info.get("ranking", 0),
                        "pregameForm": pgf.get("homeTeam", {}),
                    },
                    "away": {
                        "id": away_id,
                        "name": ev_away,
                        "form": a_form,
                        "manager": a_info.get("manager", ""),
                        "ranking": a_info.get("ranking", 0),
                        "pregameForm": pgf.get("awayTeam", {}),
                    }
                }
                matched += 1
                break

    print("Eslesen mac sayisi: {}".format(matched))
    
    existing["sofascore"] = sofascore_data
    existing["sofascore_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    with open("data/odds.json", "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print("Kaydedildi!")

if __name__ == "__main__":
    main()
