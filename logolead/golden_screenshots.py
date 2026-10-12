"""Human-verified reference examples transcribed from user-provided screenshots.

Fixtures are NOT collected live, MUST NOT be emitted to @logopedutkina.
They establish expected intent recognition; live delivery requires source URL,
timestamp and independently accessible message/order in the configured account.
"""

GOLDEN_TELEGRAM = [
    {
        "id": "telegram-ekaterina-20261010",
        "source": "Telegram",
        "date_label": "2026-10-10",
        "group_label": "Русскоязычный Таиланд",
        "text": "Здравствуйте. Ищу логопеда для дочери 7 лет. Отсутствует звук Р",
        "expected": "direct_client_request",
        "verified_source_url": None,
    },
]
GOLDEN_PROFI = [
    {
        "id": "profi-istra-2y",
        "source": "Profi.ru · Истра",
        "date_label": "2026-10-10",
        "text": "Логопеды. Возраст ребёнка: 2 года. Ребёнок плохо говорит, ребёнок не говорит. В детский клуб ищем логопеда",
        "price_label": "1200 ₽",
    },
    {
        "id": "profi-balashikha-4y-massage",
        "source": "Profi.ru · Балашиха",
        "date_label": "2026-10-09",
        "text": "Логопедический массаж. Возраст ребёнка: 4 года",
        "price_label": "2100–3300 ₽",
    },
    {
        "id": "profi-odintsovo-3-7y",
        "source": "Profi.ru · Одинцово",
        "date_label": "2026-10-09",
        "text": "Логопед для ребёнка. Возраст ребёнка: 3.7 года. Поставить другие звуки, коррекция заикания",
        "price_label": "2000–3100 ₽",
    },
    {
        "id": "profi-zrr-2y-remote",
        "source": "Profi.ru · Москва",
        "date_label": "2026-10-10",
        "text": "Логопед-дефектолог. Возраст ребёнка: 2 года. Коррекция задержки речевого развития (ЗРР)",
        "price_label": "до 3400 ₽",
    },
    {
        "id": "profi-4class-zrr",
        "source": "Profi.ru · Москва",
        "date_label": "2026-10-10",
        "text": "Логопед-дефектолог. 4 класс. Ребёнок плохо говорит, коррекция задержки речевого развития (ЗРР)",
        "price_label": "2800–3800 ₽",
    },
    {
        "id": "profi-bilingual-2class",
        "source": "Profi.ru · Санкт-Петербург",
        "date_label": "2026-10-11",
        "text": "Логопед дефектолог. 2 класс. Ищу опытного логопеда-дефектолога для занятий с ребёнком-билингвом",
        "price_label": None,
    },
    {
        "id": "profi-dyslexia-4y",
        "source": "Profi.ru · Москва",
        "date_label": "2026-10-10",
        "text": "Дислексия. Возраст ребёнка: 4 года",
        "price_label": None,
    },
    {
        "id": "profi-phonopedist-adult",
        "source": "Profi.ru · Кабардино-Балкария",
        "date_label": "2026-10-10",
        "text": "Фонопеды. Мне 19 лет и у меня расщелина твёрдого и мягкого нёба, мне нужен фонопед",
        "price_label": "от 1600 ₽",
    },
]
NEGATIVE_CASES = [
    "Я логопед, провожу занятия онлайн, открыта запись",
    "Вакансия: требуется логопед в школу на ставку",
    "Логопед набирает детей на занятия",
]
