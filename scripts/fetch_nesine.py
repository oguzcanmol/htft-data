import urllib.request, json, os
from datetime import datetime

NESINE_URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"

LEAGUE_MAP = {
    129:"ES1", 87:"EN1", 88:"DE1", 90:"IT1", 97:"FR1",
    174:"TR1", 186:"PT1", 185:"NL1", 192:"GR1", 180:"BE1",
    175:"TR1", 573:"EN1", 576:"DE1", 577:"ES1", 578:"IT1"
}

HTFT_MAP = {1:"1/1",2:"1/X",3:"1/2",4:"X/1",5:"X/X",6:"X/2",7:"2/1",8:"2/X",9:"2/2"}

def fetch_nesine():
    req = urllib.request.Request(NESINE_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.nesine.com/"
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def parse(data):
    matches = []
    for ev in data.get("sg", {}).get("EA", []):
        if not ev.get("HN") or not ev.get("AN") or ev.get("TYPE", 0) < 0:
            continue
        markets = ev.get("MA", [])
        main = next((m for m in markets if m.get("MTID")==1 and m.get("MBS")==2), None)
        open_m = next((m for m in markets if m.get("MTID")==1 and m.get("MBS")==1), None)
        htft_m = next((m for m in markets if m.get("MTID")==5), None)
        if not main: main = next((m for m in markets if m.get("MTID")==1), None)
        if not main: continue
        oca = main.get("OCA", [])
        h = next((o["O"] for o in oca if o.get("N")==1), None)
        d = next((o["O"] for o in oca if o.get("N")==2), None)
        a = next((o["O"] for o in oca if o.get("N")==3), None)
        if not all([h,d,a]): continue
        oca_o = (open_m or main).get("OCA", [])
        oh = next((o["O"] for o in oca_o if o.get("N")==1), h)
        od = next((o["O"] for o in oca_o if o.get("N")==2), d)
        oa = next((o["O"] for o in oca_o if o.get("N")==3), a)
        htft = {}
        if htft_m:
            for o in htft_m.get("OCA", []):
                if o.get("N") in HTFT_MAP: htft[HTFT_MAP[o["N"]]] = o["O"]
        parts = (ev.get("D","") or "").split(".")
        date = "{}-{}-{}".format(parts[2],parts[1],parts[0]) if len(parts)==3 else ""
        matches.append({
            "league": LEAGUE_MAP.get(ev.get("LC",0), "OTHER"),
            "leagueName": ev.get("ENN",""),
            "date": date, "time": ev.get("T",""),
            "home": ev["HN"], "away": ev["AN"],
            "open": {"h":oh,"d":od,"a":oa},
            "close": {"h":h,"d":d,"a":a},
            "htft": htft, "nesineId": ev.get("C",0)
        })
    return sorted(matches, key=lambda x: x["date"]+x["time"])

def main():
    os.makedirs("data", exist_ok=True)
    print("Nesine cekiliyor...")
    try:
        matches = parse(fetch_nesine())
        print("  {} mac bulundu".format(len(matches)))
    except Exception as e:
        print("HATA: {}".format(e))
        matches = []
    try:
        with open("data/odds.json","r",encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = {}
    existing["upcoming"] = matches
    existing["nesine_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("data/odds.json","w",encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print("Kaydedildi: {} mac".format(len(matches)))

if __name__ == "__main__":
    main()
