import json
import requests
from pathlib import Path

OUT = Path("data/team_profiles_v2.json")

teams = [
    "Galatasaray",
    "Fenerbahce",
    "Besiktas",
    "Trabzonspor"
]

profiles = {}

for team in teams:
    url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={team}"

    try:
        r = requests.get(url, timeout=10)
        js = r.json()

        if js.get("teams"):
            t = js["teams"][0]

            profiles[team] = {
                "coach": t.get("strManager", "Bilinmiyor"),
                "formation": "4-2-3-1",
                "rating": 70,
                "form": "DDDDD",
                "psychology": 65
            }

    except:
        profiles[team] = {
            "coach": "Bilinmiyor",
            "formation": "4-2-3-1",
            "rating": 50,
            "form": "DDDDD",
            "psychology": 50
        }

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(profiles, f, ensure_ascii=False, indent=2)

print("tamamlandi")
