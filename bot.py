import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = "Asia/Tbilisi"
CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Approximate coordinates for the main tourism areas used only for weather forecasts.
PLACES = {
    "Гагра": (43.2783, 40.2712),
    "Рица": (43.4840, 40.5430),
    "Новый Афон": (43.0877, 40.8136),
    "Восточная Абхазия": (42.8528, 41.6805),  # Ткуарчал area
}
SEA_POINT = (43.2600, 40.2400)  # Black Sea near Gagra coast

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
TG_URL = "https://api.telegram.org/bot{token}/sendMessage"

WEATHER_TEXT = {
    0: "ясно",
    1: "преимущественно ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "туман",
    51: "морось",
    53: "морось",
    55: "морось",
    61: "небольшой дождь",
    63: "дождь",
    65: "сильный дождь",
    71: "небольшой снег",
    73: "снег",
    75: "сильный снег",
    80: "ливни",
    81: "ливни",
    82: "сильные ливни",
    95: "гроза",
    96: "гроза",
    99: "сильная гроза",
}


def get_json(base_url, params):
    url = base_url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "VAbkhaziiBot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def weather_for(lat, lon):
    data = get_json(
        WEATHER_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,cloud_cover,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "forecast_days": 1,
            "timezone": TZ,
        },
    )
    cur = data["current"]
    daily = data["daily"]
    return {
        "temp": round(cur["temperature_2m"]),
        "code": int(cur["weather_code"]),
        "cloud": int(cur["cloud_cover"]),
        "wind": round(cur["wind_speed_10m"]),
        "max": round(daily["temperature_2m_max"][0]),
        "min": round(daily["temperature_2m_min"][0]),
        "rain_prob": int(daily["precipitation_probability_max"][0] or 0),
        "daily_code": int(daily["weather_code"][0]),
    }


def marine_now():
    lat, lon = SEA_POINT
    data = get_json(
        MARINE_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "current": "sea_surface_temperature,wave_height",
            "timezone": TZ,
        },
    )
    cur = data.get("current", {})
    return {
        "sea_temp": cur.get("sea_surface_temperature"),
        "wave": cur.get("wave_height"),
    }


def status_for(w):
    bad_codes = {65, 75, 82, 95, 96, 99}
    wet_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
    if w["daily_code"] in bad_codes or w["rain_prob"] >= 70:
        return "🔴", "сегодня лучше выбрать другое направление"
    if w["daily_code"] in wet_codes or w["rain_prob"] >= 40 or w["cloud"] >= 85:
        return "🟡", "можно, но погода может помешать видам"
    return "🟢", "хороший вариант по погоде"


def choose_best(data):
    # Lower score is better. Mountain routes get a heavier rain/cloud penalty.
    scores = {}
    for name, w in data.items():
        if name == "Гагра":
            continue
        mountain = 1.35 if name in {"Рица", "Восточная Абхазия"} else 1.0
        scores[name] = mountain * (w["rain_prob"] * 1.3 + w["cloud"] * 0.45 + max(0, w["wind"] - 18) * 2)
    return min(scores, key=scores.get)


def fmt_num(v, digits=1):
    if v is None:
        return "н/д"
    return f"{v:.{digits}f}"


def build_post(weather, marine):
    now = datetime.now(ZoneInfo(TZ))
    date_text = now.strftime("%d.%m.%Y")
    g = weather["Гагра"]
    weather_desc = WEATHER_TEXT.get(g["daily_code"], "переменная погода")

    sea_temp = marine.get("sea_temp")
    wave = marine.get("wave")
    if wave is None:
        sea_state = "данные о волне недоступны"
    elif wave < 0.4:
        sea_state = "море спокойное"
    elif wave < 0.8:
        sea_state = "небольшая волна"
    else:
        sea_state = "заметная волна"

    best = choose_best(weather)

    lines = [
        f"🇦🇧 <b>АБХАЗИЯ СЕГОДНЯ | {date_text}</b>",
        "",
        f"🌤 Побережье: <b>{weather_desc}</b>, сейчас около <b>+{g['temp']}°C</b>, днём до <b>+{g['max']}°C</b>.",
        f"🌧 Вероятность осадков: до <b>{g['rain_prob']}%</b>.",
        f"🌊 Море: <b>{fmt_num(sea_temp)}°C</b>, {sea_state} (волна около {fmt_num(wave)} м).",
        "",
        "<b>Куда я бы поехал сегодня:</b>",
    ]

    for name in ["Рица", "Новый Афон", "Восточная Абхазия"]:
        emoji, note = status_for(weather[name])
        w = weather[name]
        lines.append(f"{emoji} <b>{name}</b> — {note}; осадки до {w['rain_prob']}%, днём около +{w['max']}°C.")

    lines += [
        "",
        f"🔥 <b>МОЙ ВЫБОР НА СЕГОДНЯ: {best.upper()}</b>",
        "По прогнозу сейчас это один из наиболее комфортных вариантов. Перед выездом в горы всё равно учитывайте локальные изменения погоды и состояние дороги.",
        "",
        "📍 Уже отдыхаете в Абхазии?",
        "Напишите <b>город + сколько вас человек</b> — подберём маршрут на сегодня или завтра.",
        "",
        "👉 @VAbkhazii",
    ]
    return "\n".join(lines)


def send_telegram(text):
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    url = TG_URL.format(token=BOT_TOKEN)
    payload = urllib.parse.urlencode(
        {
            "chat_id": CHANNEL,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram error: {result}")
    return result


def main():
    weather = {name: weather_for(*coords) for name, coords in PLACES.items()}
    marine = marine_now()
    post = build_post(weather, marine)
    print(post)
    send_telegram(post)


if __name__ == "__main__":
    main()
