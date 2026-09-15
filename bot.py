import json
import os
import re
import html
import hashlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TZ = "Europe/Moscow"

CHANNEL = os.getenv(
    "TELEGRAM_CHANNEL",
    "@VAbkhazii"
)

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

STATE_DIR = Path(".bot_state")
STATE_FILE = STATE_DIR / "state.json"


PLACES = {
    "Гагра": (43.2783, 40.2712),
    "Рица": (43.4840, 40.5430),
    "Новый Афон": (43.0877, 40.8136),
    "Восточная Абхазия": (42.8528, 41.6805),
    "Мзы": (43.4160, 40.5680),
}

SEA_POINT = (43.2600, 40.2400)


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

MARINE_URL = (
    "https://marine-api.open-meteo.com/v1/marine"
)

TG_URL = (
    "https://api.telegram.org/"
    "bot{token}/sendMessage"
)


NEWS_QUERIES = [
    (
        "Абхазия туризм OR фестиваль OR культура "
        "OR природа OR гастрономия OR музей "
        "OR выставка OR концерт when:2d"
    ),
    (
        "Абхазия Гагра OR Пицунда OR Новый Афон "
        "OR Рица OR Сухум OR Акармара OR Мзы when:2d"
    ),
    (
        "Абхазия отдых OR путешествия "
        "OR достопримечательности OR традиции "
        "OR кухня when:2d"
    ),
]


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


SEVERE_CODES = {
    65,
    75,
    82,
    95,
    96,
    99,
}

WET_CODES = {
    51,
    53,
    55,
    61,
    63,
    65,
    80,
    81,
    82,
    95,
    96,
    99,
}

FOG_CODES = {
    45,
    48,
}


BAD_TOPICS = {
    "президент",
    "парламент",
    "депутат",
    "выбор",
    "правительств",
    "министр",
    "мид",
    "оппози",
    "политик",
    "санкци",
    "войн",
    "военн",
    "армия",
    "конфликт",
    "протест",
    "митинг",
    "посол",
    "дипломат",
    "суд",
    "задержан",
    "уголов",
    "криминал",
    "дтп",
    "авария",
    "погиб",
    "погибли",
    "ранен",
    "убийств",
    "пожар",
}


GOOD_TOPICS = {
    "туризм",
    "турист",
    "путеше",
    "экскурс",
    "фестиваль",
    "праздник",
    "культур",
    "театр",
    "музей",
    "выставк",
    "концерт",
    "гастроном",
    "кухн",
    "вин",
    "природ",
    "озеро",
    "водопад",
    "гора",
    "море",
    "пляж",
    "парк",
    "заповед",
    "эколог",
    "истори",
    "традиц",
    "археолог",
    "маршрут",
    "отдых",
    "гостеприим",
    "сезон",
    "мандари",
    "сад",
    "открыт",
    "реставрац",
}


FACTS = [
    (
        "Озеро Амткел образовалось после крупного "
        "горного обвала, перекрывшего русло реки Амткел."
    ),
    (
        "Новый Афон известен не только монастырём "
        "и пещерой, но и Анакопийской крепостью "
        "на Иверской горе."
    ),
    (
        "Акармара — бывший шахтёрский посёлок "
        "Восточной Абхазии, известный необычной "
        "архитектурой и горными пейзажами."
    ),
    (
        "В Абхазии на небольшой территории "
        "соседствуют морское побережье, субтропики "
        "и высокогорные ландшафты."
    ),
    (
        "Пицундская сосна — один из природных "
        "символов абхазского побережья."
    ),
    (
        "Юпшарский каньон по дороге к Рице "
        "часто называют «Каменным мешком» из-за "
        "почти отвесных скальных стен."
    ),
    (
        "Сухумский ботанический сад относится "
        "к числу старейших ботанических садов Кавказа."
    ),
    (
        "Озеро Мзы расположено высоко в горах, "
        "поэтому погода там может заметно "
        "отличаться от побережья."
    ),
    (
        "Новоафонская пещера — одна из крупнейших "
        "оборудованных для посещения пещер региона."
    ),
    (
        "После дождей многие водопады Абхазии "
        "становятся значительно полноводнее "
        "и выглядят особенно эффектно."
    ),
]


def now_local():
    return datetime.now(
        ZoneInfo(TZ)
    )


def get_json(
    base_url,
    params
):
    url = (
        base_url
        + "?"
        + urllib.parse.urlencode(
            params
        )
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "VAbkhazii/7.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        return json.loads(
            response.read().decode(
                "utf-8"
            )
        )


def get_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120 Safari/537.36"
                ),
            "Accept-Language":
                "ru-RU,ru;q=0.9,en;q=0.8",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        return (
            response.read()
            .decode(
                "utf-8",
                errors="replace"
            )
        )


def clean_text(text):
    text = html.unescape(
        re.sub(
            r"<[^>]+>",
            " ",
            text or ""
        )
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def weather_for(
    lat,
    lon
):
    data = get_json(
        WEATHER_URL,
        {
            "latitude":
                lat,
            "longitude":
                lon,
            "current":
                (
                    "temperature_2m,"
                    "weather_code,"
                    "cloud_cover,"
                    "wind_speed_10m"
                ),
            "daily":
                (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max,"
                    "precipitation_sum,"
                    "wind_speed_10m_max"
                ),
            "forecast_days":
                2,
            "timezone":
                TZ,
        }
    )

    current = data[
        "current"
    ]

    daily = data[
        "daily"
    ]

    days = []

    for index in range(2):
        days.append(
            {
                "date":
                    daily[
                        "time"
                    ][index],

                "code":
                    int(
                        daily[
                            "weather_code"
                        ][index]
                    ),

                "max":
                    round(
                        daily[
                            "temperature_2m_max"
                        ][index]
                    ),

                "min":
                    round(
                        daily[
                            "temperature_2m_min"
                        ][index]
                    ),

                "rain_prob":
                    int(
                        daily[
                            "precipitation_probability_max"
                        ][index]
                        or 0
                    ),

                "rain_sum":
                    float(
                        daily[
                            "precipitation_sum"
                        ][index]
                        or 0
                    ),

                "wind_max":
                    round(
                        daily[
                            "wind_speed_10m_max"
                        ][index]
                        or 0
                    ),
            }
        )

    return {
        "current": {
            "temp":
                round(
                    current[
                        "temperature_2m"
                    ]
                ),

            "code":
                int(
                    current[
                        "weather_code"
                    ]
                ),

            "cloud":
                int(
                    current[
                        "cloud_cover"
                    ]
                ),

            "wind":
                round(
                    current[
                        "wind_speed_10m"
                    ]
                ),
        },

        "days":
            days,
    }


def marine_now():
    lat, lon = SEA_POINT

    try:
        data = get_json(
            MARINE_URL,
            {
                "latitude":
                    lat,

                "longitude":
                    lon,

                "current":
                    (
                        "sea_surface_temperature,"
                        "wave_height"
                    ),

                "timezone":
                    TZ,
            }
        )

        current = data.get(
            "current",
            {}
        )

        return {
            "sea_temp":
                current.get(
                    "sea_surface_temperature"
                ),

            "wave":
                current.get(
                    "wave_height"
                ),
        }

    except Exception as exc:
        print(
            "Marine warning:",
            exc
        )

        return {
            "sea_temp":
                None,

            "wave":
                None,
        }


def route_status(
    name,
    day
):
    code = day[
        "code"
    ]

    rain = day[
        "rain_prob"
    ]

    wind = day[
        "wind_max"
    ]

    if name == "Мзы":
        if (
            code in SEVERE_CODES
            or rain >= 60
            or wind >= 40
        ):
            return (
                "🔴",
                (
                    "сегодня лучше выбрать "
                    "другой маршрут"
                ),
                3
            )

        if (
            code in WET_CODES
            or code in FOG_CODES
            or rain >= 30
            or wind >= 28
        ):
            return (
                "🟡",
                (
                    "высокогорье: возможны "
                    "быстро меняющиеся условия"
                ),
                2
            )

        return (
            "🟢",
            "хорошие условия по прогнозу",
            1
        )

    if name == "Рица":
        if (
            code in SEVERE_CODES
            or rain >= 75
            or wind >= 45
        ):
            return (
                "🔴",
                (
                    "лучше выбрать другой день "
                    "ради безопасности и видов"
                ),
                3
            )

        if (
            code in WET_CODES
            or code in FOG_CODES
            or rain >= 40
            or wind >= 32
        ):
            return (
                "🟡",
                (
                    "ехать можно, но панорамы "
                    "могут быть хуже"
                ),
                2
            )

        return (
            "🟢",
            (
                "хороший вариант "
                "для видов и фотографий"
            ),
            1
        )

    if name == "Восточная Абхазия":
        if (
            code in SEVERE_CODES
            or rain >= 80
            or wind >= 45
        ):
            return (
                "🔴",
                (
                    "сильная непогода — "
                    "лучше выбрать другой день"
                ),
                3
            )

        if (
            code in WET_CODES
            or rain >= 50
            or wind >= 35
        ):
            return (
                "🟡",
                "можно, но учитывайте осадки",
                2
            )

        return (
            "🟢",
            (
                "хороший день "
                "для Акармары и водопадов"
            ),
            1
        )

    if (
        code in SEVERE_CODES
        or rain >= 85
    ):
        return (
            "🔴",
            (
                "при сильной непогоде "
                "лучше перенести"
            ),
            3
        )

    if (
        code in WET_CODES
        or rain >= 55
        or wind >= 38
    ):
        return (
            "🟡",
            "подойдёт, но возможны осадки",
            2
        )

    return (
        "🟢",
        "комфортный вариант по прогнозу",
        1
    )


def choose_best(weather):
    candidates = [
        "Рица",
        "Новый Афон",
        "Восточная Абхазия",
        "Мзы",
    ]

    scored = []

    for name in candidates:
        day = (
            weather[
                name
            ][
                "days"
            ][0]
        )

        _, _, status_score = (
            route_status(
                name,
                day
            )
        )

        sensitivity = (
            1.25

            if name in {
                "Рица",
                "Мзы"
            }

            else 1.0
        )

        score = (
            status_score * 100

            + sensitivity
            * day[
                "rain_prob"
            ]

            + day[
                "rain_sum"
            ] * 8

            + max(
                0,
                day[
                    "wind_max"
                ] - 18
            ) * 2
        )

        scored.append(
            (
                score,
                name
            )
        )

    scored.sort()

    return scored[
        0
    ][
        1
    ]


def date_title(
    iso_date
):
    date = datetime.strptime(
        iso_date,
        "%Y-%m-%d"
    )

    return (
        f"{date.day} "
        f"{MONTHS[date.month]}"
    )


def fmt_num(value):
    if value is None:
        return None

    return (
        f"{float(value):.1f}"
    )


def sea_line(
    marine
):
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
            (
                f"вода около "
                f"<b>+{fmt_num(sea_temp)}°C</b>"
            )
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
            (
                f"{state}, около "
                f"<b>{fmt_num(wave)} м</b>"
            )
        )

    return (
        "🌊 Море: "
        + ", ".join(parts)
        + "."
    )


def load_state():
    try:
        return json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "used_news": [],
        }


def save_state(
    state
):
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def item_hash(text):
    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()[
        :16
    ]


def is_allowed_news(title):
    text = title.lower()

    if "абхаз" not in text:
        return False

    if any(
        bad in text
        for bad in BAD_TOPICS
    ):
        return False

    return any(
        good in text
        for good in GOOD_TOPICS
    )


def news_score(title):
    text = title.lower()

    score = 0

    for word in GOOD_TOPICS:
        if word in text:
            score += 3

    places = (
        "рица",
        "новый афон",
        "гагра",
        "пицунд",
        "сухум",
        "акармар",
        "мзы",
    )

    if any(
        place in text
        for place in places
    ):
        score += 4

    return score


def google_news_rss_url(
    query
):
    return (
        "https://news.google.com/"
        "rss/search?"
        + urllib.parse.urlencode(
            {
                "q":
                    query,

                "hl":
                    "ru",

                "gl":
                    "RU",

                "ceid":
                    "RU:ru",
            }
        )
    )


def collect_news_candidates(
    state
):
    cutoff = (
        now_local()
        - timedelta(
            hours=48
        )
    )

    result = []

    for query in NEWS_QUERIES:
        try:
            xml_text = get_text(
                google_news_rss_url(
                    query
                )
            )

            root = ET.fromstring(
                xml_text
            )

        except Exception as exc:
            print(
                "RSS warning:",
                exc
            )

            continue

        for item in root.findall(
            ".//item"
        ):
            title = clean_text(
                item.findtext(
                    "title"
                )
            )

            link = clean_text(
                item.findtext(
                    "link"
                )
            )

            pub_text = clean_text(
                item.findtext(
                    "pubDate"
                )
            )

            if (
                not title
                or not link
            ):
                continue

            if not is_allowed_news(
                title
            ):
                continue

            news_hash = item_hash(
                title
            )

            if news_hash in state.get(
                "used_news",
                []
            ):
                continue

            try:
                published = (
                    parsedate_to_datetime(
                        pub_text
                    )
                )

                if published.tzinfo is None:
                    published = (
                        published.replace(
                            tzinfo=ZoneInfo(
                                "UTC"
                            )
                        )
                    )

                published = (
                    published.astimezone(
                        ZoneInfo(TZ)
                    )
                )

            except Exception:
                continue

            if published < cutoff:
                continue

            result.append(
                {
                    "title":
                        title,

                    "url":
                        link,

                    "published":
                        published,

                    "hash":
                        news_hash,

                    "score":
                        news_score(
                            title
                        ),
                }
            )

    unique = {}

    for item in result:
        unique[
            item[
                "hash"
            ]
        ] = item

    result = list(
        unique.values()
    )

    result.sort(
        key=lambda item: (
            item[
                "score"
            ],

            item[
                "published"
            ]
        ),
        reverse=True
    )

    return result


def extract_meta(
    page,
    key,
    attr="property"
):
    patterns = [
        (
            rf'<meta[^>]+'
            rf'{attr}=["\']'
            rf'{re.escape(key)}'
            rf'["\'][^>]+'
            rf'content=["\']'
            rf'([^"\']+)'
            rf'["\']'
        ),

        (
            rf'<meta[^>]+'
            rf'content=["\']'
            rf'([^"\']+)'
            rf'["\'][^>]+'
            rf'{attr}=["\']'
            rf'{re.escape(key)}'
            rf'["\']'
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            page,
            re.I | re.S
        )

        if match:
            return clean_text(
                match.group(
                    1
                )
            )

    return None


def extract_article_paragraphs(
    page
):
    page = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        page,
        flags=re.I | re.S
    )

    page = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        page,
        flags=re.I | re.S
    )

    paragraphs = re.findall(
        r"<p\b[^>]*>(.*?)</p>",
        page,
        flags=re.I | re.S
    )

    result = []

    bad_fragments = (
        "cookie",
        "подписаться",
        "подписывайтесь",
        "реклама",
        "читайте также",
        "все права защищены",
        "политика конфиденциальности",
        "javascript",
        "скачайте приложение",
    )

    for paragraph in paragraphs:
        text = clean_text(
            paragraph
        )

        if len(text) < 70:
            continue

        if len(text) > 1500:
            continue

        lower = text.lower()

        if any(
            fragment in lower
            for fragment in bad_fragments
        ):
            continue

        if any(
            bad in lower
            for bad in BAD_TOPICS
        ):
            continue

        if text in result:
            continue

        result.append(
            text
        )

        if len(result) >= 12:
            break

    return result


def make_news_digest(
    title,
    paragraphs,
    description
):
    sentences = []

    if description:
        sentences.extend(
            re.split(
                r"(?<=[.!?])\s+",
                clean_text(
                    description
                )
            )
        )

    for paragraph in paragraphs:
        sentences.extend(
            re.split(
                r"(?<=[.!?])\s+",
                paragraph
            )
        )

    selected = []

    for sentence in sentences:
        sentence = clean_text(
            sentence
        )

        if len(sentence) < 45:
            continue

        if len(sentence) > 340:
            continue

        lower = sentence.lower()

        if any(
            bad in lower
            for bad in BAD_TOPICS
        ):
            continue

        if sentence in selected:
            continue

        selected.append(
            sentence
        )

        if len(selected) >= 5:
            break

    if len(selected) < 2:
        return None

    core = " ".join(
        selected
    )

    if len(core) > 750:
        core = (
            core[:747]
            .rsplit(
                " ",
                1
            )[0]
            + "…"
        )

    lower = (
        title
        + " "
        + core
    ).lower()

    if (
        "фестиваль" in lower
        or "концерт" in lower
        or "выстав" in lower
        or "праздник" in lower
    ):
        addition = (
            "Для отдыхающих это хороший повод "
            "добавить к экскурсионной программе "
            "ещё одно местное событие. "
            "Если мероприятие проходит в конкретную "
            "дату, программу лучше уточнить заранее."
        )

    elif (
        "кухн" in lower
        or "гастроном" in lower
        or "вин" in lower
    ):
        addition = (
            "Такие события особенно интересны тем, "
            "кто хочет познакомиться с Абхазией "
            "не только через природу, но и через "
            "местную кухню и традиции."
        )

    elif (
        "рица" in lower
        or "озеро" in lower
        or "водопад" in lower
        or "природ" in lower
        or "парк" in lower
    ):
        addition = (
            "Для путешественников это ещё одна идея "
            "для маршрута и возможность увидеть "
            "знакомые места с другой стороны."
        )

    else:
        addition = (
            "Для гостей Абхазии это ещё одна "
            "интересная деталь, которая помогает "
            "лучше познакомиться со страной "
            "за пределами классических маршрутов."
        )

    result = (
        core
        + "\n\n"
        + addition
    )

    if len(result) > 1200:
        result = (
            result[:1197]
            .rsplit(
                " ",
                1
            )[0]
            + "…"
        )

    return result


def article_summary(
    title,
    url
):
    try:
        page = get_text(
            url
        )

        description = (
            extract_meta(
                page,
                "og:description"
            )

            or

            extract_meta(
                page,
                "description",
                attr="name"
            )
        )

        paragraphs = (
            extract_article_paragraphs(
                page
            )
        )

        return make_news_digest(
            title,
            paragraphs,
            description
        )

    except Exception as exc:
        print(
            "Article warning:",
            exc
        )

        return None


def fact_of_day():
    today = now_local().date()

    index = (
        today.toordinal()
        % len(FACTS)
    )

    return FACTS[
        index
    ]


def interesting_block(
    state
):
    candidates = (
        collect_news_candidates(
            state
        )
    )

    for news in candidates[:8]:
        state.setdefault(
            "used_news",
            []
        ).append(
            news[
                "hash"
            ]
        )

        state[
            "used_news"
        ] = (
            state[
                "used_news"
            ][-50:]
        )

        summary = article_summary(
            news[
                "title"
            ],

            news[
                "url"
            ]
        )

        if not summary:
            continue

        return (
            "📰 <b>ЧТО ИНТЕРЕСНОГО "
            "В АБХАЗИИ</b>\n\n"

            f"<b>"
            f"{html.escape(news['title'])}"
            f"</b>\n\n"

            f"{html.escape(summary)}"
        )

    return (
        "📍 <b>ФАКТ ДНЯ</b>\n\n"
        + html.escape(
            fact_of_day()
        )
    )


def build_morning_post(
    weather,
    marine,
    state
):
    coast = weather[
        "Гагра"
    ]

    today = (
        coast[
            "days"
        ][0]
    )

    current = coast[
        "current"
    ]

    best = choose_best(
        weather
    )

    weather_desc = (
        WEATHER_TEXT.get(
            today[
                "code"
            ],
            "переменная погода"
        )
    )

    lines = [
        (
            f"🇦🇧 <b>АБХАЗИЯ СЕГОДНЯ | "
            f"{date_title(today['date'])}</b>"
        ),

        "",

        (
            f"🌤 Побережье: "
            f"<b>{weather_desc}</b>. "
            f"Сейчас около "
            f"<b>+{current['temp']}°C</b>, "
            f"днём до "
            f"<b>+{today['max']}°C</b>."
        ),

        (
            f"🌧 Осадки: вероятность до "
            f"<b>{today['rain_prob']}%</b>. "
            f"Ветер до "
            f"<b>{today['wind_max']} км/ч</b>."
        ),
    ]

    sea = sea_line(
        marine
    )

    if sea:
        lines.append(
            sea
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
        day = (
            weather[
                name
            ][
                "days"
            ][0]
        )

        emoji, note, _ = (
            route_status(
                name,
                day
            )
        )

        lines.append(
            (
                f"{emoji} "
                f"<b>{name}</b> — "
                f"{note}. "
                f"Днём около "
                f"+{day['max']}°C, "
                f"осадки до "
                f"{day['rain_prob']}%."
            )
        )

    lines += [
        "",

        (
            f"🔥 <b>МОЙ ВЫБОР НА СЕГОДНЯ: "
            f"{best.upper()}</b>"
        ),

        (
            "По прогнозу это один "
            "из наиболее удачных "
            "вариантов на день."
        ),

        "",

        interesting_block(
            state
        ),

        "",

        (
            "⚠️ В горах погода переменчива, "
            "поэтому перед выездом всегда "
            "учитывайте текущую обстановку "
            "на маршруте."
        ),

        "",

        (
            "📍 <b>Уже отдыхаете "
            "в Абхазии?</b>"
        ),

        (
            "Напишите "
            "<b>город + сколько вас человек</b> "
            "— подскажу маршрут "
            "на сегодня или завтра."
        ),

        "",

        "👉 @VAbkhazii",
    ]

    return "\n".join(
        lines
    )


def send_telegram(
    text
):
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set"
        )

    url = TG_URL.format(
        token=BOT_TOKEN
    )

    payload = urllib.parse.urlencode(
        {
            "chat_id":
                CHANNEL,

            "text":
                text,

            "parse_mode":
                "HTML",

            "disable_web_page_preview":
                "true",
        }
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    if not result.get(
        "ok"
    ):
        raise RuntimeError(
            f"Telegram error: {result}"
        )


def main():
    state = load_state()

    weather = {
        name:
            weather_for(
                *coords
            )

        for name, coords
        in PLACES.items()
    }

    post = build_morning_post(
        weather,
        marine_now(),
        state
    )

    print(
        post
    )

    send_telegram(
        post
    )

    save_state(
        state
    )


if __name__ == "__main__":
    main()
