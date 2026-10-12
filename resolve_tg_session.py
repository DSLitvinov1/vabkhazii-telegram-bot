import os
from pathlib import Path

from telethon.sessions import StringSession

from tg_session_cache import decrypt_session


CACHE_FILE = Path(".tg_session_cache/session.enc")


def main():
    api_hash = os.environ["TG_API_HASH"].strip()
    bot_token = os.environ["LEADS_BOT_TOKEN"].strip()
    fallback = os.environ.get("TG_SESSION_FALLBACK", "").strip()

    session = ""
    source = ""

    if CACHE_FILE.exists():
        try:
            session = decrypt_session(
                CACHE_FILE.read_text(encoding="utf-8").strip(),
                api_hash,
                bot_token,
            ).strip()
            source = "encrypted-cache"
        except Exception as exc:
            print("Encrypted TG session cache could not be decrypted:", type(exc).__name__)

    if not session and fallback:
        session = fallback
        source = "github-secret-fallback"

    if not session:
        raise RuntimeError("No usable Telegram user session is available")

    StringSession(session)

    print(f"Telegram session source: {source}")
    print(f"::add-mask::{session}")

    env_file = os.environ.get("GITHUB_ENV")
    if not env_file:
        raise RuntimeError("GITHUB_ENV is unavailable")

    with open(env_file, "a", encoding="utf-8") as handle:
        handle.write("TG_SESSION=" + session + "\n")


if __name__ == "__main__":
    main()
