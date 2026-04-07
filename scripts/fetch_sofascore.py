import urllib.request, json, os, time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

# Lig ID'leri - season ID'leri dinamik cekilecek
LEAGUE_IDS = {
    "TR1": 52,
    "EN1": 17,
    "ES1": 8,
    "DE1": 35,
    "IT1": 23,
    "FR1": 34,
    "PT1": 238,
    "NL1": 37,
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
    """Ligin guncel season ID'sini dinamik olarak cek"""
    data = fetch("https://www.sofascore.com/api/v1/unique-tournament/{}/seasons".format(league_id))
    if not data or "seasons" not in data:
        return None
    # En yeni season'i al
    seasons = sorted(data["seasons"], key=lambda x: x.get("year", ""), reverse=True)
    if seasons:
        print("    Season bulundu: {} - {}".format(seasons[0].get("id"), seasons[0].get("name")))
        return seasons[0]["id"]
    return None

def get_league_next_events(league_id, season_id):
    """Ligin bir sonraki maclarini cek"""
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
    interceptions_pg  = stats.get("interceptionsPerGame", 5)
    dribbles_pg       = stats.get("dribblesPerGame", 3)
    shots_pg          = stats.get("shotsPerGame", 10)
    goals_pg          = stats.get("goalsPerGame", 1.2)
    conceded_pg       = stats.get("concededPerGame", 1.2)
    big_chances_pg    = stats.get("bigChancesCreatedPerGame", 1.0)

    FORMATION_WEIGHTS = {
        "4-3-3":    {"pressing":4,"gegenpressing":3,"high-line":2,"tiki-taka":1},
        "4-2-3-1":  {"pressing":3,"gegenpressing":2,"technical":2,"balanced":1},
        "4-1-4-1":  {"pressing":3,"gegenpressing":3,"high-line":1},
        "3-4-3":    {"pressing":4,"high-line":3,"wing-play":2,"gegenpressing":2},
        "3-4-2-1":  {"pressing":3,"high-line":2,"wing-play":2},
        "4-3-2-1":  {"pressing":2,"technical":2,"tiki-taka":2},
        "4-6-0":    {"tiki-taka":5,"possession":4,"high-line":2},
        "3-3-3-1":  {"tiki-taka":3,"possession":3,"pressing":2},
        "4-1-3-2":  {"technical":3,"possession":2,"pressing":2},
        "4-3-1-2":  {"technical":3,"tiki-taka":2,"possession":2},
        "3-5-2":    {"possession":2,"technical":2,"counter":1,"wing-play":2},
        "4-5-1":    {"possession":2,"balanced":2,"low-block":2,"counter":2},
        "4-4-2":    {"balanced":3,"counter":2,"direct":2,"low-block":1},
        "4-4-1-1":  {"counter":3,"balanced":2,"low-block":2},
        "5-3-2":    {"low-block":4,"counter":4,"direct":2},
        "5-4-1":    {"low-block":5,"park-the-bus":3,"counter":3},
        "5-2-3":    {"low-block":3,"counter":3,"wing-play":2},
        "5-2-2-1":  {"low-block":4,"park-the-bus":2,"counter":3},
        "4-2-2-2":  {"counter":3,"direct":2,"balanced":2},
        "3-6-1":    {"low-block":3,"counter":2,"possession":1},
        "4-2-4":    {"wing-play":4,"pressing":3,"high-line":2},
        "3-4-1-2":  {"wing-play":3,"technical":2,"pressing":2},
        "4-1-2-1-2":{"technical":3,"tiki-taka":2,"pressing":2},
    }

    score = {
        "gegenpressing":0.0,"pressing":0.0,"tiki-taka":0.0,
        "possession":0.0,"counter":0.0,"direct":0.0,
        "wing-play":0.0,"low-block":0.0,"park-the-bus":0.0,
        "high-line":0.0,"reactive":0.0,"balanced":0.5,
    }

    fw = FORMATION_WEIGHTS.get(formation or "", {"balanced": 2})
    for style, weight in fw.items():
        score[style] = score.get(style, 0) + weight

    if possession >= 62:      score["tiki-taka"]+=5.0; score["possession"]+=4.0; score["high-line"]+=1.5
    elif possession >= 57:    score["possession"]+=3.0; score["tiki-taka"]+=2.0; score["pressing"]+=1.0
    elif possession >= 52:    score["possession"]+=1.5; score["balanced"]+=1.0
    elif possession <= 38:    score["counter"]+=5.0; score["direct"]+=2.0; score["low-block"]+=2.0; score["park-the-bus"]+=1.5
    elif possession <= 44:    score["counter"]+=3.0; score["low-block"]+=2.0; score["reactive"]+=1.5
    elif possession <= 48:    score["counter"]+=1.5; score["balanced"]+=1.0

    if accurate_pass_pct>=88: score["tiki-taka"]+=4.0; score["possession"]+=2.0
    elif accurate_pass_pct>=83: score["possession"]+=2.5; score["pressing"]+=1.0
    elif accurate_pass_pct>=78: score["balanced"]+=1.5; score["pressing"]+=0.5
    elif accurate_pass_pct<=68: score["direct"]+=3.5; score["counter"]+=1.5; score["low-block"]+=1.0
    elif accurate_pass_pct<=73: score["direct"]+=2.0; score["counter"]+=1.0

    if tackles_pg>=25:    score["gegenpressing"]+=5.0; score["pressing"]+=3.0
    elif tackles_pg>=20:  score["pressing"]+=4.0; score["gegenpressing"]+=2.0
    elif tackles_pg>=16:  score["pressing"]+=2.0; score["balanced"]+=1.0
    elif tackles_pg<=10:  score["low-block"]+=2.0; score["possession"]+=1.0; score["tiki-taka"]+=1.0

    if interceptions_pg>=10:  score["pressing"]+=3.0; score["gegenpressing"]+=2.0; score["high-line"]+=1.5
    elif interceptions_pg>=7: score["pressing"]+=2.0; score["balanced"]+=1.0
    elif interceptions_pg<=3: score["tiki-taka"]+=1.5; score["possession"]+=1.0

    if dribbles_pg>=7:    score["wing-play"]+=4.0; score["tiki-taka"]+=1.5; score["counter"]+=1.0
    elif dribbles_pg>=5:  score["wing-play"]+=2.5; score["tiki-taka"]+=1.0
    elif dribbles_pg<=1.5: score["direct"]+=2.0; score["low-block"]+=1.0

    if shots_pg>=18:  score["pressing"]+=2.5; score["high-line"]+=2.0; score["tiki-taka"]+=1.0
    elif shots_pg>=14: score["pressing"]+=1.5; score["high-line"]+=1.0
    elif shots_pg<=7:  score["low-block"]+=2.5; score["park-the-bus"]+=1.5; score["counter"]+=1.5
    elif shots_pg<=10: score["counter"]+=1.0; score["low-block"]+=1.0

    if big_chances_pg>=3.0:   score["tiki-taka"]+=2.0; score["wing-play"]+=2.0; score["pressing"]+=1.0
    elif big_chances_pg>=2.0: score["possession"]+=1.5; score["wing-play"]+=1.0
    elif big_chances_pg<=0.5: score["low-block"]+=2.0; score["park-the-bus"]+=1.5

    if goals_pg>=2.5:   score["pressing"]+=2.0; score["high-line"]+=1.5; score["tiki-taka"]+=1.0
    elif goals_pg>=1.8: score["pressing"]+=1.0; score["balanced"]+=1.0
    elif goals_pg<=0.7: score["park-the-bus"]+=3.0; score["low-block"]+=2.0; score["counter"]+=1.5

    if conceded_pg<=0.6:  score["high-line"]+=1.5; score["low-block"]+=1.5; score["park-the-bus"]+=1.0
    elif conceded_pg>=2.0: score["pressing"]+=1.5; score["high-line"]+=1.0
    elif conceded_pg>=1.5: score["balanced"]+=0.5

    first_half_goals = sum(1 for e in (last5_events or []) if e.get("firstHalfGoals", 0) > 0)
    if first_half_goals>=4:   score["high-line"]+=2.5; score["pressing"]+=1.5; score["gegenpressing"]+=1.0
    elif first_half_goals>=2: score["pressing"]+=1.0; score["high-line"]+=1.0

    if score["park-the-bus"]>3 and score["tiki-taka"]>3:
        score["balanced"]+=2.0; score["park-the-bus"]*=0.5; score["tiki-taka"]*=0.5
    if score["gegenpressing"]>3 and score["low-block"]>3:
        loser = "low-block" if possession>50 else "gegenpressing"
        score[loser]*=0.3

    return max(score, key=score.get)

def get_team_season_stats(team_id, league_id, season_id):
    data = fetch("https://www.sofascore.com/api/v1/team/{}/unique-tournament/{}/season/{}/statistics/overall".format(
        team_id, league_id, season_id))
    if not data or "statistics" not in data:
        return {}
    s = data["statistics"]
    m = max(s.get("matchesPlayed", 1), 1)
    return {
        "goalsPerGame":             round(s.get("goals", 0)/m, 2),
        "concededPerGame":          round(s.get("goalsConceded", 0)/m, 2),
        "shotsPerGame":             round(s.get("shots", s.get("shotsOnTarget",0)*1.6)/m, 1),
        "possession":               round(s.get("avgBallPossession", 50), 1),
        "accuratePassPct":          round(s.get("accuratePassesPercentage", 75), 1),
        "tacklesPerGame":           round(s.get("tackles", 0)/m, 1),
        "interceptionsPerGame":     round(s.get("interceptions", 0)/m, 1),
        "dribblesPerGame":          round(s.get("dribbles", 0)/m, 1),
        "bigChancesCreatedPerGame": round(s.get("bigChancesCreated", 0)/m, 2),
        "matchesPlayed":            m,
    }

def get_team_last5(team_id):
    data = fetch("https://www.sofascore.com/api/v1/team/{}/events/last/0".format(team_id))
    if not data or "events" not in data:
        return [], []
    events = sorted(data["events"], key=lambda x: x.get("startTimestamp",0), reverse=True)[:5]
    form, enriched = [], []
    for ev in events:
        ht = ev.get("homeTeam",{}).get("id")
        hw = ev.get("homeScore",{}).get("current",0) or 0
        aw = ev.get("awayScore",{}).get("current",0) or 0
        h_ht = ev.get("homeScore",{}).get("period1",0) or 0
        a_ht = ev.get("awayScore",{}).get("period1",0) or 0
        if ht == team_id:
            form.append("W" if hw>aw else "D" if hw==aw else "L")
            enriched.append({"firstHalfGoals": h_ht})
        else:
            form.append("W" if aw>hw else "D" if hw==aw else "L")
            enriched.append({"firstHalfGoals": a_ht})
    while len(form)<5: form.append("?")
    return form, enriched

def get_team_info(team_id):
    data = fetch("https://www.sofascore.com/api/v1/team/{}".format(team_id))
    if not data or "team" not in data:
        return {}
    t = data["team"]
    mgr = t.get("manager", {})
    venue = t.get("venue", {}) or {}
    coords = venue.get("coordinates") or {}
    city_raw = venue.get("city", {})
    city = city_raw.get("name","") if isinstance(city_raw, dict) else str(city_raw)
    return {
        "manager": mgr.get("name",""),
        "stadium": venue.get("name",""),
        "city":    city,
        "lat":     coords.get("latitude", 0),
        "lon":     coords.get("longitude", 0),
    }

def get_formation(team_id):
    data = fetch("https://www.sofascore.com/api/v1/team/{}/events/last/0".format(team_id))
    if not data or "events" not in data or not data["events"]:
        return ""
    last_ev = sorted(data["events"], key=lambda x: x.get("startTimestamp",0), reverse=True)[0]
    lineup = fetch("https://www.sofascore.com/api/v1/event/{}/lineups".format(last_ev["id"]))
    if not lineup: return ""
    home_id = last_ev.get("homeTeam",{}).get("id")
    side = "home" if home_id==team_id else "away"
    return (lineup.get(side) or {}).get("formation","")

def build_team_profile(team_id, league_id, season_id):
    info           = get_team_info(team_id)
    stats          = get_team_season_stats(team_id, league_id, season_id)
    form, enriched = get_team_last5(team_id)
    formation      = get_formation(team_id)
    style          = infer_style_from_data(stats, enriched, formation, stats.get("possession",50))
    gf   = stats.get("goalsPerGame", 1.2)
    gc   = stats.get("concededPerGame", 1.2)
    poss = stats.get("possession", 50) / 100
    rating = round(min(98, max(40,
        min(gf/2.5,1.0)*30 + max(1.0-gc/3.0,0.0)*30 + poss*20 + 20)))
    return {
        "manager":      info.get("manager",""),
        "managerStyle": style,
        "formation":    formation,
        "form":         form,
        "teamRating":   rating,
        "stadium":      info.get("stadium",""),
        "city":         info.get("city",""),
        "lat":          info.get("lat",0),
        "lon":          info.get("lon",0),
        "stats":        stats,
    }

def main():
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/odds.json","r",encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = {}

    upcoming  = existing.get("upcoming", [])
    sofascore = {}  # Her seferinde sifirdan olustur - guncel kalsin
    processed = {}

    print("SofaScore: {} mac taranıyor...".format(len(upcoming)))

    if not upcoming:
        print("UYARI: upcoming bos! odds.json kontrol edin.")
        existing["sofascore"] = sofascore
        existing["sofascore_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open("data/odds.json","w",encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return

    # Her lig icin season ID'yi dinamik cek
    league_seasons = {}
    for league_code, league_id in LEAGUE_IDS.items():
        season_id = get_current_season(league_id)
        if season_id:
            league_seasons[league_code] = (league_id, season_id)
            print("  {}: league={} season={}".format(league_code, league_id, season_id))

    # Lig bazi upcoming maclari grupla
    league_events = {}
    for league_code, (league_id, season_id) in league_seasons.items():
        evs = get_league_next_events(league_id, season_id)
        league_events[league_code] = evs
        print("  {}: {} mac bulundu SofaScore'da".format(league_code, len(evs)))

    # Her Nesine macini SofaScore'da eslestir
    for match in upcoming:
        league = match.get("league","OTHER")
        if league not in league_seasons:
            continue

        league_id, season_id = league_seasons[league]
        home_name = match.get("home","")
        away_name = match.get("away","")
        match_key = "{}_vs_{}".format(home_name, away_name)
        events    = league_events.get(league, [])

        for ev in events:
            ev_home = ev.get("homeTeam",{}).get("name","")
            ev_away = ev.get("awayTeam",{}).get("name","")

            h_ok = home_name[:4].lower() in ev_home.lower() or ev_home[:4].lower() in home_name.lower()
            a_ok = away_name[:4].lower() in ev_away.lower() or ev_away[:4].lower() in away_name.lower()
            if not (h_ok and a_ok):
                continue

            home_id = ev.get("homeTeam",{}).get("id")
            away_id = ev.get("awayTeam",{}).get("id")
            print("  ESLESTI: {} vs {}".format(ev_home, ev_away))

            if home_id not in processed:
                processed[home_id] = build_team_profile(home_id, league_id, season_id)
            if away_id not in processed:
                processed[away_id] = build_team_profile(away_id, league_id, season_id)

            hp = processed[home_id]
            ap = processed[away_id]
            print("    EV:  {} | {} | {}".format(hp["manager"], hp["managerStyle"], hp["formation"]))
            print("    DEP: {} | {} | {}".format(ap["manager"], ap["managerStyle"], ap["formation"]))

            sofascore[match_key] = {
                "eventId": ev["id"],
                "home": {**hp, "sofaName": ev_home, "id": home_id},
                "away": {**ap, "sofaName": ev_away, "id": away_id},
            }
            break

    existing["sofascore"]         = sofascore
    existing["sofascore_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open("data/odds.json","w",encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print("Tamam: {} mac islendi".format(len(sofascore)))

if __name__ == "__main__":
    main()
