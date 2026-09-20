import asyncio, json, os, urllib.parse, urllib.request, urllib.error
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User

TG_API_ID=int(os.environ.get('TG_API_ID','0'))
TG_API_HASH=os.environ.get('TG_API_HASH','')
TG_SESSION=os.environ.get('TG_SESSION','')
BOT_TOKEN=os.environ.get('LOGOLEAD_BOT_TOKEN') or os.environ.get('LEADS_BOT_TOKEN','')
TARGET_USERNAME=(os.environ.get('TARGET_USERNAME') or '').strip().lstrip('@')

def bot_get_chat(bot_token,chat_id):
    url=f'https://api.telegram.org/bot{bot_token}/getChat?'+urllib.parse.urlencode({'chat_id':chat_id})
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            payload=json.loads(exc.read().decode('utf-8','ignore'))
        except Exception:
            payload={'ok':False,'description':f'HTTP {exc.code}'}
        return payload

async def main():
    if not (TG_API_ID and TG_API_HASH and TG_SESSION and BOT_TOKEN and TARGET_USERNAME):
        raise RuntimeError('Missing target-check credentials or username')
    client=TelegramClient(StringSession(TG_SESSION),TG_API_ID,TG_API_HASH)
    await client.connect()
    try:
        entity=await client.get_entity(TARGET_USERNAME)
        if not isinstance(entity,User):
            raise RuntimeError('Target username is not a Telegram user')
        chat_id=int(entity.id)
        result=await asyncio.to_thread(bot_get_chat,BOT_TOKEN,chat_id)
        ready=bool(result.get('ok'))
        print('TARGET_USERNAME=@'+TARGET_USERNAME)
        print('TARGET_READY='+('1' if ready else '0'))
        if ready:
            print('TARGET_CHAT_ID='+str(chat_id))
        else:
            description=str(result.get('description') or 'chat unavailable')
            print('TARGET_REASON='+description[:200])
    finally:
        await client.disconnect()

if __name__=='__main__':
    asyncio.run(main())
