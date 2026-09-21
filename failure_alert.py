import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

import lead_bot


async def main():
    text = os.environ.get("FAILURE_MESSAGE", "").strip()
    if not text:
        print("Failure alert skipped: FAILURE_MESSAGE is empty")
        return 0

    if not lead_bot.TG_SESSION:
        print("Saved Messages alert skipped: TG_SESSION is unavailable")
        return 1

    client = TelegramClient(
        StringSession(lead_bot.TG_SESSION),
        lead_bot.TG_API_ID,
        lead_bot.TG_API_HASH,
    )

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Saved Messages alert skipped: TG_SESSION is not authorized")
            return 1

        await client.send_message(
            "me",
            text,
            link_preview=False,
        )
        print("Failure alert delivered to Telegram Saved Messages")
        return 0
    except Exception as exc:
        print(f"Saved Messages failure alert failed: {type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
