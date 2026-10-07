import json
import os
import urllib.parse
import urllib.request

token = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

text = """✈️ КАК НЕ ПЕРЕПЛАТИТЬ ЗА БАГАЖ ПРИ ПОКУПКЕ БИЛЕТА

Самая частая ошибка — смотреть только на первую цену авиабилета. У дешёвого тарифа багаж может не входить вообще, а добавление чемодана после покупки иногда сильно меняет итоговую стоимость поездки. Перед оплатой проверьте не только килограммы, но и допустимые размеры, количество мест и правила конкретного тарифа. Если летите вдвоём, иногда выгоднее купить один багаж на двоих, чем два расширенных тарифа. Если маршрут со стыковкой, отдельно проверьте правила каждого перевозчика и нужно ли получать багаж между рейсами. Скриншот условий тарифа перед оплатой тоже лишним не будет.

Собрали короткий чек-лист, что именно проверять до покупки:
https://choiceflow-affiliate.onrender.com/bagazh-aviabilet.html?utm_source=telegram&utm_medium=owned&utm_campaign=vabkhazii_baggage

ChoiceFlow — наш новый сервис-подборщик: он помогает сначала разобраться в задаче, а уже потом ведёт к подходящему сервису или покупке.

ℹ️ На ChoiceFlow часть внешних ссылок может быть партнёрской. Это отмечается на сайте; цена для пользователя из-за самого факта партнёрской ссылки не увеличивается."""

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

print("ChoiceFlow travel content post published.")
