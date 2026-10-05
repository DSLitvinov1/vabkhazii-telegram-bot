import json
import os
import urllib.parse
import urllib.request

token = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("TELEGRAM_CHANNEL", "@VAbkhazii")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

text = """✈️ КАК СРАВНИТЬ БИЛЕТЫ ДЛЯ ПОЕЗДКИ В АБХАЗИЮ

Если планируете дорогу через Сочи или Адлер, лучше проверять несколько сервисов: итоговая цена может отличаться из-за багажа, возврата и доступных тарифов.

Мы собрали отдельную страницу, где можно быстро сравнить варианты и перейти к подходящему сервису:
https://choiceflow-affiliate.onrender.com/travel.html

Перед покупкой обязательно проверьте даты, аэропорт, багаж и условия возврата.

ℹ️ Партнёрский материал: на странице есть партнёрские ссылки. Если оформить покупку после перехода по такой ссылке, мы можем получить вознаграждение; цена для пользователя от этого не увеличивается."""

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
