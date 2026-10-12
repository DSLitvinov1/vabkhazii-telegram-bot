"""Read-only, user-authorized Telegram account diagnostic for missed screenshot.

No messaging, joining chats, inviting people or scraping of private group content.
Find public group titles and explicit golden text using allowed Telegram API.
Only output public URLs and aggregate counts, not private chat metadata.
"""
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.functions.contacts import SearchRequest
from session_compat import normalize_tg_session
from classifier import score

TARGET_PHRASES = (
    "Ищу логопеда для дочери",
    "Отсутствует звук Р",
    "Ищу логопеда",
)
TARGET_GROUP_NAMES = (
    "Русскоязычный Таиланд",
    "Русскоязычные Таиланд",
    "Русскоязычный Тайланд",
    "Русские в Таиланде",
)
CUTOFF_HOURS = 72


def is_target_group(title):
    title = (title or "").casefold().replace("й", "и").replace("ё", "е")
    return "таиланд" in title or "таиланд" in title or "таиланд" in title


async def main():
    api_id=int(os.environ["TG_API_ID"])
    api_hash=os.environ["TG_API_HASH"]
    session=normalize_tg_session(os.environ.get("TG_SESSION",""))
    if not session:raise RuntimeError("SESSION_NOT_CONFIGURED")
    client=TelegramClient(StringSession(session),api_id,api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():raise RuntimeError("SESSION_NOT_AUTHORIZED")
        cutoff=datetime.now(timezone.utc)-timedelta(hours=CUTOFF_HOURS)
        result={
            "authorized": True,
            "lookback_hours": CUTOFF_HOURS,
            "joined_dialogs_checked": 0,
            "target_named_dialogs_found": 0,
            "public_target_dialogs": [],
            "global_phrase_matches": 0,
            "global_qualified_public_matches": [],
            "discovery_titles": [],
        }
        # A screenshot does not establish which Telegram account sees that chat.
        # Distinguish absent membership from a broken classifier.
        async for dialog in client.iter_dialogs(limit=220):
            result["joined_dialogs_checked"]+=1
            entity=dialog.entity
            title=getattr(dialog,"name","") or ""
            if is_target_group(title) and not getattr(entity,"broadcast",False):
                result["target_named_dialogs_found"]+=1
                public_user=getattr(entity,"username",None)
                if public_user:
                    result["public_target_dialogs"].append("@"+public_user)
        for query in TARGET_GROUP_NAMES:
            try:
                found=await client(SearchRequest(q=query,limit=40))
                for entity in found.chats:
                    username=getattr(entity,"username",None)
                    title=(getattr(entity,"title","") or "")
                    if username and is_target_group(title) and not getattr(entity,"broadcast",False):
                        label="@"+username
                        if label not in result["discovery_titles"]:
                            result["discovery_titles"].append(label)
            except FloodWaitError as exc:
                result["flood_wait_seconds"]=exc.seconds
                break
        for query in TARGET_PHRASES:
            try:
                async for msg in client.iter_messages(None, search=query, limit=45):
                    if not msg.date or msg.date<cutoff:
                        break
                    if not msg.message:
                        continue
                    lower=msg.message.casefold()
                    # Exact 7-year-old / sound R screenshot phrase, not random search results.
                    if query.casefold() not in lower:
                        continue
                    result["global_phrase_matches"]+=1
                    chat=await msg.get_chat()
                    name=(getattr(chat,"title",None) or "")
                    username=getattr(chat,"username",None)
                    points,_=score(msg.message)
                    if username and not getattr(chat,"broadcast",False) and points>=60:
                        result["global_qualified_public_matches"].append({
                            "url":f"https://t.me/{username}/{msg.id}",
                            "date":msg.date.isoformat(),
                            "score":points,
                            "matching_target_name":is_target_group(name),
                        })
            except FloodWaitError as exc:
                result["flood_wait_seconds"]=exc.seconds
                break
        print("GOLDEN_SOURCE_DIAGNOSTIC", json.dumps(result,ensure_ascii=False))
    finally:
        await client.disconnect()


if __name__=="__main__":
    asyncio.run(main())
