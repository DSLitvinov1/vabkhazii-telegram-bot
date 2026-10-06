import json
import os
import urllib.parse
import urllib.request

token = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

text = """🌿 ИНДИВИДУАЛЬНЫЕ ЭКСКУРСИИ И ТРАНСФЕРЫ ПО АБХАЗИИ

Если вы уже знаете даты поездки, можно не искать маршруты по десяткам чатов.

Оставьте:
— даты;
— город или точку выезда;
— количество человек;
— что хотите посмотреть.

Подберём подходящий маршрут или трансфер и свяжемся для подтверждения.

👉 Заявка:
https://choiceflow-affiliate.onrender.com/excursions.html

Можно указать, что вам важнее: природа, Новый Афон, Рица, водопады, святыни, прогулка без спешки или просто трансфер.

Никакой оплаты на странице не требуется."""

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = urllib.parse.urlencode({
    "chat_id": channel,
    "text": text,
    "disable_web_page_preview": "false",
}).encode("utf-8")

req = urllib.request.Request(url, data=payload, method="POST")
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read().decode("utf-8"))

if not result.get("ok"):
    raise RuntimeError(f"Telegram error: {result}")

print("Direct sales post published.")
