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

FORCE_MODE = os.getenv(
    "POST_MODE",
    "auto"
).lower()


STATE_DIR = Path(".bot_state")
STATE_FILE = STATE_DIR / "state.json"


PLACES = {

    "Гагра": (
        43.2783,
        40.2712
    ),

    "Рица": (
        43.4840,
        40.5430
    ),

    "Новый Афон": (
        43.0877,
        40.8136
    ),

    "Восточная Абхазия": (
        42.8528,
        41.6805
    ),

    "Мзы": (
        43.4160,
        40.5680
    ),
}


SEA_POINT = (
    43.2600,
    40.2400
)


WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

MARINE_URL = (
    "https://marine-api.open-meteo.com/v1/marine"
)

TG_URL = (
    "https://api.telegram.org/"
    "bot{token}/sendMessage"
)


NEWS_QUERIES = [

    (
        "Абхазия туризм OR фестиваль "
        "OR культура OR природа "
        "OR гастрономия OR музей "
        "OR выставка OR концерт when:2d"
    ),

    (
        "Абхазия Рица OR Новый Афон "
        "OR Гагра OR Пицунда OR Сухум "
        "OR Акармара OR Мзы when:2d"
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


# Эти темы в канал автоматически
# не допускаются.
POLITICS = {

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

    "переговор",
    "посол",
    "дипломат",

    "суд",
    "задержан",
    "уголов",
    "криминал",

    "дтп",
    "погиб",
    "ранен",
}


# Интересующие нас темы.
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


EVENT_WORDS = {

    "фестиваль",
    "концерт",
    "выставк",
    "ярмарк",

    "праздник",
    "турнир",
    "форум",

    "мероприят",
    "открытие",
}


FACTS = [

    (
        "Озеро Амткел образовалось "
        "после крупного горного обвала, "
        "перекрывшего русло реки Амткел."
    ),

    (
        "Новый Афон известен не только "
        "монастырём и пещерой, но и "
        "Анакопийской крепостью "
        "на Иверской горе."
    ),

    (
        "Акармара — бывший шахтёрский "
        "посёлок в восточной части "
        "Абхазии, известный необычной "
        "архитектурой и горными пейзажами."
    ),

    (
        "В Абхазии на небольшой территории "
        "соседствуют морское побережье, "
        "субтропики и высокогорные "
        "ландшафты."
    ),

    (
        "Пицундская сосна — один из "
        "символов побережья Абхазии. "
        "Её реликтовые рощи особенно "
        "известны в районе Пицунды."
    ),

    (
        "Юпшарский каньон по дороге "
        "к Рице часто называют "
        "«Каменным мешком» из-за "
        "почти отвесных скальных стен."
    ),

    (
        "Сухумский ботанический сад — "
        "один из старейших ботанических "
        "садов Кавказа."
    ),

    (
        "Высокогорное озеро Мзы лежит "
        "значительно выше курортного "
        "побережья, поэтому погода там "
        "может сильно отличаться от Гагры."
    ),

    (
        "Новоафонская пещера — одна "
        "из крупнейших оборудованных "
        "для посещения пещер региона."
    ),
]


PLACE_CARDS = [

    (
        "Псырцха",

        (
            "Станция Псырцха в Новом Афоне "
            "стоит прямо среди зелени и воды. "
            "Сюда стоит зайти не только ради "
            "фотографии: место удобно совместить "
            "с прогулкой по Новому Афону."
        )
    ),

    (
        "Акармара",

        (
            "Акармара — необычное место "
            "Восточной Абхазии с атмосферной "
            "архитектурой, горами и дорогой "
            "к водопадам. Хороший вариант "
            "для тех, кто уже видел "
            "классические маршруты."
        )
    ),

    (
        "Шакуранский водопад",

        (
            "Шакуранский водопад находится "
            "в живописном ущелье. Особенно "
            "эффектно место выглядит после "
            "дождей, когда поток становится "
            "мощнее."
        )
    ),

    (
        "Озеро Мзы",

        (
            "Мзы — высокогорное озеро "
            "с совсем другим климатом, "
            "чем на побережье. Для поездки "
            "нужна удобная обувь и готовность "
            "к быстрой смене погоды."
        )
    ),
]


TIPS = [

    (
        "В горы лучше брать лёгкую ветровку "
        "даже в тёплый день: температура "
        "на высоте заметно ниже, чем "
        "на побережье."
    ),

    (
        "На Рицу и другие популярные "
        "маршруты удобнее выезжать раньше — "
        "так меньше людей и больше времени "
        "остаётся на остановки."
    ),

    (
        "Для Мзы и других пеших горных "
        "маршрутов лучше выбирать обувь "
        "с хорошим сцеплением."
    ),

    (
        "После дождей водопады часто "
        "выглядят эффектнее, но тропы "
        "могут быть скользкими — "
        "это стоит учитывать."
    ),
]


FOOD = [

    (
        "Попробуйте ачапу — традиционную "
        "закуску из овощей, зелени, "
        "орехов и специй."
    ),

    (
        "Если любите местную кухню, "
        "обратите внимание на абысту "
        "и блюда с домашним сыром."
    ),

    (
        "В сезон стоит искать местные "
        "фрукты и цитрусовые — вкус у них "
        "часто заметно отличается "
        "от магазинных."
    ),
]


def now_local():

    return datetime.now(
        ZoneInfo(
            TZ
        )
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
                "VAbkhaziiBot/4.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=25
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
                    "(compatible; "
                    "VAbkhaziiBot/4.0)"
                ),

            "Accept-Language":
                "ru-RU,ru;q=0.9,en;q=0.8",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=25
    ) as response:

        return (
            response.read()
            .decode(
                "utf-8",
                errors="replace"
            )
        )


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
                    ][
                        index
                    ],

                "code":
                    int(
                        daily[
                            "weather_code"
                        ][
                            index
                        ]
                    ),

                "max":
                    round(
                        daily[
                            "temperature_2m_max"
                        ][
                            index
                        ]
                    ),

                "min":
                    round(
                        daily[
                            "temperature_2m_min"
                        ][
                            index
                        ]
                    ),

                "rain_prob":
                    int(
                        daily[
                            "precipitation_probability_max"
                        ][
                            index
                        ]
                        or 0
                    ),

                "rain_sum":
                    float(
                        daily[
                            "precipitation_sum"
                        ][
                            index
                        ]
                        or 0
                    ),

                "wind_max":
                    round(
                        daily[
                            "wind_speed_10m_max"
                        ][
                            index
                        ]
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
            "Marine API warning:",
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
                    "лучше перенести ради "
                    "безопасности и видов"
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
                "хороший вариант для "
                "видов и фотографий"
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
                (
                    "можно, но учитывайте "
                    "осадки"
                ),
                2
            )


        return (
            "🟢",
            (
                "хороший день для "
                "Акармары и водопадов"
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
            (
                "подойдёт, но возможны "
                "осадки"
            ),
            2
        )


    return (
        "🟢",
        "комфортный вариант по прогнозу",
        1
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

        day = (
            weather[
                name
            ][
                "days"
            ][
                day_index
            ]
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


def fmt_num(value):

    if value is None:

        return None


    return (
        f"{float(value):.1f}"
    )


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

            f"вода около "
            f"<b>+{fmt_num(sea_temp)}°C</b>"
        )


    if wave is not None:

        if wave < 0.4:

            state = (
                "море спокойное"
            )

        elif wave < 0.8:

            state = (
                "небольшая волна"
            )

        elif wave < 1.4:

            state = (
                "заметная волна"
            )

        else:

            state = (
                "море волнуется"
            )


        parts.append(

            f"{state}, около "
            f"<b>{fmt_num(wave)} м</b>"
        )


    return (
        "🌊 Море: "
        + ", ".join(
            parts
        )
        + "."
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


def is_allowed_news(
    title
):

    text = title.lower()


    if "абхаз" not in text:

        return False


    if any(

        word in text

        for word
        in POLITICS

    ):

        return False


    return any(

        word in text

        for word
        in GOOD_TOPICS
    )


def news_score(
    title
):

    text = title.lower()


    score = sum(

        3

        for word
        in GOOD_TOPICS

        if word in text
    )


    score += sum(

        2

        for word
        in EVENT_WORDS

        if word in text
    )


    if any(

        place in text

        for place in (

            "рица",
            "новый афон",
            "гагра",
            "пицунд",
            "сухум",
            "акармар",
            "мзы",
        )

    ):

        score += 4


    return score


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
            "recent_blocks": [],
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


def item_hash(
    text
):

    return hashlib.sha256(

        text.encode(
            "utf-8"
        )

    ).hexdigest()[
        :16
    ]


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


def find_fresh_news(
    state
):

    cutoff = (
        now_local()
        - timedelta(
            hours=48
        )
    )


    candidates = []


    for query in NEWS_QUERIES:

        try:

            root = ET.fromstring(

                get_text(

                    google_news_rss_url(
                        query
                    )
                )
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


            published_text = clean_text(

                item.findtext(
                    "pubDate"
                )
            )


            if (
                not title
                or not link
                or not is_allowed_news(
                    title
                )
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
                        published_text
                    )
                )


                if (
                    published.tzinfo
                    is None
                ):

                    published = (
                        published.replace(
                            tzinfo=ZoneInfo(
                                "UTC"
                            )
                        )
                    )


                published = (
                    published.astimezone(
                        ZoneInfo(
                            TZ
                        )
                    )
                )


            except Exception:

                continue


            if published < cutoff:

                continue


            candidates.append(
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


    if not candidates:

        return None


    candidates.sort(

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


    return candidates[
        0
    ]


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


def trim_summary(
    text
):

    text = clean_text(
        text
    )


    sentences = re.split(

        r"(?<=[.!?])\s+",

        text
    )


    chosen = []

    total = 0


    for sentence in sentences:

        sentence = sentence.strip()


        if len(
            sentence
        ) < 25:

            continue


        if (
            total
            + len(
                sentence
            )
            > 520
        ):

            break


        chosen.append(
            sentence
        )


        total += (
            len(
                sentence
            )
            + 1
        )


        if len(
            chosen
        ) >= 3:

            break


    if chosen:

        result = " ".join(
            chosen
        )

    else:

        result = text[
            :500
        ].strip()


    if len(
        result
    ) > 520:

        result = (
            result[
                :517
            ].rstrip()
            + "…"
        )


    return result


def article_summary(
    url,
    fallback_title
):

    try:

        page = get_text(
            url
        )


        summary = (

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


        if (
            summary
            and len(
                summary
            ) >= 80
        ):

            return trim_summary(
                summary
            )


        paragraphs = re.findall(

            r"<p\b[^>]*>(.*?)</p>",

            page,

            re.I | re.S
        )


        clean_paragraphs = []


        for paragraph in paragraphs:

            text = clean_text(
                paragraph
            )


            if (
                70
                <= len(
                    text
                )
                <= 700
            ):

                lower = text.lower()


                if not any(

                    bad in lower

                    for bad in (

                        "cookie",
                        "подпис",
                        "реклам",
                        "javascript",
                    )

                ):

                    clean_paragraphs.append(
                        text
                    )


            if len(
                clean_paragraphs
            ) >= 3:

                break


        if clean_paragraphs:

            return trim_summary(

                " ".join(
                    clean_paragraphs
                )
            )


    except Exception as exc:

        print(
            "Article warning:",
            exc
        )


    return trim_summary(
        fallback_title
    )


def fallback_block(
    state
):

    today = (
        now_local()
        .date()
    )


    options = [

        (
            "fact",
            "📍 <b>ФАКТ ДНЯ</b>",
            FACTS
        ),

        (
            "place",
            "🏞 <b>МЕСТО ДНЯ</b>",
            PLACE_CARDS
        ),

        (
            "tip",
            "💡 <b>СОВЕТ ТУРИСТУ</b>",
            TIPS
        ),

        (
            "food",
            "🍽 <b>ЧТО ПОПРОБОВАТЬ</b>",
            FOOD
        ),
    ]


    recent = state.get(
        "recent_blocks",
        []
    )


    allowed = [

        option

        for option
        in options

        if option[
            0
        ] not in recent[
            -2:
        ]
    ]


    if not allowed:

        allowed = options


    block_type, heading, pool = (

        allowed[

            today.toordinal()
            % len(
                allowed
            )
        ]
    )


    index = (

        today.toordinal()
        % len(
            pool
        )
    )


    item = pool[
        index
    ]


    state.setdefault(
        "recent_blocks",
        []
    ).append(
        block_type
    )


    state[
        "recent_blocks"
    ] = state[
        "recent_blocks"
    ][
        -10:
    ]


    if block_type == "place":

        name, text = item


        return (

            f"{heading}\n"
            f"<b>{html.escape(name)}</b>\n"
            f"{html.escape(text)}"
        )


    return (

        f"{heading}\n"

        + html.escape(
            item
        )
    )


def interesting_block(
    state
):

    news = find_fresh_news(
        state
    )


    if news:

        summary = article_summary(

            news[
                "url"
            ],

            news[
                "title"
            ]
        )


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
        ] = state[
            "used_news"
        ][
            -30:
        ]


        state.setdefault(

            "recent_blocks",
            []

        ).append(
            "news"
        )


        state[
            "recent_blocks"
        ] = state[
            "recent_blocks"
        ][
            -10:
        ]


        if any(

            word
            in news[
                "title"
            ].lower()

            for word
            in EVENT_WORDS

        ):

            heading = (
                "🎉 <b>СОБЫТИЕ / "
                "НОВОСТЬ ДНЯ</b>"
            )

        else:

            heading = (
                "📰 <b>ЧТО ИНТЕРЕСНОГО "
                "В АБХАЗИИ</b>"
            )


        return (

            f"{heading}\n"

            f"<b>"
            f"{html.escape(news['title'])}"
            f"</b>\n"

            f"{html.escape(summary)}"
        )


    return fallback_block(
        state
    )


def build_morning_post(
    weather,
    marine,
    state
):

    coast = weather[
        "Гагра"
    ]


    today = coast[
        "days"
    ][
        0
    ]


    current = coast[
        "current"
    ]


    best = choose_best(
        weather,
        0
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
            ][
                0
            ]
        )


        emoji, note, _ = (
            route_status(
                name,
                day
            )
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


def build_evening_post(
    weather
):

    coast = weather[
        "Гагра"
    ]


    tomorrow = coast[
        "days"
    ][
        1
    ]


    best = choose_best(
        weather,
        1
    )


    weather_desc = (

        WEATHER_TEXT.get(

            tomorrow[
                "code"
            ],

            "переменная погода"
        )
    )


    lines = [

        (
            f"🚙 <b>КУДА ЕДЕМ ЗАВТРА | "
            f"{date_title(tomorrow['date'])}</b>"
        ),

        "",

        (
            f"🌤 На побережье ожидается "
            f"<b>{weather_desc}</b>."
        ),

        (
            f"🌡 Температура примерно "
            f"<b>+{tomorrow['min']}…"
            f"+{tomorrow['max']}°C</b>."
        ),

        (
            f"🌧 Вероятность осадков — "
            f"до <b>{tomorrow['rain_prob']}%</b>."
        ),

        (
            f"💨 Ветер до "
            f"<b>{tomorrow['wind_max']} км/ч</b>."
        ),

        "",

        "<b>Что выбрать на завтра:</b>",
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
            ][
                1
            ]
        )


        emoji, note, _ = (
            route_status(
                name,
                day
            )
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

        (
            f"🔥 <b>МОЯ РЕКОМЕНДАЦИЯ "
            f"НА ЗАВТРА: "
            f"{best.upper()}</b>"
        ),

        "",

        (
            "Свободные места и детали "
            "ближайших поездок уточняйте "
            "перед записью."
        ),

        "",

        (
            "📩 Хотите подобрать поездку? "
            "Напишите "
            "<b>где вы отдыхаете + "
            "сколько вас человек</b>."
        ),

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
        timeout=25
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

            f"Telegram error: "
            f"{result}"
        )


def choose_mode():

    if FORCE_MODE in {
        "morning",
        "evening"
    }:

        return FORCE_MODE


    if now_local().hour >= 15:

        return "evening"


    return "morning"


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


    mode = choose_mode()


    if mode == "evening":

        post = build_evening_post(
            weather
        )

    else:

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
