import asyncio, hashlib, html, json, os, re, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import User
from classifier import score, norm
from card import build
from web_sources import collect_web
from sources import scan_chat, merge_unique
TG_API_ID=int(os.environ.get("TG_API_ID","0")); TG_API_HASH=os.environ.get("TG_API_HASH",""); TG_SESSION=os.environ.get("TG_SESSION","")
BOT_TOKEN=os.environ.get("LEADS_BOT_TOKEN",""); CHAT_ID=os.environ.get("LEADS_CHAT_ID","")
STATE_VERSION=2
STATE_DIR=Path('.lead_state'); STATE_FILE=STATE_DIR/'state.json'
MAX_AGE_HOURS=int(os.environ.get("MAX_AGE_HOURS","72")); SEARCH_LIMIT=40; MAX_LEADS_PER_RUN=int(os.environ.get("MAX_LEADS_PER_RUN","25")); MIN_SCORE=int(os.environ.get("MIN_SCORE","35"))
ENABLE_WEB=os.environ.get('ENABLE_WEB','0').strip().lower() in {'1','true','yes','on'}
SEARCH_QUERIES=[
 "ищу логопеда","нужен логопед ребенку","посоветуйте логопеда","логопед онлайн",
 "ребенок не говорит логопед","не выговаривает р логопед","не выговаривает л логопед",
 "запуск речи логопед","ЗРР логопед","нужен дефектолог","дисграфия логопед","дислексия логопед"]
def load_state():
 STATE_DIR.mkdir(exist_ok=True)
 try:
  st=json.loads(STATE_FILE.read_text('utf-8'))
  if st.get('version')==STATE_VERSION:return st
 except Exception:pass
 return {'version':STATE_VERSION,'seen':[]}
def save_state(st):
 st['version']=STATE_VERSION
 STATE_FILE.write_text(json.dumps(st,ensure_ascii=False,indent=2),'utf-8')
def key(chat_id,msg_id): return hashlib.sha256(f'{chat_id}:{msg_id}'.encode()).hexdigest()
async def notify(text):
 if not BOT_TOKEN or not CHAT_ID:
  print('DRY_SEND',text.encode('ascii','backslashreplace').decode()[:300]); return
 data=urllib.parse.urlencode({'chat_id':CHAT_ID,'text':text,'disable_web_page_preview':'true'}).encode()
 req=urllib.request.Request(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',data=data)
 await asyncio.to_thread(urllib.request.urlopen,req,timeout=20)
async def main():
 if not (TG_API_ID and TG_API_HASH and TG_SESSION): raise RuntimeError('Missing Telegram user credentials')
 if not (BOT_TOKEN and CHAT_ID): raise RuntimeError('Missing Telegram bot delivery credentials')
 st=load_state(); seen=set(st.get('seen',[])); found=[]
 client=TelegramClient(StringSession(TG_SESSION),TG_API_ID,TG_API_HASH)
 await client.connect()
 if not await client.is_user_authorized(): raise RuntimeError('TG_SESSION not authorized')
 cutoff=datetime.now(timezone.utc)-timedelta(hours=MAX_AGE_HOURS)
 # True Telegram global message search (ported from the proven production lead bot).
 for q in SEARCH_QUERIES:
  try:
   async for m in client.iter_messages(None,search=q,limit=SEARCH_LIMIT):
    if not m.message or not m.date or m.date<cutoff: continue
    chat=await m.get_chat(); chat_id=getattr(chat,'id',0); k=key(chat_id,m.id)
    if k in seen: continue
    seen.add(k); sc,why=score(m.message)
    if sc<MIN_SCORE: continue
    username=getattr(chat,'username',None); url=f'https://t.me/{username}/{m.id}' if username else ''
    found.append((sc,m.date,m.message,url,why,'Telegram'))
  except FloodWaitError as e:
   if e.seconds<=60: await asyncio.sleep(e.seconds+1)
   else: print('GLOBAL_FLOOD_WAIT',e.seconds); break
  except Exception as e: print('GLOBAL_WARN',q,type(e).__name__)
 discovered=await discover_public_groups(client)
 print('DISCOVERED_GROUPS',len(discovered))
 for chat in discovered:
  try:
   async for m in client.iter_messages(chat,limit=80):
    if not m.message or not m.date or m.date<cutoff: continue
    k=key(getattr(chat,'id',0),m.id)
    if k in seen: continue
    seen.add(k); sc,why=score(m.message)
    if sc<MIN_SCORE: continue
    username=getattr(chat,'username',None); url=f'https://t.me/{username}/{m.id}' if username else ''
    found.append((sc,m.date,m.message,url,why,'Telegram'))
  except Exception as e: print('SCAN_WARN',getattr(chat,'title','?'),type(e).__name__)
 found=merge_unique(found)
 found=[x for x in found if x[0]>=MIN_SCORE]
 # Public web index sources are opt-in until publication-time validation is reliable.
 try:
  for item in (await asyncio.to_thread(collect_web) if ENABLE_WEB else []):
   k=hashlib.sha256(item['url'].encode()).hexdigest()
   if k in seen: continue
   seen.add(k); sc,why=score(item['text'])
   if sc<MIN_SCORE: continue
   found.append((sc,datetime.now(timezone.utc),item['text'],item['url'],why,item.get('source','Web')))
 except Exception as e: print('WEB_SCAN_WARN',type(e).__name__)
 found.sort(key=lambda x:(x[0],x[1]),reverse=True)
 for sc,dt,msg,url,why,source in found[:MAX_LEADS_PER_RUN]:
  published=dt.strftime('%d.%m %H:%M UTC') if source=='Telegram' else None
  card=build(msg,url,source,sc,why,published)
  await notify(card)
 st['seen']=list(seen)[-15000:]; save_state(st); await client.disconnect()
 print('FOUND',len(found),'SENT',min(len(found),MAX_LEADS_PER_RUN))
# Public-group discovery: only publicly searchable Telegram groups; no auto-join.
DISCOVERY_QUERIES=[
 'логопед родители чат','мамы дети развитие речи','запуск речи родители',
 'ЗРР родители чат','детский сад родители чат','подготовка к школе родители',
 'дисграфия родители','дислексия родители','дефектолог родители']
COMMERCIAL_CHAT_MARKERS=['услуги логопеда','логопедический центр','школа логопеда','курсы логопедов','вакансии логопед']
async def discover_public_groups(client):
 groups={}
 for q in DISCOVERY_QUERIES:
  try:
   result=await client(SearchRequest(q=q,limit=20))
   for chat in result.chats:
    title=(getattr(chat,'title','') or '').lower()
    username=getattr(chat,'username',None)
    if not username or getattr(chat,'broadcast',False): continue
    if any(x in title for x in COMMERCIAL_CHAT_MARKERS): continue
    groups[getattr(chat,'id',username)]=chat
  except FloodWaitError as e:
   if e.seconds<=60: await asyncio.sleep(e.seconds+1)
   else: print('DISCOVERY_FLOOD_WAIT',e.seconds); break
  except Exception as e: print('DISCOVERY_WARN',q,type(e).__name__)
 return list(groups.values())[:25]

if __name__=='__main__': asyncio.run(main())
