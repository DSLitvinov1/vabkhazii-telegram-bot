import json
import os
import urllib.parse
import urllib.request

token = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

text = """✈️ БИЛЕТЫ И ОТЕЛИ ДЛЯ ПОЕЗДКИ В АБХАЗИЮ

Если едете через Сочи/Адлер или планируете перелёт в Сухум, сравнивайте не только стартовую цену: багаж, возврат и условия тарифа могут сильно менять итоговую стоимость.

Для сравнения билетов:
https://choiceflow-affiliate.onrender.com/travel.html

Ещё один вариант — City.Travel: там можно проверить авиабилеты и размещение в одном сервисе:
https://ficca2021.com/g/c3c08bdc8fe0e02a444a09315e6c64/

Перед оплатой обязательно проверьте даты, аэропорт, багаж и правила возврата.

ℹ️ Партнёрский материал: ссылки могут приносить каналу вознаграждение после подтверждённой покупки; цена для пользователя из-за этого не увеличивается."""

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
