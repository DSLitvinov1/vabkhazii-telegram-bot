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
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import User


# =========================================================
# CONFIG
# =========================================================

TG_API_ID = int(os.environ["TG_API_ID"])
TG_API_HASH = os.environ["TG_API_HASH"]
TG_SESSION = os.environ["TG_SESSION"]

LEADS_BOT_TOKEN = os.environ["LEADS_BOT_TOKEN"]
LEADS_CHAT_ID = os.environ["LEADS_CHAT_ID"]

STATE_DIR = Path(".lead_state")
STATE_FILE = STATE_DIR / "state.json"

MAX_AGE_HOURS = 48
SEARCH_LIMIT = 35
CHAT_SCAN_LIMIT = 250
MAX_LEADS_PER_RUN = 20
MIN_SCORE_TO_SEND = 28
QUERY_DELAY_SECONDS = 0.20

# Белый список именно туристических обсуждений, не рекламных каналов гидов.
# Недоступный/переименованный чат просто будет пропущен с warning в Actions.
TARGET_CHATS = [
    "abkhazia_chat",
    "abhazia_travel_chat",
]

# Наши источники и технические аккаунты никогда не считаем лидами.
BLOCKED_USERNAMES = {
    "vabkhazii",
    "vabkhaziileadsbot",
}


# =========================================================
# GLOBAL TELEGRAM SEARCH
# =========================================================

SEARCH_QUERIES = [
    # Экскурсии и скрытый спрос
    "Абхазия экскурсия",
    "нужна экскурсия Абхазия",
    "ищем экскурсию Абхазия",
    "посоветуйте экскурсию Абхазия",
    "нужен гид Абхазия",
    "ищем гида Абхазия",
    "индивидуальная экскурсия Абхазия",
    "что посмотреть Абхазия",
    "куда поехать Абхазия",
    "куда съездить Абхазия",
    "что посетить Абхазия",
    "Абхазия с детьми куда поехать",
    "едем в Абхазию что посмотреть",
    "отдыхаем в Абхазии куда поехать",

    # Города и экскурсии
    "экскурсии из Гагры",
    "куда поехать из Гагры",
    "что посмотреть в Гагре",
    "экскурсии из Пицунды",
    "куда поехать из Пицунды",
    "что посмотреть Пицунда",
    "Новый Афон экскурсия",
    "что посмотреть Новый Афон",
    "экскурсии из Сухума",
    "куда поехать из Сухума",
    "что посмотреть Сухум",
    "Гудаута экскурсия",

    # Маршруты
    "Рица экскурсия",
    "хочу на Рицу",
    "как попасть на Рицу",
    "кто возит на Рицу",
    "Мзы экскурсия",
    "как попасть на Мзы",
    "Восточная Абхазия экскурсия",
    "Акармара экскурсия",
    "Ткуарчал экскурсия",
    "Шакуранский водопад экскурсия",
    "Амткел экскурсия",

    # Попутчики
    "ищем попутчиков Абхазия",
    "кто завтра на Рицу",
    "кто едет на Рицу",
    "ищем компанию на экскурсию Абхазия",
    "нас двое экскурсия Абхазия",

    # Трансферы — общий спрос
    "нужен трансфер Абхазия",
    "ищем трансфер Абхазия",
    "трансфер в Абхазию",
    "трансфер из Абхазии",
    "нужна машина Абхазия",
    "кто встретит Абхазия",
    "как добраться Абхазия",
    "как доехать Абхазия",

    # Аэропорт/Адлер/Сочи ↔ Абхазия
    "аэропорт Сочи Абхазия трансфер",
    "аэропорт Сочи Гагра трансфер",
    "аэропорт Сочи Пицунда трансфер",
    "аэропорт Сочи Новый Афон трансфер",
    "аэропорт Сочи Сухум трансфер",
    "Абхазия аэропорт Сочи трансфер",
    "Адлер Абхазия трансфер",
    "Абхазия Адлер трансфер",
    "Сочи Абхазия трансфер",
    "Абхазия Сочи трансфер",
    "Сириус Абхазия трансфер",
    "Абхазия Сириус трансфер",

    # Красная Поляна / Роза Хутор
    "Красная Поляна Абхазия трансфер",
    "Абхазия Красная Поляна трансфер",
    "Роза Хутор Абхазия трансфер",
    "Абхазия Роза Хутор трансфер",
    "Эсто-Садок Абхазия трансфер",

    # Юг Краснодарского края
    "Краснодар Абхазия трансфер",
    "Анапа Абхазия трансфер",
    "Новороссийск Абхазия трансфер",
    "Геленджик Абхазия трансфер",
    "Туапсе Абхазия трансфер",
    "Лазаревское Абхазия трансфер",
    "Лоо Абхазия трансфер",
    "Дагомыс Абхазия трансфер",
    "Абхазия Краснодар трансфер",
    "Абхазия Анапа трансфер",
    "Абхазия Новороссийск трансфер",
    "Абхазия Геленджик трансфер",
    "Абхазия Туапсе трансфер",

    # Большие компании / дети / багаж
    "нужен минивэн Абхазия",
    "нужен микроавтобус Абхазия",
    "трансфер группа Абхазия",
    "трансфер с детьми Абхазия",
    "трансфер детское кресло Абхазия",
    "трансфер много багажа Абхазия",
]


# =========================================================
# SIGNALS
# =========================================================

HOT_PHRASES = [
    "нужен гид", "ищем гида", "ищу гида", "посоветуйте гида",
    "нужна экскурсия", "ищем экскурсию", "ищу экскурсию",
    "хочу экскурсию", "хотим экскурсию", "где заказать экскурсию",
    "кто организует", "кто возит", "кто свозит", "кто может свозить",
    "нужен трансфер", "ищем трансфер", "ищу трансфер",
    "нужна машина", "ищем машину", "нужен водитель",
    "кто отвезет", "кто отвезёт", "кто довезет", "кто довезёт",
    "кто заберет", "кто заберёт", "кто встретит",
]

WARM_PHRASES = [
    "куда поехать", "куда съездить", "что посмотреть", "что посетить",
    "куда сходить", "что посоветуете", "что рекомендуете",
    "едем в абхазию", "приезжаем в абхазию", "будем в абхазии",
    "отдыхаем в абхазии", "мы в гагре", "мы в пицунде",
    "мы в сухуме", "мы в новом афоне", "как добраться", "как доехать",
]

URGENT_PHRASES = [
    "сегодня", "завтра", "послезавтра", "сейчас", "срочно",
    "уже приехали", "мы уже", "сегодня прилетаем", "завтра прилетаем",
    "сегодня приезжаем", "завтра приезжаем",
]

SELLER_PHRASES = [
    "провожу экскурсии", "проводим экскурсии", "организуем экскурсии",
    "предлагаем экскурсии", "предлагаю экскурсии", "наши экскурсии",
    "стоимость экскурсии", "цена экскурсии", "запись на экскурсию",
    "бронируйте", "свободные места", "набор группы", "набираем группу",
    "экскурсии каждый день", "ваш гид", "я гид", "работаю гидом",
    "туроператор", "турагентство", "турфирма", "экскурсионное бюро",
    "скидка на экскурсию", "трансферы по абхазии", "предлагаем трансфер",
    "предлагаю трансфер", "заказывайте трансфер", "услуги трансфера",
    "наш автопарк", "наши автомобили", "трансфер каждый день",
    "встречаем в аэропорту", "встречаем на вокзале", "заказ трансфера",
    "для бронирования", "по вопросам бронирования", "пишите в личные сообщения",
    "пишите в лс", "пишите в личку", "напишите в личку", "обращайтесь в личку",
    "кому нужно пишите", "кому нужен трансфер", "кому нужна экскурсия",
    "трансфер и экскурсии", "трансфер - экскурсии", "трансфер — экскурсии",
    "запись в директ", "записывайтесь", "места ограничены",
]

JOB_PHRASES = [
    "требуются водители", "требуется водитель", "нужны водители",
    "нуждаемся в водителях", "ищем водителей", "ищем водителя на работу",
    "вакансия водителя", "вакансия", "работа водителем", "работа для водителей",
    "если ты водитель", "если вы водитель", "приглашаем водителей",
    "требуются сотрудники", "ищем сотрудников", "зарплата", "оплата за смену",
    "водитель категории", "резюме",
]

BROADCAST_CONTENT_PHRASES = [
    "абхазия сегодня", "побережье:", "осадки:", "ветер до", "море: вода",
    "мой выбор на сегодня", "факт дня", "прогноз погоды", "погода сегодня",
    "новости абхазии", "дайджест", "доброе утро", "подписывайтесь",
    "наш канал", "в нашем канале", "смотрите видео", "посмотрите на это видео",
]

# Признаки ответа/совета другому туристу. Один признак сам по себе не блокирует,
# но несколько таких фраз без вопроса и без первого лица — обычно не покупатель.
ADVICE_RESPONSE_PHRASES = [
    "вам нужно", "вам надо", "вам лучше", "переходите границу",
    "там будет", "там есть", "садитесь на", "выходите на", "доедете до",
    "идет через", "идёт через", "на маршрутке", "маршрутка идет",
    "маршрутка идёт", "можно доехать", "доехать можно", "по стоимости",
    "стоит примерно", "примерно стоит", "советую", "рекомендую",
    "лучше ехать", "лучше поехать", "на каждой маршрутке", "вам нужен",
]

BUYER_INTENT_PHRASES = [
    # Явный запрос услуги от первого лица / своей компании.
    "мне нужен", "мне нужна", "нам нужен", "нам нужна", "нам нужно",
    "нужен трансфер", "нужна машина", "нужна экскурсия", "нужен гид",
    "нужно доехать", "нужно добраться", "хочу ", "хотим ",
    "ищу ", "ищем ", "подскажите", "посоветуйте", "порекомендуйте",
    "кто может", "кто возит", "кто отвезет", "кто отвезёт",
    "кто довезет", "кто довезёт", "кто заберет", "кто заберёт",
    "кто встретит", "кто свозит", "как добраться", "как доехать",
    "куда поехать", "куда съездить", "куда сходить", "что посмотреть",
    "что посетить", "чем заняться", "где заказать", "где найти",
    "сколько стоит", "сколько будет стоить", "можно заказать",
    "можно ли заказать", "кто организует", "есть ли трансфер",
    "есть ли экскурсия", "кто едет", "кто завтра", "кто сегодня",
    "ищем попут", "ищу попут",
]

ABKHAZIA_CONTEXT_PHRASES = [
    "абхаз", "псоу", "цандрыпш", "гантиади", "гагр", "пицунд", "гудаут",
    "новый афон", "нового афона", "новом афоне", "сухум", "очамч", "ткуарчал",
    "риц", "мзы", "акармар", "амткел", "шакуран", "черниговк",
]

TRANSFER_PHRASES = [
    "нужен трансфер", "нужна машина", "ищем трансфер", "ищу трансфер",
    "заказать трансфер", "кто отвезет", "кто отвезёт", "кто довезет",
    "кто довезёт", "кто заберет", "кто заберёт", "кто встретит",
    "нужен водитель", "ищем водителя", "нужен минивэн", "нужен минивен",
    "нужен микроавтобус", "трансфер", "такси", "машина из", "машина до",
    "как доехать", "как добраться", "забрать из аэропорта",
    "встретить в аэропорту", "встретить на вокзале", "забрать с вокзала",
    "довезти до отеля", "довезти до гостиницы", "до границы", "от границы",
]

COMPANION_PHRASES = [
    "ищем попутчиков", "ищу попутчиков", "ищем попутчика", "ищу попутчика",
    "кто с нами", "кто поедет с нами", "кто едет", "кто завтра на",
    "есть желающие", "есть кто хочет", "ищем компанию", "ищу компанию",
    "добор группы", "добрать группу", "ищем людей", "кто хочет присоединиться",
    "присоединиться к поездке",
]

EXCURSION_PHRASES = [
    "нужен гид", "ищем гида", "ищу гида", "посоветуйте гида",
    "нужна экскурсия", "ищем экскурсию", "ищу экскурсию", "хочу экскурсию",
    "хотим экскурсию", "посоветуйте экскурсию", "какую экскурсию",
    "индивидуальная экскурсия", "куда поехать", "куда съездить", "куда сходить",
    "что посмотреть", "что посетить", "чем заняться", "куда лучше поехать", "кто возит на рицу",
    "хочу на рицу", "хотим на рицу", "как попасть на рицу", "хочу на мзы",
    "хотим на мзы", "как попасть на мзы", "джиппинг", "джип тур", "джип-тур",
    "достопримечательности",
]


# =========================================================
# GEOGRAPHY / ROUTES
# =========================================================

CITIES = {
    "Цандрыпш": ["цандрыпш", "гантиади"],
    "Гагра": ["гагра", "гагре", "гагры", "гагру"],
    "Пицунда": ["пицунда", "пицунде", "пицунды", "пицунду"],
    "Гудаута": ["гудаута", "гудауте", "гудауты", "гудауту"],
    "Новый Афон": ["новый афон", "новом афоне", "нового афона", "новому афону"],
    "Сухум": ["сухум", "сухуме", "сухуми", "сухума", "сухуму"],
    "Очамчыра": ["очамчыра", "очамчира", "очамчыре", "очамчыру", "очамчиру"],
    "Ткуарчал": ["ткуарчал", "ткуарчале", "ткуарчала", "ткуарчалу"],
    "Гал": ["гал", "гале"],
    "Адлер": ["адлер", "адлере"],
    "Сочи": ["сочи"],
    "Сириус": ["сириус"],
    "Красная Поляна": ["красная поляна", "красной поляне"],
    "Роза Хутор": ["роза хутор"],
    "Эсто-Садок": ["эсто-садок", "эстосадок"],
    "Лазаревское": ["лазаревское", "лазаревском"],
    "Лоо": ["лоо"],
    "Дагомыс": ["дагомыс"],
    "Туапсе": ["туапсе"],
    "Геленджик": ["геленджик", "геленджике"],
    "Новороссийск": ["новороссийск", "новороссийске"],
    "Анапа": ["анапа", "анапе", "анапы"],
    "Краснодар": ["краснодар", "краснодаре"],
}

SPECIAL_PLACES = {
    "Аэропорт Сочи": ["аэропорт сочи", "аэропорт адлер", "аэропорта сочи", "аэропорту сочи"],
    "Псоу": ["псоу", "граница абхазии", "границы абхазии", "границе абхазии"],
    "Ж/д вокзал Адлер": ["вокзал адлер", "жд адлер", "ж/д адлер", "жд вокзал адлер", "ж/д вокзал адлер"],
    "Ж/д вокзал Сочи": ["вокзал сочи", "жд сочи", "ж/д сочи", "жд вокзал сочи", "ж/д вокзал сочи"],
}

ROUTES = {
    "Рица": ["рица", "рицу", "рице", "рицы", "озеро рица", "озеро рицу", "малая рица"],
    "Мзы": ["мзы", "озеро мзы"],
    "Новый Афон": ["новый афон", "новоафон", "новоафонская пещера", "анакопия"],
    "Восточная Абхазия": ["акармара", "ткуарчал", "шакуран", "черниговка", "амткел", "ольгинские водопады", "водопад", "водопады"],
    "Святыни": ["каманы", "дранда", "илор", "бедийский", "бедиа", "святыни", "монастырь", "храм"],
}


# =========================================================
# STATE
# =========================================================

def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["seen"] = state.get("seen", [])[-3000:]
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# =========================================================
# BOT API
# =========================================================

def bot_api(method, data):
    url = f"https://api.telegram.org/bot{LEADS_BOT_TOKEN}/{method}"
    payload = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"User-Agent": "VAbkhaziiLeads/3.0"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"Telegram Bot API error: {result}")

    return result


def send_private_message(text):
    bot_api(
        "sendMessage",
        {
            "chat_id": LEADS_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
    )


# =========================================================
# TEXT HELPERS
# =========================================================

def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip()


def contains_any(text, phrases):
    lower = text.lower()
    return any(phrase in lower for phrase in phrases)


def looks_like_seller(text):
    lower = text.lower()

    if contains_any(lower, SELLER_PHRASES):
        return True

    commercial_markers = [
        "₽", "руб", "цена", "стоимость", "запись", "бронь", "бронируйте",
        "телефон", "whatsapp", "ватсап", "скидка", "акция", "предоплата",
        "места", "заказ", "менеджер",
    ]
    count = sum(1 for marker in commercial_markers if marker in lower)

    # Несколько коммерческих маркеров + контакт обычно означают объявление продавца.
    has_contact = bool(
        re.search(r"(?:\+?7|8)[\s()\-]*\d{3}", lower)
        or "@" in text
        or "t.me/" in lower
    )

    if count >= 3 and has_contact:
        return True

    return count >= 5


def looks_like_job(text):
    return contains_any(text, JOB_PHRASES)


def looks_like_broadcast_content(text):
    lower = text.lower()
    hits = sum(1 for phrase in BROADCAST_CONTENT_PHRASES if phrase in lower)
    return hits >= 2


def looks_like_advice_response(text):
    lower = text.lower()
    hits = sum(1 for phrase in ADVICE_RESPONSE_PHRASES if phrase in lower)

    # Реальный вопрос пользователя не режем только из-за слов "на маршрутке" и т.п.
    if "?" in text:
        return False

    # Явное первое лицо означает, что человек говорит о своей потребности.
    first_person_need = any(
        phrase in lower
        for phrase in [
            "мне нужен", "мне нужна", "нам нужен", "нам нужна", "нам нужно",
            "я ищу", "мы ищем", "ищу ", "ищем ", "хочу ", "хотим ",
        ]
    )
    if first_person_need:
        return False

    return hits >= 2


def looks_like_commercial_sender(sender, text):
    if not sender:
        return False

    display = " ".join(
        part for part in [
            getattr(sender, "first_name", None),
            getattr(sender, "last_name", None),
            getattr(sender, "username", None),
        ]
        if part
    ).lower()

    strong_profile_markers = [
        "трансфер и экскурсии", "трансфер по абхазии", "экскурсии по абхазии",
        "гид по абхазии", "туры по абхазии", "такси абхазия",
        "transfer_abkhazia", "travel_in_abkhazia",
    ]

    if any(marker in display for marker in strong_profile_markers):
        return True

    # Коммерческое название + призыв написать/заказать.
    profile_service_markers = ["трансфер", "экскурс", "гид", "такси", "туры"]
    call_to_action = ["пишите", "заказ", "бронь", "брониру", "обращайтесь"]
    if any(marker in display for marker in profile_service_markers) and any(
        marker in text.lower() for marker in call_to_action
    ):
        return True

    return False


def has_abkhazia_context(text):
    lower = text.lower()
    return any(phrase in lower for phrase in ABKHAZIA_CONTEXT_PHRASES)


def has_buyer_intent(text):
    lower = text.lower()

    # Отсекаем ответы и советы другим туристам.
    if looks_like_advice_response(text):
        return False

    direct = any(phrase in lower for phrase in BUYER_INTENT_PHRASES)
    if direct:
        return True

    # Короткий естественный вопрос туриста тоже считается намерением.
    question_words = [
        "кто ", "куда ", "как ", "где ", "какой ", "какая ", "какие ",
        "можно ли", "есть кто", "подскажите", "посоветуйте", "сколько ",
    ]
    if "?" in text and any(word in lower for word in question_words):
        return True

    return False


def is_allowed_chat(chat):
    if not chat:
        return False

    username = (getattr(chat, "username", None) or "").lower()
    if not username:
        return False

    if username in BLOCKED_USERNAMES:
        return False

    # Broadcast-каналы — не источник клиентских сообщений.
    if getattr(chat, "broadcast", False):
        return False

    # Для первого этапа принимаем только публичные группы/супергруппы.
    return bool(getattr(chat, "megagroup", False))


def is_allowed_sender(sender, self_user_id):
    if not isinstance(sender, User):
        return False

    if getattr(sender, "bot", False):
        return False

    if self_user_id and getattr(sender, "id", None) == self_user_id:
        return False

    username = (getattr(sender, "username", None) or "").lower()
    if username in BLOCKED_USERNAMES:
        return False

    return True


# =========================================================
# EXTRACTION
# =========================================================

def detect_city(text):
    lower = text.lower()
    for city, variants in CITIES.items():
        if any(variant in lower for variant in variants):
            return city
    return None


def detect_route(text):
    lower = text.lower()
    for route, variants in ROUTES.items():
        if any(variant in lower for variant in variants):
            return route
    return None


def detect_people(text):
    lower = text.lower()
    patterns = [
        r"\bнас\s+(\d{1,2})\b",
        r"\b(\d{1,2})\s*человек\b",
        r"\b(\d{1,2})\s*чел\b",
        r"\b(\d{1,2})\s*взросл",
        r"\bсемья\s+из\s+(\d{1,2})\b",
        r"\bкомпания\s+из\s+(\d{1,2})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            try:
                value = int(match.group(1))
                if 1 <= value <= 50:
                    return value
            except Exception:
                pass

    word_values = {
        "нас двое": 2,
        "нас трое": 3,
        "нас четверо": 4,
        "нас пятеро": 5,
    }
    for phrase, value in word_values.items():
        if phrase in lower:
            return value

    return None


def detect_children(text):
    lower = text.lower()
    return any(
        word in lower
        for word in [
            "ребенок", "ребёнок", "дети", "ребёнка", "ребенка",
            "с детьми", "детское кресло", "автокресло",
        ]
    )


def detect_baggage(text):
    lower = text.lower()
    return any(
        word in lower
        for word in ["багаж", "чемодан", "чемоданы", "коляска", "велосипед", "лыжи", "сноуборд"]
    )


def detect_urgency(text):
    lower = text.lower()
    for phrase in URGENT_PHRASES:
        if phrase in lower:
            return phrase
    return None


def detect_date_hint(text):
    lower = text.lower()

    for phrase in [
        "сегодня", "завтра", "послезавтра", "на выходных", "в выходные",
        "на следующей неделе",
    ]:
        if phrase in lower:
            return phrase

    patterns = [
        r"\b([0-3]?\d)\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b",
        # Только точки/слэши: диапазон "5-7 минут" не должен становиться датой.
        r"\b([0-3]?\d)[./]([01]?\d)(?:[./](\d{2,4}))?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return match.group(0)

    return None


def detect_time_hint(text):
    for pattern in [
        r"\b(?:в|к)\s+([01]?\d|2[0-3])[:.](\d{2})\b",
        r"\b([01]?\d|2[0-3])[:.](\d{2})\b",
    ]:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(0)
    return None


def detect_flight_train(text):
    lower = text.lower()
    flight = re.search(r"\b(?:рейс|flight)\s*[:№#-]?\s*([a-zа-я]{1,3}\s?\d{2,5})\b", lower, re.IGNORECASE)
    if flight:
        return f"рейс {flight.group(1).upper()}"

    train = re.search(r"\b(?:поезд)\s*[:№#-]?\s*(\d{1,4}[а-яa-z]?)\b", lower, re.IGNORECASE)
    if train:
        return f"поезд {train.group(1)}"

    return None


def detect_all_places(text):
    lower = text.lower()
    matches = []

    def collect(mapping):
        for name, variants in mapping.items():
            best_index = None
            for variant in variants:
                idx = lower.find(variant)
                if idx >= 0 and (best_index is None or idx < best_index):
                    best_index = idx
            if best_index is not None:
                matches.append((best_index, name))

    collect(SPECIAL_PLACES)
    collect(CITIES)

    matches.sort(key=lambda item: item[0])
    names = []
    for _, name in matches:
        if name not in names:
            names.append(name)

    # Убираем дубли, возникающие из составных названий.
    if "Аэропорт Сочи" in names and "Сочи" in names:
        names.remove("Сочи")
    if "Ж/д вокзал Адлер" in names and "Адлер" in names:
        names.remove("Адлер")
    if "Ж/д вокзал Сочи" in names and "Сочи" in names:
        names.remove("Сочи")

    return names


# =========================================================
# LEAD TYPE / SCORE
# =========================================================

def detect_lead_type(text):
    lower = normalize(text).lower()

    transfer_score = sum(1 for phrase in TRANSFER_PHRASES if phrase in lower)
    companion_score = sum(1 for phrase in COMPANION_PHRASES if phrase in lower)
    excursion_score = sum(1 for phrase in EXCURSION_PHRASES if phrase in lower)

    if any(word in lower for word in [
        "трансфер", "машина", "такси", "водитель", "доехать", "добраться",
        "отвезти", "довезти", "забрать", "встретить", "аэропорт", "вокзал",
    ]):
        transfer_score += 2

    if detect_route(text):
        excursion_score += 1

    scores = {
        "transfer": transfer_score,
        "companions": companion_score,
        "excursion": excursion_score,
    }
    best_type = max(scores, key=scores.get)

    if scores[best_type] <= 0:
        return "unknown"
    return best_type


def classify_lead(text):
    lower = text.lower()

    # Сначала жёстко убираем вакансии, рекламные объявления и контент-посты.
    if looks_like_job(text):
        return None

    if looks_like_seller(text):
        return None

    if looks_like_broadcast_content(text):
        return None

    if looks_like_advice_response(text):
        return None

    # Нам нужен именно потенциальный покупатель, а не просто упоминание Рицы/трансфера.
    if not has_buyer_intent(text):
        return None

    # Поисковик предназначен для Абхазии и связанных с ней маршрутов.
    if not has_abkhazia_context(text):
        return None

    lead_type = detect_lead_type(text)

    # Если намерение есть, но тип не определился, туристический вопрос
    # по Абхазии считаем экскурсионным запросом.
    if lead_type == "unknown":
        lead_type = "excursion"

    score = 0
    reasons = ["автор — человек", "есть покупательское намерение"]

    hot_hits = [phrase for phrase in HOT_PHRASES if phrase in lower]
    warm_hits = [phrase for phrase in WARM_PHRASES if phrase in lower]
    urgent_hits = [phrase for phrase in URGENT_PHRASES if phrase in lower]

    if hot_hits:
        score += 55
        reasons.append("явный запрос услуги")
    elif warm_hits:
        score += 28
        reasons.append("туристический вопрос")
    else:
        score += 20
        reasons.append("потенциальный спрос")

    if urgent_hits:
        score += 20
        reasons.append("срочный запрос")

    if lead_type == "transfer":
        score += 14
        reasons.append("трансфер")
    elif lead_type == "excursion":
        score += 12
        reasons.append("экскурсия")
    elif lead_type == "companions":
        score += 14
        reasons.append("попутчики/добор")

    if detect_route(text):
        score += 8
    if detect_city(text):
        score += 6
    if len(detect_all_places(text)) >= 2:
        score += 10
    if detect_people(text):
        score += 8
    if detect_date_hint(text):
        score += 8
    if detect_time_hint(text):
        score += 4
    if "?" in text:
        score += 5

    # Слишком длинные посты без вопроса чаще являются публикациями/рекламой.
    if len(text) > 900 and "?" not in text:
        score -= 25

    if len(text) < 12:
        score -= 15

    if score >= 75:
        level = "🔥 ГОРЯЧИЙ"
    elif score >= 50:
        level = "🟡 ТЁПЛЫЙ"
    elif score >= MIN_SCORE_TO_SEND:
        level = "⚪ ПЕРСПЕКТИВНЫЙ"
    else:
        return None

    return {
        "score": score,
        "level": level,
        "lead_type": lead_type,
        "reasons": reasons,
    }


# =========================================================
# REPLY DRAFT
# =========================================================

def make_reply(text, lead_type):
    city = detect_city(text)
    route = detect_route(text)
    people = detect_people(text)
    date_hint = detect_date_hint(text)
    parts = ["Добрый день!"]

    if lead_type == "transfer":
        places = detect_all_places(text)
        if len(places) >= 2:
            parts.append(f"Могу помочь с трансфером по маршруту {places[0]} — {places[1]}.")
        else:
            parts.append("Могу помочь с трансфером.")
        if people:
            parts.append(f"Для {people} человек можно подобрать подходящий автомобиль.")
        if date_hint:
            parts.append(f"На {date_hint} можно проверить свободную машину.")
        parts.append("Напишите, пожалуйста, точку отправления, точку назначения, дату и время, количество пассажиров и багажа.")

    elif lead_type == "companions":
        parts.append("Вижу, что вы ищете попутчиков или компанию для поездки.")
        if route:
            parts.append(f"По направлению «{route}» можно подобрать вариант.")
        parts.append("Напишите дату поездки и сколько вас человек.")

    else:
        if route:
            parts.append(f"Могу организовать поездку по маршруту «{route}».")
        else:
            parts.append("Могу помочь подобрать экскурсию по Абхазии под ваши пожелания.")
        if city:
            parts.append(f"Можно подобрать удобный выезд из {city}.")
        if people:
            parts.append(f"Для компании из {people} человек подберём формат.")
        parts.append("Напишите, пожалуйста, дату поездки, сколько будет взрослых и детей и что хочется увидеть.")

    return " ".join(parts)


# =========================================================
# CARDS
# =========================================================

def build_message_link(entity, message_id):
    username = getattr(entity, "username", None)
    if not username:
        return None
    return f"https://t.me/{username}/{message_id}"


def lead_type_label(lead_type):
    return {
        "transfer": "🚐 ТРАНСФЕР",
        "companions": "👥 ПОПУТЧИКИ / ДОБОР",
        "excursion": "🏔 ЭКСКУРСИЯ",
        "unknown": "🔎 ТУРИСТИЧЕСКИЙ ЗАПРОС",
    }.get(lead_type, "🔎 ТУРИСТИЧЕСКИЙ ЗАПРОС")


def source_title(entity):
    return (
        getattr(entity, "title", None)
        or getattr(entity, "first_name", None)
        or getattr(entity, "username", None)
        or "Telegram"
    )


def make_card(text, entity, sender, message_id, date, classification):
    lead_type = classification["lead_type"]
    city = detect_city(text)
    route = detect_route(text)
    people = detect_people(text)
    urgency = detect_urgency(text)
    date_hint = detect_date_hint(text)
    time_hint = detect_time_hint(text)
    children = detect_children(text)
    baggage = detect_baggage(text)
    flight_train = detect_flight_train(text)
    places = detect_all_places(text)
    link = build_message_link(entity, message_id)
    reply = make_reply(text, lead_type)

    sender_name = None
    sender_username = None
    if sender:
        sender_name = " ".join(
            part for part in [
                getattr(sender, "first_name", None),
                getattr(sender, "last_name", None),
            ] if part
        ).strip() or None
        sender_username = getattr(sender, "username", None)

    lines = [
        f"{classification['level']} <b>ЛИД</b>",
        lead_type_label(lead_type),
        "",
        f"⭐ Оценка: <b>{classification['score']}</b>",
        f"📡 Источник: <b>{html.escape(str(source_title(entity)))}</b>",
        "✅ Автор: <b>пользователь Telegram (не бот и не канал)</b>",
    ]

    if sender_name:
        lines.append(f"👤 Автор: <b>{html.escape(sender_name)}</b>")
    if sender_username:
        lines.append(f"🔹 Telegram: @{html.escape(sender_username)}")
    if city:
        lines.append(f"📍 Город: <b>{html.escape(city)}</b>")
    if route:
        lines.append(f"🏞 Интерес: <b>{html.escape(route)}</b>")
    if people:
        lines.append(f"👥 Людей: <b>{people}</b>")

    if lead_type == "transfer":
        if len(places) >= 2:
            lines.append(f"🛣 Маршрут: <b>{html.escape(places[0])} → {html.escape(places[1])}</b>")
        elif places:
            lines.append(f"🛣 Упомянуто: <b>{html.escape(', '.join(places[:4]))}</b>")

    if date_hint:
        lines.append(f"📅 Когда: <b>{html.escape(date_hint)}</b>")
    if time_hint:
        lines.append(f"🕐 Время: <b>{html.escape(time_hint)}</b>")
    if urgency:
        lines.append(f"⏰ Срочность: <b>{html.escape(urgency)}</b>")
    if children:
        lines.append("👶 Есть дети / упоминание детского кресла")
    if baggage:
        lines.append("🧳 Есть багаж / крупные вещи")
    if flight_train:
        lines.append(f"✈️🚆 {html.escape(flight_train)}")
    if classification["reasons"]:
        lines.append("🎯 Сигналы: " + html.escape(", ".join(classification["reasons"])))

    lines += [
        "",
        "💬 <b>Сообщение:</b>",
        html.escape(text[:1200]),
        "",
        "✍️ <b>Черновик ответа:</b>",
        html.escape(reply),
    ]

    if link:
        lines += ["", f'<a href="{html.escape(link)}">🔗 Открыть исходное сообщение</a>']

    lines += ["", "🕒 " + date.strftime("%d.%m.%Y %H:%M UTC")]

    card = "\n".join(lines)
    if len(card) > 3900:
        card = card[:3850] + "\n…"
    return card


# =========================================================
# SEARCH
# =========================================================

async def message_to_candidate(message, cutoff, state, source_kind, self_user_id):
    if not message:
        return None

    # Наши собственные сообщения, посты каналов, пересылки и сообщения через ботов
    # не должны попадать в лиды.
    if getattr(message, "out", False):
        return None
    if getattr(message, "post", False):
        return None
    if getattr(message, "fwd_from", None):
        return None
    if getattr(message, "via_bot_id", None):
        return None

    text = normalize(getattr(message, "message", ""))
    if not text or not message.date:
        return None

    date = message.date
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    if date < cutoff:
        return None

    chat = await message.get_chat()
    if not is_allowed_chat(chat):
        return None

    try:
        sender = await message.get_sender()
    except Exception:
        sender = None

    if not is_allowed_sender(sender, self_user_id):
        return None

    if looks_like_commercial_sender(sender, text):
        return None

    unique_id = f"{getattr(chat, 'id', '')}:{message.id}"
    if unique_id in state.get("seen", []):
        return None

    classification = classify_lead(text)
    if not classification:
        return None

    return {
        "id": unique_id,
        "message_id": message.id,
        "text": text,
        "date": date,
        "chat": chat,
        "sender": sender,
        "classification": classification,
        "source_kind": source_kind,
    }


def merge_candidate(candidates, item):
    if not item:
        return
    current = candidates.get(item["id"])
    if current is None or item["classification"]["score"] > current["classification"]["score"]:
        candidates[item["id"]] = item


async def global_search_worker(client, state, cutoff, self_user_id):
    candidates = {}

    for query in SEARCH_QUERIES:
        print(f"[GLOBAL] {query}")
        try:
            async for message in client.iter_messages(None, search=query, limit=SEARCH_LIMIT):
                item = await message_to_candidate(message, cutoff, state, "global", self_user_id)
                merge_candidate(candidates, item)

        except FloodWaitError as exc:
            print(f"[FLOOD WAIT] {exc.seconds}s on query: {query}")
            if exc.seconds <= 60:
                await asyncio.sleep(exc.seconds + 1)
            else:
                break
        except Exception as exc:
            print(f"[GLOBAL WARNING] {query}: {exc}")

        await asyncio.sleep(QUERY_DELAY_SECONDS)

    return candidates


async def chat_scan_worker(client, state, cutoff, self_user_id):
    candidates = {}

    for chat_ref in TARGET_CHATS:
        print(f"[CHAT] @{chat_ref}")
        try:
            entity = await client.get_entity(chat_ref)

            async for message in client.iter_messages(entity, limit=CHAT_SCAN_LIMIT):
                if message.date:
                    date = message.date
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    if date < cutoff:
                        break

                item = await message_to_candidate(message, cutoff, state, "whitelist", self_user_id)
                merge_candidate(candidates, item)

        except FloodWaitError as exc:
            print(f"[CHAT FLOOD WAIT] @{chat_ref}: {exc.seconds}s")
            if exc.seconds <= 60:
                await asyncio.sleep(exc.seconds + 1)
        except Exception as exc:
            print(f"[CHAT WARNING] @{chat_ref}: {exc}")

    return candidates


async def search_public_messages(client, state, self_user_id):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)

    # Два независимых поисковых воркера первого этапа.
    global_results, chat_results = await asyncio.gather(
        global_search_worker(client, state, cutoff, self_user_id),
        chat_scan_worker(client, state, cutoff, self_user_id),
    )

    candidates = {}
    for source in (global_results, chat_results):
        for item in source.values():
            merge_candidate(candidates, item)

    result = list(candidates.values())
    result.sort(
        key=lambda item: (item["classification"]["score"], item["date"]),
        reverse=True,
    )

    return result[:MAX_LEADS_PER_RUN]


# =========================================================
# MAIN
# =========================================================

async def async_main():
    state = load_state()
    client = TelegramClient(StringSession(TG_SESSION), TG_API_ID, TG_API_HASH)
    await client.connect()

    try:
        if not await client.is_user_authorized():
            raise RuntimeError("TG_SESSION is not authorized")

        me = await client.get_me()
        print("Connected as:", getattr(me, "first_name", ""), getattr(me, "username", ""))

        leads = await search_public_messages(client, state, getattr(me, "id", None))
        print(f"Found {len(leads)} lead(s)")

        if not leads:
            print("No new leads found.")
            save_state(state)
            return

        sent = 0
        for lead in leads:
            try:
                card = make_card(
                    lead["text"],
                    lead["chat"],
                    lead["sender"],
                    lead["message_id"],
                    lead["date"],
                    lead["classification"],
                )
                send_private_message(card)
                state.setdefault("seen", []).append(lead["id"])
                sent += 1
            except Exception as exc:
                print("Send warning:", exc)

        save_state(state)
        print(f"Sent {sent} lead(s)")

    finally:
        await client.disconnect()


def main():
    try:
        asyncio.run(async_main())
    except Exception as exc:
        print("ERROR:", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
