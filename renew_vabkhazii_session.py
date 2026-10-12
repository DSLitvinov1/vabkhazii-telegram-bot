import asyncio
from pathlib import Path

import qrcode
import requests
from telethon import TelegramClient
from telethon.errors import AuthTokenExpiredError, SessionPasswordNeededError
from telethon.sessions import StringSession

from tg_session_cache import encrypt_session

import os


API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"].strip()
BOT_TOKEN = os.environ["LEADS_BOT_TOKEN"].strip()
CHAT_ID = os.environ["LEADS_CHAT_ID"].strip()
TWOFA_PASSWORD = os.environ.get("TG_2FA_PASSWORD", "").strip()

OUT_DIR = Path(".tg_session_cache")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = OUT_DIR / "session.enc"
STATUS_FILE = Path(".ci-status/vabkhazii-session-renew.txt")
STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


def bot_call(method, data=None, files=None):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=data or {},
        files=files,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram Bot API failed: {method}")
    return payload["result"]


def send_text(text):
    return bot_call("sendMessage", {"chat_id": CHAT_ID, "text": text})


def send_qr(path):
    with path.open("rb") as handle:
        return bot_call(
            "sendPhoto",
            {
                "chat_id": CHAT_ID,
                "caption": (
                    "VAbkhazii Leads: отсканируйте QR в Telegram → Настройки → "
                    "Устройства → Подключить устройство. QR действует несколько минут."
                ),
            },
            {"photo": handle},
        )


def delete_message(message_id):
    try:
        bot_call(
            "deleteMessage",
            {"chat_id": CHAT_ID, "message_id": str(message_id)},
        )
    except Exception:
        pass


def write_status(status, detail=""):
    safe_detail = (detail or "").replace("\n", " ")[:240]
    STATUS_FILE.write_text(
        f"{status}\n{safe_detail}\n",
        encoding="utf-8",
    )


async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    qr_path = Path("vabkhazii-login-qr.png")
    qr_message_id = None

    try:
        await client.connect()
        qr = await client.qr_login()
        deadline = asyncio.get_running_loop().time() + 420
        first_qr = True

        while True:
            qrcode.make(qr.url).save(qr_path)

            if qr_message_id:
                delete_message(qr_message_id)
                qr_message_id = None

            result = send_qr(qr_path)
            qr_message_id = result.get("message_id")

            if first_qr:
                send_text(
                    "VAbkhazii Leads ждёт подтверждения входа. "
                    "Откройте QR на компьютере и отсканируйте его телефоном."
                )
                first_qr = False

            try:
                await asyncio.wait_for(qr.wait(), timeout=45)
                break
            except SessionPasswordNeededError:
                if not TWOFA_PASSWORD:
                    write_status(
                        "NEEDS_2FA",
                        "Telegram требует пароль двухэтапной аутентификации",
                    )
                    send_text(
                        "VAbkhazii Leads: Telegram запросил облачный пароль 2FA. "
                        "Сессию пока не меняю."
                    )
                    return
                await client.sign_in(password=TWOFA_PASSWORD)
                break
            except (asyncio.TimeoutError, AuthTokenExpiredError):
                if asyncio.get_running_loop().time() >= deadline:
                    write_status("TIMEOUT", "QR не был подтверждён за 7 минут")
                    send_text(
                        "VAbkhazii Leads: QR не был подтверждён вовремя. "
                        "Рабочая конфигурация не изменена."
                    )
                    return
                await qr.recreate()

        if not await client.is_user_authorized():
            write_status("UNAUTHORIZED", "Telegram не подтвердил авторизацию")
            send_text(
                "VAbkhazii Leads: Telegram не подтвердил новую сессию."
            )
            return

        me = await client.get_me()
        if getattr(me, "bot", False):
            write_status(
                "REJECTED",
                "Вместо пользовательского аккаунта авторизован бот",
            )
            send_text(
                "VAbkhazii Leads: вход отклонён — нужен пользовательский "
                "Telegram-аккаунт."
            )
            return

        session = client.session.save()
        SESSION_FILE.write_text(
            encrypt_session(session, API_HASH, BOT_TOKEN),
            encoding="utf-8",
        )

        username = getattr(me, "username", None) or ""
        write_status(
            "AUTHORIZED",
            f"user_id={getattr(me, 'id', '')}; username={username}",
        )
        send_text(
            "VAbkhazii Leads: новая Telegram-сессия создана и проверена. "
            "Сейчас запускаю полный тест и поиск."
        )

    except Exception as exc:
        write_status("ERROR", type(exc).__name__)
        try:
            send_text(
                "VAbkhazii Leads: обновление Telegram-сессии остановилось: "
                f"{type(exc).__name__}."
            )
        except Exception:
            pass

    finally:
        if qr_message_id:
            delete_message(qr_message_id)
        try:
            qr_path.unlink(missing_ok=True)
        except Exception:
            pass
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
