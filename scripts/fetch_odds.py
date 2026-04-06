"""
HTFT Elite — Otomatik Veri Cekici
football-data.co.uk -> data/odds.json
"""
import urllib.request, csv, json, io, os
from datetime import datetime

LEAGUES = {
    "TR1": {"name": "Super Lig",      "code": "T1"},
    "EN1": {"name": "Premier League", "code": "E0"},
    "ES1": {"name": "La Liga",        "code": "SP1"},
    "DE1": {"name": "Bundesliga",     "code": "D1"},
    "IT1": {"name": "Serie A",        "code": "I1"},
    "FR1": {"name": "Ligue 1",        "code": "F1"},
    "PT1": {"name": "Primeira Liga",  "code": "P1"},
    "NL1": {"name": "Eredivisie",     "code": "N1"},
    "GR1": {"name": "Super League",   "code": "G1"},
    "BE1": {"name": "First Div A",    "code": "B1"},
}

SEASONS = ["2526", "2425"]
BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"

def safe_float(val, default=None):
    try:
        v = float(val)
        return v if v > 0 else default
    except:
        return default

def parse_date(date_str):
    for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except:
            continue
    return date_str

def htft_code(htr, ftr):
    mapping = {"H": "1", "D": "X", "A": "2"}
    return "{}/{}".format(mapping.get(htr,"?"), mapping.get(ftr,"?"))

def fetch_league(league_id, season):
    code = LEAGUES[league_id]["code"]
    url  = BASE_URL.format(season=season, code=code)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode("latin-1")
    except Exception as e:
        print("  HATA ({} {}): {}".format(league_id, season, e))
        return []
    matches = []
    reader  = csv.DictReader(io.StringIO(content))
    for row in reader:
        if not row.get("HomeTeam") or not row.get("Date"):
            continue
        open_h = safe_float(row.get("B365H")) or safe_float(row.get("PSH")) or safe_float(row.get("WHH"))
        open_d = safe_float(row.get("B365D")) or safe_float(row.get("PSD")) or safe_float(row.get("WHD"))
        open_a = safe_float(row.get("B365A")) or safe_float(row.get("PSA")) or safe_float(row.get("WHA"))
        if not open_h:
            continue
        close_h = safe_float(row.get("MaxH")) or open_h
        close_d = safe_float(row.get("MaxD")) or open_d
        close_a = safe_float(row.get("MaxA")) or open_a
        ftr  = row.get("FTR", "")
        htr  = row.get("HTR", "")
        fthg = safe_float(row.get("FTHG"), 0)
        ftag = safe_float(row.get("FTAG"), 0)
        hthg = safe_float(row.get("HTHG"), 0)
        htag = safe_float(row.get("HTAG"), 0)
        matches.append({
            "league": league_id, "season": season,
            "date": parse_date(row["Date"]),
            "home": row["HomeTeam"].strip(),
            "away": row["AwayTeam"].strip(),
            "open":  {"h": open_h,  "d": open_d,  "a": open_a},
            "close": {"h": close_h, "d": close_d, "a": close_a},
            "ht_score": "{}-{}".format(int(hthg), int(htag)) if htr else None,
            "ft_score": "{}-{}".format(int(fthg), int(ftag)) if ftr else None,
            "htr": htr, "ftr": ftr,
            "htft": htft_code(htr, ftr) if htr and ftr else None,
        })
    print("  {} {}: {} mac".format(league_id, season, len(matches)))
    return matches

def build_htft_matrix(matches):
    cats = {"strongHome": [], "balanced": [], "strongAway": []}
    for m in matches:
        if not m["htft"] or "?" in m["htft"]:
            continue
        oh, oa = m["open"]["h"], m["open"]["a"]
        cat = "strongHome" if oh < 1.60 else "strongAway" if oa < 1.80 else "balanced"
        cats[cat].append(m["htft"])
    combos = ["1/1","1/X","1/2","X/1","X/X","X/2","2/1","2/X","2/2"]
    matrix = {}
    for cat, results in cats.items():
        total = len(results) or 1
        matrix[cat] = {c: round(results.count(c)/total, 4) for c in combos}
    return matrix

def get_upcoming(matches):
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = [m for m in matches if m.get("date","") >= today and not m.get("ftr")]
    return sorted(upcoming, key=lambda x: x["date"])[:60]

def main():
    os.makedirs("data", exist_ok=True)
    all_matches = []
    for league_id in LEAGUES:
        for season in SEASONS:
            print("Cekiliyor: {} {}".format(league_id, season))
            all_matches.extend(fetch_league(league_id, season))
    print("\nToplam: {} mac".format(len(all_matches)))
    completed = [m for m in all_matches if m.get("htft")]
    matrix    = build_htft_matrix(completed)
    upcoming  = get_upcoming(all_matches)
    teams = {}
    for m in all_matches[-800:]:
        for side in ["home", "away"]:
            key = "{}:{}".format(m["league"], m[side])
            if key not in teams:
                teams[key] = {"name": m[side], "league": m["league"], "last5": []}
            if m.get("ftr") and len(teams[key]["last5"]) < 5:
                if side == "home":
                    r = "W" if m["ftr"]=="H" else "D" if m["ftr"]=="D" else "L"
                else:
                    r = "W" if m["ftr"]=="A" else "D" if m["ftr"]=="D" else "L"
                teams[key]["last5"].insert(0, r)
    output = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "matrix": matrix, "upcoming": upcoming,
        "teams": teams, "total_matches": len(all_matches)
    }
    with open("data/odds.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Kaydedildi: {} KB".format(len(json.dumps(output))//1024))

if __name__ == "__main__":
    main()
