import asyncio, hashlib, json, os, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from classifier import score
from card import build
from web_sources import collect_web
from market_sources import collect_markets
from sources import merge_unique

TG_API_ID=int(os.environ.get('TG_API_ID','0'))
TG_API_HASH=os.environ.get('TG_API_HASH','')
TG_SESSION=os.environ.get('TG_SESSION','')
BOT_TOKEN=os.environ.get('LEADS_BOT_TOKEN','')
CHAT_ID=os.environ.get('LEADS_CHAT_ID','')

STATE_VERSION=3
CLASSIFIER_VERSION=5
STATE_DIR=Path('.lead_state')
STATE_FILE=STATE_DIR/'state.json'
MAX_AGE_HOURS=int(os.environ.get('MAX_AGE_HOURS','72'))
SEARCH_LIMIT=int(os.environ.get('SEARCH_LIMIT','40'))
MAX_LEADS_PER_RUN=int(os.environ.get('MAX_LEADS_PER_RUN','25'))
MIN_SCORE=int(os.environ.get('MIN_SCORE','35'))
RUN_INTERVAL_MINUTES=int(os.environ.get('RUN_INTERVAL_MINUTES','10'))
DISCOVERY_INTERVAL_MINUTES=int(os.environ.get('DISCOVERY_INTERVAL_MINUTES','360'))
GROUP_SCAN_LIMIT=int(os.environ.get('GROUP_SCAN_LIMIT','80'))
INITIAL_GROUP_SCAN_LIMIT=int(os.environ.get('INITIAL_GROUP_SCAN_LIMIT','180'))
MAX_DISCOVERED_GROUPS=int(os.environ.get('MAX_DISCOVERED_GROUPS','30'))
GROUP_CACHE_LIMIT=int(os.environ.get('GROUP_CACHE_LIMIT','120'))
DEEP_GROUP_INTERVAL_MINUTES=int(os.environ.get('DEEP_GROUP_INTERVAL_MINUTES','180'))
DEEP_GROUP_SCAN_COUNT=int(os.environ.get('DEEP_GROUP_SCAN_COUNT','6'))
DEEP_GROUP_SEARCH_LIMIT=int(os.environ.get('DEEP_GROUP_SEARCH_LIMIT','15'))
WEB_INTERVAL_MINUTES=int(os.environ.get('WEB_INTERVAL_MINUTES','60'))
MARKET_INTERVAL_MINUTES=int(os.environ.get('MARKET_INTERVAL_MINUTES','30'))
ENABLE_WEB=os.environ.get('ENABLE_WEB','0').strip().lower() in {'1','true','yes','on'}
ENABLE_MARKETS=os.environ.get('ENABLE_MARKETS','1').strip().lower() in {'1','true','yes','on'}
FORCE_RUN=os.environ.get('FORCE_RUN','0').strip().lower() in {'1','true','yes','on'}
SEND_STATUS=os.environ.get('SEND_STATUS','0').strip().lower() in {'1','true','yes','on'}
STATUS_INTERVAL_HOURS=int(os.environ.get('STATUS_INTERVAL_HOURS','24'))
BUILD_SHA=os.environ.get('GITHUB_SHA','local')[:7]

SEARCH_QUERIES=[
    'ищу логопеда','ищем логопеда','нужен логопед','логопед нужен',
    'нужен логопед ребенку','нужен логопед ребёнку','логопед ребенку','логопед ребёнку',
    'посоветуйте логопеда','порекомендуйте логопеда','подскажите логопеда',
    'кто-нибудь знает логопеда','кто знает логопеда','хороший логопед',
    'где найти логопеда','контакты логопеда','логопед для ребенка','логопед для ребёнка',
    'логопед онлайн','ищу логопеда онлайн','нужен дефектолог','дефектолог нужен',
    'посоветуйте дефектолога','порекомендуйте дефектолога','нужен нейрологопед',
    'ребенок не говорит','ребёнок не говорит','не говорит предложениями',
    'плохо говорит ребенок','плохо говорит ребёнок','не выговаривает р',
    'не выговаривает л','не выговаривает звуки','запуск речи','ЗРР логопед',
    'ЗПРР логопед','дисграфия логопед','дислексия логопед',
    'логопед','дефектолог','нейрологопед',
]
DISCOVERY_QUERIES=[
    'логопед родители чат','мамы дети развитие речи','запуск речи родители',
    'ЗРР родители чат','ЗПРР родители чат','дефектолог родители',
    'детский сад родители чат','подготовка к школе родители',
    'мамы дошкольников чат','мамочки чат дети','родители дети чат',
    'особенные дети родители','развитие детей родители чат',
    'мамы москва чат','мамы спб чат','мамы краснодар чат','мамы сочи чат',
    'мамы казань чат','мамы екатеринбург чат','мамы новосибирск чат','мамы красноярск чат',
    'мамы самара чат','мамы уфа чат','мамы ростов чат','мамы воронеж чат','мамы пермь чат',
    'мамы тюмень чат','мамы челябинск чат','мамы нижний новгород чат','мамы омск чат',
    'мамы волгоград чат','мамы минск чат','мамы алматы чат','мамы астана чат',
]
DEEP_GROUP_QUERIES=['логопед','дефектолог','нейрологопед','не говорит','не выговаривает','зрр','зпрр','картавит','шепелявит','заикается','задержка речи','запуск речи','дисграфия']
COMMERCIAL_CHAT_MARKERS=[
    'услуги логопеда','логопедический центр','школа логопеда',
    'курсы логопедов','вакансии логопед','обучение логопедов',
]

def load_state():
    STATE_DIR.mkdir(exist_ok=True)
    try:
        state=json.loads(STATE_FILE.read_text('utf-8'))
        if not isinstance(state,dict): raise ValueError('bad state')
    except Exception:
        state={}
    state.setdefault('seen',[])
    state.setdefault('sent',[])
    state.setdefault('groups',{})
    state.setdefault('group_last_ids',{})
    if state.get('classifier_version')!=CLASSIFIER_VERSION:
        state['seen']=[]
        state['group_last_ids']={}
        state['classifier_version']=CLASSIFIER_VERSION
    state['version']=STATE_VERSION
    return state

def save_state(state):
    state['version']=STATE_VERSION
    STATE_FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2),'utf-8')

def message_key(chat_id,msg_id):
    return hashlib.sha256(f'{chat_id}:{msg_id}'.encode()).hexdigest()

def delivery_key(url,text):
    basis=('url:'+url.strip()) if url else ('text:'+' '.join((text or '').lower().split())[:1200])
    return hashlib.sha256(basis.encode()).hexdigest()

async def notify(text):
    if not BOT_TOKEN or not CHAT_ID:
        print('DRY_SEND',text.encode('ascii','backslashreplace').decode()[:400])
        return
    data=urllib.parse.urlencode({
        'chat_id':CHAT_ID,
        'text':text,
        'disable_web_page_preview':'true',
    }).encode()
    req=urllib.request.Request(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',data=data)
    def send():
        with urllib.request.urlopen(req,timeout=20) as response:
            response.read(2000)
    await asyncio.to_thread(send)

async def discover_public_groups(client,state,now):
    cached=state.get('groups') or {}
    due=FORCE_RUN or not cached or not state.get('last_discovery')
    if cached and not FORCE_RUN and state.get('last_discovery'):
        try:
            due=now-datetime.fromisoformat(state['last_discovery'])>=timedelta(minutes=DISCOVERY_INTERVAL_MINUTES)
        except Exception:
            due=True
    if not due:
        print('DISCOVERY_CACHE',len(cached))
        return cached

    keep=max(0,GROUP_CACHE_LIMIT-40)
    groups=dict(list(cached.items())[:keep])
    for query in DISCOVERY_QUERIES:
        try:
            result=await client(SearchRequest(q=query,limit=20))
            for chat in result.chats:
                title=(getattr(chat,'title','') or '').strip()
                low=title.lower()
                username=getattr(chat,'username',None)
                if not username or getattr(chat,'broadcast',False):
                    continue
                if any(marker in low for marker in COMMERCIAL_CHAT_MARKERS):
                    continue
                groups[username]=title or username
                if len(groups)>=GROUP_CACHE_LIMIT:
                    break
        except FloodWaitError as exc:
            if exc.seconds<=60:
                await asyncio.sleep(exc.seconds+1)
            else:
                print('DISCOVERY_FLOOD_WAIT',exc.seconds)
                break
        except Exception as exc:
            print('DISCOVERY_WARN',query,type(exc).__name__)
        if len(groups)>=GROUP_CACHE_LIMIT:
            break

    if groups:
        state['groups']=groups
    state['last_discovery']=now.isoformat()
    print('DISCOVERED_GROUPS',len(state.get('groups') or {}))
    return state.get('groups') or {}

async def main():
    if not (TG_API_ID and TG_API_HASH and TG_SESSION):
        raise RuntimeError('Missing Telegram user credentials')
    if not (BOT_TOKEN and CHAT_ID):
        raise RuntimeError('Missing Telegram bot delivery credentials')

    state=load_state()
    seen=dict.fromkeys(state.get('seen',[]))
    sent_keys=dict.fromkeys(state.get('sent',[]))
    found=[]
    seed_groups={}
    stats={'global_checked':0,'global_candidates':0,'group_checked':0,'group_candidates':0,'deep_checked':0,'deep_candidates':0,'market_checked':0,'market_candidates':0,'web_checked':0,'web_candidates':0}
    reject_counts={}
    query_hits={}
    score_hist={}
    signal_combos={}
    now=datetime.now(timezone.utc)

    def record_score(value,reasons):
        key=str(value)
        score_hist[key]=score_hist.get(key,0)+1
        combo=' + '.join(reasons) if reasons else 'нет сигналов'
        signal_combos[combo]=signal_combos.get(combo,0)+1

    if not FORCE_RUN and RUN_INTERVAL_MINUTES>0 and state.get('last_run'):
        try:
            last=datetime.fromisoformat(state['last_run'])
            if now-last<timedelta(minutes=RUN_INTERVAL_MINUTES-1):
                print('SKIP_INTERVAL',state['last_run'])
                return
        except Exception:
            pass

    client=TelegramClient(StringSession(TG_SESSION),TG_API_ID,TG_API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError('TG_SESSION not authorized')

    cutoff=now-timedelta(hours=MAX_AGE_HOURS)

    for query in SEARCH_QUERIES:
        try:
            async for message in client.iter_messages(None,search=query,limit=SEARCH_LIMIT):
                if not message.message or not message.date:
                    continue
                if message.date<cutoff:
                    break
                chat=await message.get_chat()
                stats['global_checked']+=1
                query_hits[query]=query_hits.get(query,0)+1
                username=getattr(chat,'username',None)
                title=getattr(chat,'title',None) or username or 'public'
                low_title=(title or '').lower()
                if username and not getattr(chat,'broadcast',False) and not any(x in low_title for x in COMMERCIAL_CHAT_MARKERS):
                    seed_groups[username]=title or username
                chat_id=getattr(chat,'id',0)
                key=message_key(chat_id,message.id)
                if key in seen:
                    continue
                seen[key]=None
                if not username:
                    reject_counts['нет публичной ссылки']=reject_counts.get('нет публичной ссылки',0)+1
                    continue
                value,reasons=score(message.message)
                record_score(value,reasons)
                if value<MIN_SCORE:
                    reason=reasons[0] if reasons else f'score<{MIN_SCORE}'
                    reject_counts[reason]=reject_counts.get(reason,0)+1
                    continue
                url=f'https://t.me/{username}/{message.id}' if username else ''
                sent_key=delivery_key(url,message.message)
                if sent_key in sent_keys:
                    continue
                stats['global_candidates']+=1
                found.append((value,message.date,message.message,url,reasons,f'Telegram: {title}',key,sent_key))
        except FloodWaitError as exc:
            if exc.seconds<=60:
                await asyncio.sleep(exc.seconds+1)
            else:
                print('GLOBAL_FLOOD_WAIT',exc.seconds)
                break
        except Exception as exc:
            print('GLOBAL_WARN',query,type(exc).__name__)

    if seed_groups:
        merged_groups=dict(seed_groups)
        merged_groups.update(state.get('groups') or {})
        state['groups']=merged_groups
    print('GLOBAL_STATS',stats['global_checked'],stats['global_candidates'],'SEED_GROUPS',len(seed_groups))
    groups=await discover_public_groups(client,state,now)
    group_last_ids=state.get('group_last_ids') or {}

    all_groups=list(groups.items())
    priority=[item for item in all_groups if item[0] in seed_groups]
    priority_names={item[0] for item in priority}
    others=[item for item in all_groups if item[0] not in priority_names]
    remaining=max(0,MAX_DISCOVERED_GROUPS-len(priority))
    cursor=int(state.get('group_scan_cursor',0) or 0)
    rotated=[]
    if others and remaining:
        count=min(remaining,len(others))
        rotated=[others[(cursor+i)%len(others)] for i in range(count)]
        state['group_scan_cursor']=(cursor+count)%len(others)
    selected_groups=(priority+rotated)[:MAX_DISCOVERED_GROUPS]
    print('GROUP_SCAN_SET',len(selected_groups),'PRIORITY',len(priority),'CACHE',len(all_groups),'CURSOR',state.get('group_scan_cursor',0))

    for username,title in selected_groups:
        min_id=int(group_last_ids.get(username,0) or 0)
        newest_id=min_id
        try:
            scan_limit=INITIAL_GROUP_SCAN_LIMIT if min_id==0 else GROUP_SCAN_LIMIT
            async for message in client.iter_messages(username,limit=scan_limit,min_id=min_id):
                newest_id=max(newest_id,message.id)
                if not message.message or not message.date:
                    continue
                if message.date<cutoff:
                    break
                stats['group_checked']+=1
                key=message_key(username,message.id)
                if key in seen:
                    continue
                seen[key]=None
                value,reasons=score(message.message)
                record_score(value,reasons)
                if value<MIN_SCORE:
                    reason=reasons[0] if reasons else f'score<{MIN_SCORE}'
                    reject_counts[reason]=reject_counts.get(reason,0)+1
                    continue
                url=f'https://t.me/{username}/{message.id}'
                sent_key=delivery_key(url,message.message)
                if sent_key in sent_keys:
                    continue
                stats['group_candidates']+=1
                found.append((value,message.date,message.message,url,reasons,f'Telegram: {title or username}',key,sent_key))
            if newest_id>min_id:
                group_last_ids[username]=newest_id
        except FloodWaitError as exc:
            if exc.seconds<=60:
                await asyncio.sleep(exc.seconds+1)
            else:
                print('GROUP_FLOOD_WAIT',username,exc.seconds)
                break
        except Exception as exc:
            print('SCAN_WARN',username,type(exc).__name__)

    state['group_last_ids']=group_last_ids

    deep_due=FORCE_RUN or not state.get('last_deep_scan')
    if not FORCE_RUN and state.get('last_deep_scan'):
        try:
            deep_due=now-datetime.fromisoformat(state['last_deep_scan'])>=timedelta(minutes=DEEP_GROUP_INTERVAL_MINUTES)
        except Exception:
            deep_due=True
    if deep_due and all_groups:
        deep_cursor=int(state.get('deep_group_cursor',0) or 0)
        deep_count=min(DEEP_GROUP_SCAN_COUNT,len(all_groups))
        deep_groups=[all_groups[(deep_cursor+i)%len(all_groups)] for i in range(deep_count)]
        state['deep_group_cursor']=(deep_cursor+deep_count)%len(all_groups)
        print('DEEP_SCAN_SET',len(deep_groups),'CURSOR',state['deep_group_cursor'])
        stop_deep=False
        for username,title in deep_groups:
            if stop_deep:
                break
            for query in DEEP_GROUP_QUERIES:
                try:
                    async for message in client.iter_messages(username,search=query,limit=DEEP_GROUP_SEARCH_LIMIT):
                        if not message.message or not message.date:
                            continue
                        if message.date<cutoff:
                            break
                        stats['deep_checked']+=1
                        key=message_key(username,message.id)
                        if key in seen:
                            continue
                        seen[key]=None
                        value,reasons=score(message.message)
                        record_score(value,reasons)
                        if value<MIN_SCORE:
                            reason=reasons[0] if reasons else f'score<{MIN_SCORE}'
                            reject_counts[reason]=reject_counts.get(reason,0)+1
                            continue
                        url=f'https://t.me/{username}/{message.id}'
                        sent_key=delivery_key(url,message.message)
                        if sent_key in sent_keys:
                            continue
                        stats['deep_candidates']+=1
                        found.append((value,message.date,message.message,url,reasons,f'Telegram: {title or username}',key,sent_key))
                except FloodWaitError as exc:
                    if exc.seconds<=60:
                        await asyncio.sleep(exc.seconds+1)
                    else:
                        print('DEEP_FLOOD_WAIT',username,exc.seconds)
                        stop_deep=True
                        break
                except Exception as exc:
                    print('DEEP_SCAN_WARN',username,query,type(exc).__name__)
        state['last_deep_scan']=datetime.now(timezone.utc).isoformat()

    found=merge_unique(found)
    found=[item for item in found if item[0]>=MIN_SCORE]

    market_due=ENABLE_MARKETS
    if market_due and not FORCE_RUN and state.get('last_market_run'):
        try:
            market_due=now-datetime.fromisoformat(state['last_market_run'])>=timedelta(minutes=MARKET_INTERVAL_MINUTES)
        except Exception:
            market_due=True
    try:
        market_items=await asyncio.to_thread(collect_markets,MAX_AGE_HOURS) if market_due else []
        print('MARKET_ITEMS',len(market_items))
        for item in market_items:
            stats['market_checked']+=1
            key=hashlib.sha256(item['url'].encode()).hexdigest()
            if key in seen:
                continue
            seen[key]=None
            value,reasons=score(item['text'])
            record_score(value,reasons)
            if value<MIN_SCORE:
                reason=reasons[0] if reasons else f'score<{MIN_SCORE}'
                reject_counts[reason]=reject_counts.get(reason,0)+1
                continue
            sent_key=delivery_key(item['url'],item['text'])
            if sent_key in sent_keys:
                continue
            stats['market_candidates']+=1
            published=item.get('published') or datetime.now(timezone.utc)
            found.append((value,published,item['text'],item['url'],reasons,item.get('source','Marketplace'),key,sent_key))
        if market_due:
            state['last_market_run']=datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        print('MARKET_SCAN_WARN',type(exc).__name__)

    web_due=ENABLE_WEB
    if web_due and not FORCE_RUN and state.get('last_web_run'):
        try:
            web_due=now-datetime.fromisoformat(state['last_web_run'])>=timedelta(minutes=WEB_INTERVAL_MINUTES)
        except Exception:
            web_due=True

    try:
        web_items=await asyncio.to_thread(collect_web,MAX_AGE_HOURS) if web_due else []
        print('WEB_ITEMS',len(web_items))
        for item in web_items:
            stats['web_checked']+=1
            key=hashlib.sha256(item['url'].encode()).hexdigest()
            if key in seen:
                continue
            seen[key]=None
            value,reasons=score(item['text'])
            record_score(value,reasons)
            if value<MIN_SCORE:
                reason=reasons[0] if reasons else f'score<{MIN_SCORE}'
                reject_counts[reason]=reject_counts.get(reason,0)+1
                continue
            sent_key=delivery_key(item['url'],item['text'])
            if sent_key in sent_keys:
                continue
            stats['web_candidates']+=1
            published=item.get('published') or datetime.now(timezone.utc)
            found.append((value,published,item['text'],item['url'],reasons,item.get('source','Web'),key,sent_key))
        if web_due:
            state['last_web_run']=datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        print('WEB_SCAN_WARN',type(exc).__name__)

    found.sort(key=lambda item:(item[0],item[1]),reverse=True)
    sent=0
    failed=0
    for value,published,text,url,reasons,source,seen_key,sent_key in found[:MAX_LEADS_PER_RUN]:
        card=build(text,url,source,value,reasons,published.strftime('%d.%m %H:%M UTC'))
        try:
            await notify(card)
            sent_keys[sent_key]=None
            sent+=1
        except Exception as exc:
            failed+=1
            seen.pop(seen_key,None)
            print('SEND_WARN',source,type(exc).__name__)

    status_due=SEND_STATUS and not state.get('last_status')
    if SEND_STATUS and state.get('last_status'):
        try:
            status_due=datetime.now(timezone.utc)-datetime.fromisoformat(state['last_status'])>=timedelta(hours=STATUS_INTERVAL_HOURS)
        except Exception:
            status_due=True
    if status_due:
        summary=(
            f'✅ LogoLead работает\nВерсия: {BUILD_SHA}\n'
            f'Проверено: Telegram global {stats["global_checked"]}, группы {stats["group_checked"]}, глубокий поиск {stats["deep_checked"]}, площадки {stats["market_checked"]}\n'
            f'Публичных групп в базе: {len(groups)}\n'
            f'Новых подходящих лидов: {len(found)}, отправлено: {sent}'
        )
        try:
            await notify(summary)
            state['last_status']=datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            print('STATUS_SEND_WARN',type(exc).__name__)

    state['seen']=list(seen.keys())[-20000:]
    state['sent']=list(sent_keys.keys())[-10000:]
    state['last_run']=datetime.now(timezone.utc).isoformat()
    save_state(state)
    await client.disconnect()
    top_queries=sorted(query_hits.items(),key=lambda x:x[1],reverse=True)[:10]
    top_rejects=sorted(reject_counts.items(),key=lambda x:x[1],reverse=True)[:10]
    top_signals=sorted(signal_combos.items(),key=lambda x:x[1],reverse=True)[:10]
    print('PIPELINE_STATS',json.dumps(stats,ensure_ascii=False,sort_keys=True))
    print('SCORE_HIST',json.dumps(sorted(score_hist.items(),key=lambda x:int(x[0])),ensure_ascii=False))
    print('SIGNAL_COMBOS',json.dumps(top_signals,ensure_ascii=False))
    print('QUERY_HITS',json.dumps(top_queries,ensure_ascii=False))
    print('REJECT_COUNTS',json.dumps(top_rejects,ensure_ascii=False))
    print('FOUND',len(found),'SENT',sent,'SEND_FAILED',failed,'GROUPS',len(groups),'SEEN',len(state['seen']))

if __name__=='__main__':
    asyncio.run(main())
