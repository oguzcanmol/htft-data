import urllib.request, json, os, time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

TEAM_IDS = {
    "Galatasaray":2918,"Fenerbahce":2919,"Besiktas":2920,"Trabzonspor":2931,
    "Basaksehir":5981,"Sivasspor":2928,"Konyaspor":2930,"Alanyaspor":262309,
    "Kasimpasa":2933,"Antalyaspor":2929,"Kayserispor":2935,"Rizespor":2932,
    "Samsunspor":2927,"Gaziantep":2936,"Kocaelispor":2934,"Goztepe":2926,
    "Adana Demirspor":261274,"Eyupspor":680742,"Bodrum":680741,
    "Arsenal":42,"Chelsea":38,"Liverpool":44,"Man City":17,
    "Man United":35,"Tottenham":33,"Newcastle":39,"Aston Villa":40,
    "Brighton":30,"West Ham":37,
    "Real Madrid":2829,"Barcelona":2817,"Atletico Madrid":2836,
    "Sevilla":2833,"Villarreal":2828,"Athletic Bilbao":2825,
    "Bayern Munich":2672,"Dortmund":2673,"RB Leipzig":37945,"Leverkusen":2674,
    "Juventus":2686,"Inter Milan":2697,"AC Milan":2692,"Napoli":2714,
    "PSG":2172,"Monaco":2173,"Marseille":2175,"Lyon":2174,
}

def fetch(url, delay=1):
    time.sleep(delay)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("  HATA: {} -> {}".format(url, e))
        return None

def get_team_form(team_id):
    data = fetch("https://www.sofascore.com/api/v1/team/{}/last/5".format(team_id))
    if not data or "events" not in data:
        return ["D","D","D","D","D"]
    form = []
    for ev in data["events"][:5]:
        ht = ev.get("homeTeam",{}).get("id")
        hw = ev.get("homeScore",{}).get("current",0) or 0
        aw = ev.get("awayScore",{}).get("current",0) or 0
        if ht == team_id:
            form.append("W" if hw > aw else "D" if hw == aw else "L")
        else:
            form.append("W" if aw > hw else "D" if hw == aw else "L")
    while len(form) < 5:
        form.append("D")
    return form

def get_team_info(team_id):
    data = fetch("https://www.sofascore.com/api/v1/team/{}".format(team_id))
    if not data or "team" not in data:
        return {}
    t = data["team"]
    manager = t.get("manager", {})
    return {"manager_name": manager.get("name","")}

def get_team_stats(team_id):
    stats = {}
    for tid in [52, 17, 8, 35, 23, 34]:
        data = fetch("https://www.sofascore.com/api/v1/team/{}/unique-tournament/{}/season/stats/overall".format(team_id, tid))
        if data and "stats" in data:
            s = data["stats"]
            m = s.get("matches", 1) or 1
            stats = {
                "goals_per_game": round(s.get("goalsScored",0)/m, 2),
                "conceded_per_game": round(s.get("goalsConceded",0)/m, 2),
                "possession_avg": round(s.get("avgBallPossessionPercent",50), 1),
                "pressing_index": round(s.get("tacklesPerGame",5)*2, 1),
            }
            if stats["goals_per_game"] > 0:
                break
    return stats

def calc_ratings(stats, form):
    form_score = sum(3 if r=="W" else 1 if r=="D" else 0 for r in form) / 15
    goals = stats.get("goals_per_game", 1.2)
    conceded = stats.get("conceded_per_game", 1.2)
    pressing = min(stats.get("pressing_index", 10) / 20, 1.0)
    poss = stats.get("possession_avg", 50) / 100
    attack = min(goals / 2.5, 1.0)
    defense = max(1.0 - conceded / 3.0, 0.0)
    rating = round((attack*0.30 + defense*0.30 + form_score*0.25 + poss*0.15) * 100)
    style = "pressing" if pressing > 0.6 else "technical" if poss > 0.55 else "counter" if goals > 1.5 and poss < 0.45 else "balanced"
    char = {
        "determination": round(10 + form_score*10),
        "bravery": round(10 + pressing*8),
        "composure": round(8 + poss*10),
        "leadership": round(10 + form_score*6),
        "workRate": round(10 + pressing*8),
        "teamwork": round(10 + poss*8),
        "concentration": round(10 + defense*8),
    }
    mgr = {
        "manManagement": round(10 + form_score*8),
        "tactical": round(10 + poss*8),
        "motivation": round(10 + form_score*9),
        "adaptability": 13,
        "pressureHandling": round(10 + form_score*7),
    }
    return rating, style, char, mgr

def main():
    os.makedirs("data", exist_ok=True)
    print("SofaScore profilleri cekiliyor...")
    profiles = {}
    total = len(TEAM_IDS)
    for i, (name, team_id) in enumerate(TEAM_IDS.items()):
        print("[{}/{}] {}...".format(i+1, total, name))
        form = get_team_form(team_id)
        info = get_team_info(team_id)
        stats = get_team_stats(team_id)
        rating, style, char, mgr = calc_ratings(stats, form)
        profiles[name] = {
            "id": team_id, "teamRating": rating, "style": style,
            "last5": form, "manager": info.get("manager_name",""),
            "character": char, "managerStats": mgr, "stats": stats,
            "updated": datetime.now().strftime("%Y-%m-%d"),
        }
        print("  Rating:{} Form:{} Stil:{} Hoca:{}".format(rating, form, style, info.get("manager_name","?")))
    try:
        with open("data/odds.json","r",encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = {}
    existing["team_profiles"] = profiles
    existing["profiles_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("data/odds.json","w",encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print("Tamam: {} takim kaydedildi".format(len(profiles)))

if __name__ == "__main__":
    main()
