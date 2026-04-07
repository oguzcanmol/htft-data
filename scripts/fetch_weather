import urllib.request, json, os
from datetime import datetime

def get_surface_condition(rain_mm, wind_kmh, temp_c):
    if rain_mm > 5:   return "heavy"
    elif rain_mm > 1: return "soft"
    elif temp_c > 32: return "firm"
    else:             return "good"

def get_weather(lat, lon, api_key):
    if not lat or not lon:
        return {}
    url = "https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}&units=metric".format(
        lat, lon, api_key)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
            temp = round(d["main"]["temp"])
            wind = round(d["wind"]["speed"] * 3.6)
            rain = d.get("rain", {}).get("1h", 0)
            return {
                "temp_c": temp,
                "humidity": d["main"]["humidity"],
                "wind_kmh": wind,
                "rain_mm": rain,
                "description": d["weather"][0]["description"],
                "condition": d["weather"][0]["main"],
                "surface_condition": get_surface_condition(rain, wind, temp),
            }
    except Exception as e:
        print("  Hava hatasi: {}".format(e))
        return {}

def main():
    api_key = os.environ.get("OPENWEATHER_API_KEY", "")
    if not api_key:
        print("OPENWEATHER_API_KEY yok, atlaniyor...")
        return

    try:
        with open("data/odds.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = {}

    sofascore = existing.get("sofascore", {})
    weather_data = {}

    # SofaScore'dan gelen koordinatlara göre hava çek
    for match_key, match_data in sofascore.items():
        home = match_data.get("home", {})
        lat = home.get("lat", 0)
        lon = home.get("lon", 0)
        city = home.get("city", "")
        stadium = home.get("stadium", "")

        if lat and lon and match_key not in weather_data:
            print("  {} - {}...".format(city or match_key, stadium))
            w = get_weather(lat, lon, api_key)
            weather_data[match_key] = {
                "city": city,
                "stadium": stadium,
                "weather": w,
                "surface_condition": w.get("surface_condition", "good"),
            }

    existing["weather"] = weather_data
    existing["weather_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open("data/odds.json", "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print("Hava durumu kaydedildi: {} mac".format(len(weather_data)))

if __name__ == "__main__":
    main()
