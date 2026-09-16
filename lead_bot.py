import asyncio
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession


# =========================================================
# SETTINGS
# =========================================================

TG_API_ID = int(os.environ["TG_API_ID"])
TG_API_HASH = os.environ["TG_API_HASH"]
TG_SESSION = os.environ["TG_SESSION"]

LEADS_BOT_TOKEN = os.environ["LEADS_BOT_TOKEN"]
LEADS_CHAT_ID = os.environ["LEADS_CHAT_ID"]

STATE_DIR = Path(".lead_state")
STATE_FILE = STATE_DIR / "state.json"

MAX_AGE_HOURS = 48
SEARCH_LIMIT = 60
MAX_LEADS_PER_RUN = 12


SEARCH_QUERIES = [
    "Абхазия экскурсия",
    "Абхазия гид",
    "нужен гид Абхазия",
    "экскурсии Абхазия",
    "Рица экскурсия",
    "Новый Афон экскурсия",
    "что посмотреть Абхазия",
    "куда поехать Абхазия",
    "едем в Абхазию",
    "отдыхаем в Абхазии",
    "кто возит на Рицу",
    "водитель Абхазия экскурсия",
    "индивидуальная экскурсия Абхазия",
    "Гагра экскурсия",
    "Пицунда экскурсия",
    "Сухум экскурсия",
    "Новый Афон гид",
]


HOT_PHRASES = [
    "нужен гид",
    "ищем гида",
    "посоветуйте гида",
    "посоветуйте экскурсию",
    "кто возит",
    "кто может отвезти",
    "хотим экскурсию",
    "хочу экскурсию",
    "где заказать экскурсию",
    "кто организует",
    "ищем экскурсию",
    "нужна экскурсия",
    "нужен водитель",
    "кто свозит",
    "кто может свозить",
    "хотим на рицу",
    "хочу на рицу",
    "хотим в новый афон",
]


WARM_PHRASES = [
    "куда поехать",
    "куда съездить",
    "что посмотреть",
    "что посетить",
    "куда сходить",
    "что посоветуете",
    "что рекомендуете",
    "едем в абхазию",
    "приезжаем в абхазию",
    "будем в абхазии",
    "отдыхаем в абхазии",
    "мы в гагре",
    "мы в пицунде",
    "мы в сухуме",
    "мы в новом афоне",
]


URGENT_PHRASES = [
    "сегодня",
    "завтра",
    "послезавтра",
    "сейчас",
    "уже в",
    "приехали",
    "находимся",
]


SELLER_PHRASES = [
    "провожу экскурсии",
    "организуем экскурсии",
    "предлагаем экскурсии",
    "наши экскурсии",
    "стоимость экскурсии",
    "запись на экскурсию",
    "бронируйте",
    "свободные места",
    "набор группы",
    "экскурсии каждый день",
    "гид по абхазии",
    "ваш гид",
    "туроператор",
    "турагентство",
    "турфирма",
    "экскурсионное бюро",
    "скидка на экскурсию",
]


ROUTES = {
    "Рица": [
        "рица",
        "озеро рица",
        "малая рица",
    ],

    "Новый Афон": [
        "новый афон",
        "новоафон",
        "пещера",
        "монастырь",
        "анакоп",
    ],

    "Восточная Абхазия": [
        "акармара",
        "ткуарчал",
        "водопад",
        "шакуран",
        "черниговка",
        "амткел",
    ],

    "Мзы": [
        "мзы",
        "озеро мзы",
    ],

    "Святыни": [
        "каманы",
        "дранда",
        "илор",
        "святыни",
        "храм",
        "монастыр",
    ],
}


CITIES = {
    "Гагра": [
        "гагра",
        "гагре",
        "гагры",
    ],

    "Пицунда": [
        "пицунда",
        "пицунде",
        "пицунды",
    ],

    "Сухум": [
        "сухум",
        "сухуме",
        "сухума",
    ],

    "Новый Афон": [
        "новый афон",
        "новом афоне",
    ],

    "Гудаута": [
        "гудаута",
        "гудауте",
    ],

    "Цандрыпш": [
        "цандрыпш",
        "гантиади",
    ],
}


# =========================================================
# STATE
# =========================================================

def load_state():
    try:
        return json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {
            "seen": [],
        }


def save_state(state):
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    state["seen"] = state.get(
        "seen",
        []
    )[-1500:]

    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# =========================================================
# TELEGRAM BOT API
# =========================================================

def bot_api(method, data):
    url = (
        f"https://api.telegram.org/"
        f"bot{LEADS_BOT_TOKEN}/{method}"
    )

    payload = urllib.parse.urlencode(
        data
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "User-Agent":
                "VAbkhaziiLeads/2.0"
        }
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

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram Bot API error: {result}"
        )

    return result


def send_private_message(text):
    bot_api(
        "sendMessage",
        {
            "chat_id":
                LEADS_CHAT_ID,

            "text":
                text,

            "parse_mode":
                "HTML",

            "disable_web_page_preview":
                "true",
        }
    )


# =========================================================
# TEXT ANALYSIS
# =========================================================

def normalize(text):
    return re.sub(
        r"\s+",
        " ",
        text or ""
    ).strip()


def contains_any(text, phrases):
    lower = text.lower()

    return any(
        phrase in lower
        for phrase in phrases
    )


def looks_like_seller(text):
    lower = text.lower()

    if contains_any(
        lower,
        SELLER_PHRASES
    ):
        return True

    commercial_markers = [
        "₽",
        "руб",
        "цена",
        "стоимость",
        "запись",
        "бронь",
        "места",
        "телефон",
        "whatsapp",
        "ватсап",
    ]

    count = sum(
        1
        for marker in commercial_markers
        if marker in lower
    )

    return count >= 3


def detect_city(text):
    lower = text.lower()

    for city, variants in CITIES.items():
        if any(
            variant in lower
            for variant in variants
        ):
            return city

    return None


def detect_route(text):
    lower = text.lower()

    for route, variants in ROUTES.items():
        if any(
            variant in lower
            for variant in variants
        ):
            return route

    return None


def detect_people(text):
    patterns = [
        r"\bнас\s+(\d{1,2})\b",
        r"\b(\d{1,2})\s*человек\b",
        r"\b(\d{1,2})\s*чел\b",
        r"\b(\d{1,2})\s*взросл",
        r"\bсемья\s+из\s+(\d{1,2})\b",
        r"\bкомпания\s+из\s+(\d{1,2})\b",
    ]

    lower = text.lower()

    for pattern in patterns:
        match = re.search(
            pattern,
            lower
        )

        if match:
            try:
                people = int(
                    match.group(1)
                )

                if 1 <= people <= 50:
                    return people

            except Exception:
                pass

    return None


def detect_urgency(text):
    lower = text.lower()

    for phrase in URGENT_PHRASES:
        if phrase in lower:
            return phrase

    return None


def classify_lead(text):
    lower = text.lower()

    if looks_like_seller(
        lower
    ):
        return None

    score = 0
    reasons = []

    hot_hits = [
        phrase
        for phrase in HOT_PHRASES
        if phrase in lower
    ]

    warm_hits = [
        phrase
        for phrase in WARM_PHRASES
        if phrase in lower
    ]

    urgent_hits = [
        phrase
        for phrase in URGENT_PHRASES
        if phrase in lower
    ]

    if hot_hits:
        score += 60
        reasons.append(
            "явно ищет экскурсию/гида"
        )

    if warm_hits:
        score += 30
        reasons.append(
            "спрашивает, куда поехать"
        )

    if urgent_hits:
        score += 20
        reasons.append(
            "есть срочность"
        )

    if "абхаз" in lower:
        score += 10

    if detect_route(
        lower
    ):
        score += 10

    if detect_city(
        lower
    ):
        score += 8

    if detect_people(
        lower
    ):
        score += 8

    if "?" in text:
        score += 5

    if score >= 65:
        level = "🔥 ГОРЯЧИЙ"

    elif score >= 35:
        level = "🟡 ТЁПЛЫЙ"

    elif score >= 20:
        level = "⚪ СЛАБЫЙ"

    else:
        return None

    return {
        "score":
            score,

        "level":
            level,

        "reasons":
            reasons,
    }


# =========================================================
# RESPONSE SUGGESTION
# =========================================================

def make_reply(
    city,
    route,
    people,
    urgency
):
    parts = [
        "Добрый день!"
    ]

    if route:
        parts.append(
            f"Могу организовать поездку "
            f"по маршруту «{route}»."
        )

    else:
        parts.append(
            "Могу помочь подобрать экскурсию "
            "по Абхазии под ваши пожелания."
        )

    if city:
        parts.append(
            f"Можно организовать выезд "
            f"из {city}."
        )

    if people:
        parts.append(
            f"Для компании из {people} чел. "
            "подберём удобный формат."
        )

    if urgency:
        parts.append(
            "Если поездка нужна в ближайшее время, "
            "могу сразу проверить варианты."
        )

    parts.append(
        "Напишите, пожалуйста, дату поездки "
        "и сколько будет взрослых и детей."
    )

    return " ".join(
        parts
    )


# =========================================================
# LINK
# =========================================================

def build_message_link(
    entity,
    message_id
):
    username = getattr(
        entity,
        "username",
        None
    )

    if not username:
        return None

    return (
        f"https://t.me/"
        f"{username}/"
        f"{message_id}"
    )


# =========================================================
# CARD
# =========================================================

def make_card(
    text,
    entity,
    message_id,
    date,
    classification
):
    city = detect_city(
        text
    )

    route = detect_route(
        text
    )

    people = detect_people(
        text
    )

    urgency = detect_urgency(
        text
    )

    title = (
        getattr(
            entity,
            "title",
            None
        )
        or
        getattr(
            entity,
            "first_name",
            None
        )
        or
        "Telegram"
    )

    link = build_message_link(
        entity,
        message_id
    )

    reply = make_reply(
        city,
        route,
        people,
        urgency
    )

    safe_text = html.escape(
        text[:900]
    )

    lines = [
        (
            f"{classification['level']} "
            f"<b>ЛИД</b>"
        ),

        "",

        (
            f"⭐ Оценка: "
            f"<b>{classification['score']}</b>"
        ),

        (
            f"📡 Источник: "
            f"<b>{html.escape(str(title))}</b>"
        ),
    ]

    if city:
        lines.append(
            f"📍 Город: <b>{city}</b>"
        )

    if people:
        lines.append(
            f"👥 Людей: <b>{people}</b>"
        )

    if route:
        lines.append(
            f"🏞 Интерес: <b>{route}</b>"
        )

    if urgency:
        lines.append(
            f"⏰ Срочность: "
            f"<b>{html.escape(urgency)}</b>"
        )

    lines += [
        "",
        "💬 <b>Сообщение:</b>",
        safe_text,
        "",
        "🎯 <b>Что можно предложить:</b>",
        (
            route
            if route
            else
            "подбор индивидуального маршрута"
        ),
        "",
        "✍️ <b>Готовый ответ:</b>",
        html.escape(
            reply
        ),
    ]

    if link:
        lines += [
            "",
            (
                f'🔗 <a href="{html.escape(link)}">'
                f'Открыть исходное сообщение'
                f'</a>'
            ),
        ]

    lines += [
        "",
        (
            "🕒 "
            + date.strftime(
                "%d.%m.%Y %H:%M UTC"
            )
        ),
    ]

    return "\n".join(
        lines
    )


# =========================================================
# SEARCH
# =========================================================

async def search_public_messages(
    client,
    state
):
    cutoff = datetime.now(
        timezone.utc
    ) - timedelta(
        hours=MAX_AGE_HOURS
    )

    candidates = {}

    for query in SEARCH_QUERIES:
        print(
            f"Searching: {query}"
        )

        try:
            async for message in client.iter_messages(
                None,
                search=query,
                limit=SEARCH_LIMIT
            ):
                if not message:
                    continue

                text = normalize(
                    getattr(
                        message,
                        "message",
                        ""
                    )
                )

                if not text:
                    continue

                if not message.date:
                    continue

                date = message.date

                if date.tzinfo is None:
                    date = date.replace(
                        tzinfo=timezone.utc
                    )

                if date < cutoff:
                    continue

                chat = await message.get_chat()

                if not chat:
                    continue

                username = getattr(
                    chat,
                    "username",
                    None
                )

                # Only public Telegram sources.
                if not username:
                    continue

                unique_id = (
                    f"{getattr(chat, 'id', '')}:"
                    f"{message.id}"
                )

                if unique_id in state.get(
                    "seen",
                    []
                ):
                    continue

                classification = classify_lead(
                    text
                )

                if not classification:
                    continue

                current = candidates.get(
                    unique_id
                )

                item = {
                    "id":
                        unique_id,

                    "message_id":
                        message.id,

                    "text":
                        text,

                    "date":
                        date,

                    "chat":
                        chat,

                    "classification":
                        classification,
                }

                if (
                    current is None
                    or
                    classification["score"]
                    >
                    current[
                        "classification"
                    ][
                        "score"
                    ]
                ):
                    candidates[
                        unique_id
                    ] = item

        except Exception as exc:
            print(
                f"Search warning [{query}]: "
                f"{exc}"
            )

    result = list(
        candidates.values()
    )

    result.sort(
        key=lambda item: (
            item[
                "classification"
            ][
                "score"
            ],
            item[
                "date"
            ]
        ),
        reverse=True
    )

    return result[
        :MAX_LEADS_PER_RUN
    ]


# =========================================================
# MAIN
# =========================================================

async def async_main():
    state = load_state()

    client = TelegramClient(
        StringSession(
            TG_SESSION
        ),
        TG_API_ID,
        TG_API_HASH,
    )

    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError(
            "TG_SESSION is not authorized"
        )

    me = await client.get_me()

    print(
        "Connected as:",
        getattr(
            me,
            "first_name",
            ""
        )
    )

    leads = await search_public_messages(
        client,
        state
    )

    print(
        f"Found {len(leads)} lead(s)"
    )

    if not leads:
        print(
            "No new leads found."
        )

        await client.disconnect()
        save_state(
            state
        )
        return

    sent = 0

    for lead in leads:
        try:
            card = make_card(
                lead[
                    "text"
                ],
                lead[
                    "chat"
                ],
                lead[
                    "message_id"
                ],
                lead[
                    "date"
                ],
                lead[
                    "classification"
                ],
            )

            send_private_message(
                card
            )

            state.setdefault(
                "seen",
                []
            ).append(
                lead[
                    "id"
                ]
            )

            sent += 1

        except Exception as exc:
            print(
                "Send warning:",
                exc
            )

    save_state(
        state
    )

    await client.disconnect()

    print(
        f"Sent {sent} lead(s)"
    )


def main():
    try:
        asyncio.run(
            async_main()
        )

    except Exception as exc:
        print(
            "ERROR:",
            str(exc)
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
