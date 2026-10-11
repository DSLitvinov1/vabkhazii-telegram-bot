"""Read-only audit of specific publicly accessible Thailand parent chats."""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.errors import FloodWaitError
from session_compat import normalize_tg_session
from classifier import score

SEARCH_TITLES = [
    'Русскоязычный Таиланд',
    'Русскоязычные Таиланд',
    'русские в Таиланде',
    'Паттайя русскоязычный чат',
    'мамы Таиланд',
    'родители Паттайя',
]
SEARCH_WORDS = ('логопед', 'дефектолог', 'речь', 'звук р')
MAX_CHATS = 14


async def main():
    raw_session = normalize_tg_session(os.getenv('TG_SESSION', ''))
    api_id = int(os.environ['TG_API_ID'])
    api_hash = os.environ['TG_API_HASH']
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    client = TelegramClient(__import__('telethon').sessions.StringSession(raw_session), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError('Telegram user session not authorized')
        candidates = {}
        for query in SEARCH_TITLES:
            try:
                result = await client(SearchRequest(q=query, limit=40))
                for chat in result.chats:
                    username = getattr(chat,'username',None)
                    title = getattr(chat,'title','') or ''
                    if not username or getattr(chat,'broadcast',False):
                        continue
                    if username.lower() not in candidates:
                        candidates[username.lower()] = {'username': username, 'title': title}
            except FloodWaitError as e:
                print('THAILAND_GROUP_SEARCH_WAIT',e.seconds)
                break
            except Exception as e:
                print('THAILAND_GROUP_SEARCH_ERROR',type(e).__name__)
        ranked = sorted(candidates.values(), key=lambda x: (
            0 if 'русскоязыч' in x['title'].lower() and 'таиланд' in x['title'].lower() else 1,
            0 if 'таиланд' in x['title'].lower() or 'тайланд' in x['title'].lower() else 1
        ))
        stats = {'discovered_public_chats':len(candidates),'checked_chats':0,
                 'checked_messages':0,'matches':0,'valid_leads':0,'public_chat_index':[]}
        for chat in ranked[:MAX_CHATS]:
            username=chat['username']
            checked=set()
            chat_counts={'group':'@'+username,'title':chat['title'][:90],
                         'matched_messages':0,'qualified':0}
            try:
                for term in SEARCH_WORDS:
                    async for msg in client.iter_messages(username,search=term,limit=45):
                        if msg.id in checked or not msg.message or not msg.date:
                            continue
                        if msg.date<cutoff:
                            break
                        checked.add(msg.id)
                        score_num, reasons = score(msg.message)
                        stats['checked_messages']+=1
                        chat_counts['matched_messages']+=1
                        if score_num>=60:
                            stats['valid_leads']+=1
                            chat_counts['qualified']+=1
                            print('QUALIFIED_PUBLIC_THAILAND_LEAD',json.dumps({
                                'link':f'https://t.me/{username}/{msg.id}',
                                'score':score_num,'date':msg.date.isoformat()
                            },ensure_ascii=False))
                stats['checked_chats']+=1
            except FloodWaitError as e:
                print('THAILAND_GROUP_WAIT', e.seconds)
                break
            except Exception as e:
                chat_counts['error']=type(e).__name__
            stats['matches']+=chat_counts['matched_messages']
            stats['public_chat_index'].append(chat_counts)
        print('THAILAND_PUBLIC_GROUP_AUDIT',json.dumps(stats,ensure_ascii=False))
    finally:
        await client.disconnect()


if __name__=='__main__':
    asyncio.run(main())
