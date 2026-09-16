import json
import os
import sys
import urllib.parse
import urllib.request


BOT_TOKEN = os.getenv("LEADS_BOT_TOKEN", "").strip()
AUTHORIZED_CHAT_ID = os.getenv("LEADS_CHAT_ID", "").strip()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def api_request(method, data=None):
    if not BOT_TOKEN:
        raise RuntimeError("Secret LEADS_BOT_TOKEN is not configured")

    url = TELEGRAM_API.format(
        token=BOT_TOKEN,
        method=method,
    )

    encoded_data = None

    if data is not None:
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded_data,
        headers={
            "User-Agent": "VAbkhaziiLeadsBot/1.0",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result}"
        )

    return result


def send_message(chat_id, text):
    return api_request(
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
    )


def get_private_start_users():
    result = api_request(
        "getUpdates",
        {
            "limit": 100,
            "timeout": 0,
        },
    )

    users = {}

    for update in result.get("result", []):
        message = update.get("message") or {}

        chat = message.get("chat") or {}
        sender = message.get("from") or {}

        if chat.get("type") != "private":
            continue

        text = str(
            message.get("text", "")
        ).strip()

        if not text.startswith("/start"):
            continue

        chat_id = str(chat.get("id", ""))

        if not chat_id:
            continue

        users[chat_id] = {
            "chat_id": chat_id,
            "username": sender.get("username", ""),
            "first_name": sender.get("first_name", ""),
            "last_name": sender.get("last_name", ""),
        }

    return list(users.values())


def print_setup_information():
    users = get_private_start_users()

    print("")
    print("=" * 60)
    print("VABKHAZII LEADS BOT — PRIVATE CHAT SETUP")
    print("=" * 60)

    if not users:
        print("")
        print("No private /start messages found.")
        print("")
        print("Open @VAbkhaziiLeadsBot in Telegram")
        print("and press START, then run this workflow again.")
        print("")
        return

    print("")
    print("Private users who pressed START:")
    print("")

    for index, user in enumerate(users, start=1):
        username = user["username"]
        first_name = user["first_name"]
        last_name = user["last_name"]

        name = " ".join(
            part
            for part in [first_name, last_name]
            if part
        )

        print(f"{index}.")
        print(f"   Name: {name or '-'}")
        print(
            f"   Username: "
            f"@{username if username else '-'}"
        )
        print(
            f"   TELEGRAM CHAT ID: "
            f"{user['chat_id']}"
        )
        print("")

    print("=" * 60)
    print("")
    print(
        "Copy YOUR TELEGRAM CHAT ID and create "
        "GitHub secret LEADS_CHAT_ID."
    )
    print("")


def verify_authorized_chat():
    if not AUTHORIZED_CHAT_ID:
        print_setup_information()
        return

    text = (
        "✅ <b>ВАбхазии | Лиды подключён</b>\n\n"
        "Личный канал связи с ботом работает.\n\n"
        "🔐 Лиды будут отправляться только "
        "в этот личный Telegram-чат.\n\n"
        "Следующий этап — подключение поиска "
        "потенциальных туристов."
    )

    send_message(
        AUTHORIZED_CHAT_ID,
        text,
    )

    print("")
    print("Private Telegram connection verified.")
    print("Test message sent successfully.")
    print("")


def main():
    try:
        verify_authorized_chat()

    except Exception as exc:
        print("")
        print("ERROR:")
        print(str(exc))
        print("")
        sys.exit(1)


if __name__ == "__main__":
    main()
