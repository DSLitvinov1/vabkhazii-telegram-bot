import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = "Europe/Moscow"
CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FORCE_MODE = os.getenv("POST_MODE", "auto").lower()

# Координаты используются только для прогноза погоды.
PLACES = {
    "Гагра": (43.2783, 40.2712),
    "Рица": (43.4840, 40.5430),
    "Новый Афон": (43.0877, 40.8136),
    "Восточная Абхазия": (42.8528, 41.6805),
    "Мзы": (43.4160, 40.5680),
}

SEA_POINT = (43.2600, 40.2400)

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
    96: "гроза с градом",
    99: "сильная гроза",
}

MONTHS = {
    1: "ЯНВАРЯ",
    2: "ФЕВРАЛЯ",
    3: "МАРТА",
    4: "АПРЕЛЯ",
    5: "МАЯ",
    6: "ИЮНЯ",
    7: "ИЮЛЯ",
    8: "АВГУСТА",
    9: "СЕНТЯБРЯ",
    10: "ОКТЯБРЯ",
    11: "НОЯБРЯ",
    12: "ДЕКАБРЯ",
}

SEVERE_CODES = {65, 75, 82, 95, 96, 99}
WET_CODES = {
    51, 53, 55,
    61, 63, 65,
    80, 81, 82,
    95, 96, 99,
}

FOG_CODES = {45, 48}


def get_json(base_url, params):
    url = base_url + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "VAbkhaziiBot/2.0"},
    )

    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(
            resp.read().decode("utf-8")
        )


def weather_for(lat, lon):

    data = get_json(
        WEATHER_URL,
        {
            "latitude": lat,
            "longitude": lon,

            "current":
                "temperature_2m,"
                "weather_code,"
                "cloud_cover,"
                "wind_speed_10m",

            "daily":
                "weather_code,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max,"
                "precipitation_sum,"
                "wind_speed_10m_max",

            "forecast_days": 2,
            "timezone": TZ,
        },
    )

    cur = data["current"]
    daily = data["daily"]

    days = []

    for i in range(2):

        days.append({

            "date":
                daily["time"][i],

            "code":
                int(daily["weather_code"][i]),

            "max":
                round(
                    daily["temperature_2m_max"][i]
                ),

            "min":
                round(
                    daily["temperature_2m_min"][i]
                ),

            "rain_prob":
                int(
                    daily[
                        "precipitation_probability_max"
                    ][i] or 0
                ),

            "rain_sum":
                float(
                    daily[
                        "precipitation_sum"
                    ][i] or 0
                ),

            "wind_max":
                round(
                    daily[
                        "wind_speed_10m_max"
                    ][i] or 0
                ),
        })

    return {

        "current": {

            "temp":
                round(
                    cur["temperature_2m"]
                ),

            "code":
                int(
                    cur["weather_code"]
                ),

            "cloud":
                int(
                    cur["cloud_cover"]
                ),

            "wind":
                round(
                    cur["wind_speed_10m"]
                ),
        },

        "days": days,
    }


def marine_now():

    lat, lon = SEA_POINT

    try:

        data = get_json(
            MARINE_URL,
            {
                "latitude": lat,
                "longitude": lon,

                "current":
                    "sea_surface_temperature,"
                    "wave_height",

                "timezone": TZ,
            },
        )

        cur = data.get(
            "current",
            {}
        )

        return {
            "sea_temp":
                cur.get(
                    "sea_surface_temperature"
                ),

            "wave":
                cur.get(
                    "wave_height"
                ),
        }

    except Exception as exc:

        print(
            "Marine API warning:",
            exc
        )

        return {
            "sea_temp": None,
            "wave": None,
        }


def route_status(name, day):

    code = day["code"]
    rain = day["rain_prob"]
    wind = day["wind_max"]

    # Мзы — высокогорье,
    # поэтому требования строже.
    if name == "Мзы":

        if (
            code in SEVERE_CODES
            or rain >= 60
            or wind >= 40
        ):

            return (
                "🔴",
                "лучше выбрать другой маршрут",
                3,
            )

        if (
            code in WET_CODES
            or code in FOG_CODES
            or rain >= 30
            or wind >= 28
        ):

            return (
                "🟡",
                "высокогорье: погода может быстро измениться",
                2,
            )

        return (
            "🟢",
            "хорошие условия по прогнозу",
            1,
        )

    # Рица
    if name == "Рица":

        if (
            code in SEVERE_CODES
            or rain >= 75
            or wind >= 45
        ):

            return (
                "🔴",
                "лучше перенести ради безопасности и видов",
                3,
            )

        if (
            code in WET_CODES
            or code in FOG_CODES
            or rain >= 40
            or wind >= 32
        ):

            return (
                "🟡",
                "ехать можно, но панорамы могут быть хуже",
                2,
            )

        return (
            "🟢",
            "хороший вариант для видов и фотографий",
            1,
        )

    # Восточная Абхазия
    if name == "Восточная Абхазия":

        if (
            code in SEVERE_CODES
            or rain >= 80
            or wind >= 45
        ):

            return (
                "🔴",
                "сильная непогода — лучше выбрать другой день",
                3,
            )

        if (
            code in WET_CODES
            or rain >= 50
            or wind >= 35
        ):

            return (
                "🟡",
                "можно, но учитывайте осадки",
                2,
            )

        return (
            "🟢",
            "хороший день для Акармары и водопадов",
            1,
        )

    # Новый Афон
    if (
        code in SEVERE_CODES
        or rain >= 85
    ):

        return (
            "🔴",
            "при сильной непогоде лучше перенести",
            3,
        )

    if (
        code in WET_CODES
        or rain >= 55
        or wind >= 38
    ):

        return (
            "🟡",
            "подойдёт, но возможны осадки",
            2,
        )

    return (
        "🟢",
        "комфортный вариант по прогнозу",
        1,
    )


def choose_best(
    weather,
    day_index
):

    candidates = [
        "Рица",
        "Новый Афон",
        "Восточная Абхазия",
        "Мзы",
    ]

    scored = []

    for name in candidates:

        day = weather[name]["days"][day_index]

        _, _, status_score = route_status(
            name,
            day
        )

        sensitivity = (
            1.25
            if name in {"Рица", "Мзы"}
            else 1.0
        )

        score = (
            status_score * 100
            + sensitivity * day["rain_prob"]
            + day["rain_sum"] * 8
            + max(
                0,
                day["wind_max"] - 18
            ) * 2
        )

        scored.append(
            (score, name)
        )

    scored.sort()

    return scored[0][1]


def fmt_num(value):

    if value is None:
        return None

    return f"{float(value):.1f}"


def date_title(iso_date):

    dt = datetime.strptime(
        iso_date,
        "%Y-%m-%d"
    )

    return (
        f"{dt.day} "
        f"{MONTHS[dt.month]}"
    )


def sea_line(marine):

    sea_temp = marine.get(
        "sea_temp"
    )

    wave = marine.get(
        "wave"
    )

    if (
        sea_temp is None
        and wave is None
    ):

        return None

    parts = []

    if sea_temp is not None:

        parts.append(
            f"вода около "
            f"<b>+{fmt_num(sea_temp)}°C</b>"
        )

    if wave is not None:

        if wave < 0.4:
            state = "море спокойное"

        elif wave < 0.8:
            state = "небольшая волна"

        elif wave < 1.4:
            state = "заметная волна"

        else:
            state = "море волнуется"

        parts.append(
            f"{state}, "
            f"около "
            f"<b>{fmt_num(wave)} м</b>"
        )

    return (
        "🌊 Море: "
        + ", ".join(parts)
        + "."
    )


def build_morning_post(
    weather,
    marine
):

    g = weather["Гагра"]

    today = g["days"][0]
    cur = g["current"]

    best = choose_best(
        weather,
        0
    )

    weather_desc = WEATHER_TEXT.get(
        today["code"],
        "переменная погода"
    )

    lines = [

        f"🇦🇧 <b>АБХАЗИЯ СЕГОДНЯ | "
        f"{date_title(today['date'])}</b>",

        "",

        f"🌤 Побережье: "
        f"<b>{weather_desc}</b>. "
        f"Сейчас около "
        f"<b>+{cur['temp']}°C</b>, "
        f"днём до "
        f"<b>+{today['max']}°C</b>.",

        f"🌧 Осадки: вероятность до "
        f"<b>{today['rain_prob']}%</b>. "
        f"Ветер до "
        f"<b>{today['wind_max']} км/ч</b>.",
    ]

    sline = sea_line(
        marine
    )

    if sline:
        lines.append(
            sline
        )

    lines += [
        "",
        "<b>Куда я бы поехал сегодня:</b>",
    ]

    for name in [
        "Рица",
        "Новый Афон",
        "Восточная Абхазия",
        "Мзы",
    ]:

        day = weather[name]["days"][0]

        emoji, note, _ = route_status(
            name,
            day
        )

        lines.append(

            f"{emoji} "
            f"<b>{name}</b> — "
            f"{note}. "
            f"Днём около "
            f"+{day['max']}°C, "
            f"осадки до "
            f"{day['rain_prob']}%."
        )

    lines += [

        "",

        f"🔥 <b>МОЙ ВЫБОР НА СЕГОДНЯ: "
        f"{best.upper()}</b>",

        "По прогнозу это один из наиболее "
        "удачных вариантов на день.",

        "",

        "⚠️ Для горных маршрутов прогноз — "
        "ориентир. Погода в горах может "
        "меняться быстро.",

        "⚠️ В горах погода переменчива, поэтому перед выездом всегда учитывайте текущую обстановку на маршруте.",
        "",

        "📍 <b>Уже отдыхаете в Абхазии?</b>",

        "Напишите "
        "<b>город + сколько вас человек</b> "
        "— подскажу маршрут на сегодня "
        "или завтра.",

        "",

        "👉 @VAbkhazii",
    ]

    return "\n".join(
        lines
    )


def build_evening_post(
    weather
):

    g = weather["Гагра"]

    tomorrow = g["days"][1]

    best = choose_best(
        weather,
        1
    )

    weather_desc = WEATHER_TEXT.get(
        tomorrow["code"],
        "переменная погода"
    )

    lines = [

        f"🚙 <b>КУДА ЕДЕМ ЗАВТРА | "
        f"{date_title(tomorrow['date'])}</b>",

        "",

        f"🌤 На побережье ожидается "
        f"<b>{weather_desc}</b>.",

        f"🌡 Температура примерно "
        f"<b>+{tomorrow['min']}…"
        f"+{tomorrow['max']}°C</b>.",

        f"🌧 Вероятность осадков — "
        f"до <b>{tomorrow['rain_prob']}%</b>.",

        f"💨 Ветер до "
        f"<b>{tomorrow['wind_max']} км/ч</b>.",

        "",

        "<b>Что выбрать на завтра:</b>",
    ]

    for name in [
        "Рица",
        "Новый Афон",
        "Восточная Абхазия",
        "Мзы",
    ]:

        day = weather[name]["days"][1]

        emoji, note, _ = route_status(
            name,
            day
        )

        lines.append(

            f"{emoji} "
            f"<b>{name}</b> — "
            f"{note}. "
            f"Осадки до "
            f"{day['rain_prob']}%, "
            f"днём около "
            f"+{day['max']}°C."
        )

    lines += [

        "",

        f"🔥 <b>МОЯ РЕКОМЕНДАЦИЯ "
        f"НА ЗАВТРА: "
        f"{best.upper()}</b>",

        "",

        "Свободные места бот специально "
        "не указывает автоматически — "
        "только реальные данные "
        "после подтверждения.",

        "",

        "📩 Хотите подобрать поездку? "
        "Напишите "
        "<b>где вы отдыхаете + "
        "сколько вас человек</b>.",

        "👉 @VAbkhazii",
    ]

    return "\n".join(
        lines
    )


def send_telegram(text):

    if not BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set"
        )

    url = TG_URL.format(
        token=BOT_TOKEN
    )

    payload = urllib.parse.urlencode({

        "chat_id":
            CHANNEL,

        "text":
            text,

        "parse_mode":
            "HTML",

        "disable_web_page_preview":
            "true",

    }).encode(
        "utf-8"
    )

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST"
    )

    with urllib.request.urlopen(
        req,
        timeout=25
    ) as resp:

        result = json.loads(
            resp.read().decode(
                "utf-8"
            )
        )

    if not result.get(
        "ok"
    ):

        raise RuntimeError(
            f"Telegram error: {result}"
        )

    return result


def choose_mode():

    if FORCE_MODE in {
        "morning",
        "evening",
    }:

        return FORCE_MODE

    hour = datetime.now(
        ZoneInfo(TZ)
    ).hour

    if hour >= 15:
        return "evening"

    return "morning"


def main():

    weather = {

        name:
            weather_for(
                *coords
            )

        for name, coords
        in PLACES.items()
    }

    mode = choose_mode()

    if mode == "evening":

        post = build_evening_post(
            weather
        )

    else:

        marine = marine_now()

        post = build_morning_post(
            weather,
            marine
        )

    print(
        post
    )

    send_telegram(
        post
    )


if __name__ == "__main__":
    main()
