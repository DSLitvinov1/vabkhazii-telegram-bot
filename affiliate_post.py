import json
import os
import urllib.parse
import urllib.request

token = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

text = """🌍 ЕЩЁ ДВА ПОЛЕЗНЫХ СЕРВИСА ДЛЯ ПУТЕШЕСТВИЯ

Если хочется не только самостоятельно собирать маршрут, можно посмотреть авторские туры и готовые программы на Youtravel.me:
https://dorinebeaumont.com/g/6gk4ba6fs6e0e02a444acc54f31e64/?erid=25H8d7vbP8SRTvK4AKHyL7

Для зарубежных поездок отдельно можно проверить туристическую страховку EKTA:
https://ogsib.com/g/92qb79zvwne0e02a444a239505df72/

Перед оформлением обязательно проверьте программу тура, условия отмены, территорию действия страховки, исключения и страховую сумму.

ℹ️ Партнёрский материал: обе программы одобрены для площадки VAbkhazii. Канал может получить вознаграждение после подтверждённой покупки; цена для пользователя из-за этого не увеличивается."""

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = urllib.parse.urlencode({
    "chat_id": channel,
    "text": text,
    "disable_web_page_preview": "true",
}).encode("utf-8")

req = urllib.request.Request(url, data=payload, method="POST")
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read().decode("utf-8"))

if not result.get("ok"):
    raise RuntimeError(f"Telegram error: {result}")

print("Affiliate travel post published.")
