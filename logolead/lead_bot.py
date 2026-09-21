import asyncio, hashlib, json, os, re, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import User
from classifier import score
from card import build
from web_sources import collect_cloud_web
from market_sources import collect_markets
from sources import merge_unique, content_signature

TG_API_ID=int(os.environ.get('TG_API_ID','0'))
TG_API_HASH=os.environ.get('TG_API_HASH','')
TG_SESSION=os.environ.get('TG_SESSION','')
BOT_TOKEN=os.environ.get('LOGOLEAD_BOT_TOKEN') or os.environ.get('LEADS_BOT_TOKEN','')
CHAT_ID=os.environ.get('LOGOLEAD_CHAT_ID','')

STATE_VERSION=4
CLASSIFIER_VERSION=7
STATE_DIR=Path('.lead_state')
STATE_FILE=STATE_DIR/'state.json'
MAX_AGE_HOURS=int(os.environ.get('MAX_AGE_HOURS','72'))
SEARCH_LIMIT=int(os.environ.get('SEARCH_LIMIT','40'))
MAX_LEADS_PER_RUN=int(os.environ.get('MAX_LEADS_PER_RUN','25'))
DELIVERY_MAX_AGE_HOURS=int(os.environ.get('DELIVERY_MAX_AGE_HOURS','24'))
PENDING_LIMIT=int(os.environ.get('PENDING_LIMIT','500'))
MIN_SCORE=int(os.environ.get('MIN_SCORE','35'))
RUN_INTERVAL_MINUTES=int(os.environ.get('RUN_INTERVAL_MINUTES','10'))
DISCOVERY_INTERVAL_MINUTES=int(os.environ.get('DISCOVERY_INTERVAL_MINUTES','360'))
GROUP_SCAN_LIMIT=int(os.environ.get('GROUP_SCAN_LIMIT','80'))
INITIAL_GROUP_SCAN_LIMIT=int(os.environ.get('INITIAL_GROUP_SCAN_LIMIT','180'))
BACKFILL_GROUPS_PER_RUN=int(os.environ.get('BACKFILL_GROUPS_PER_RUN','1'))
BACKFILL_SCAN_LIMIT=int(os.environ.get('BACKFILL_SCAN_LIMIT','120'))
MAX_DISCOVERED_GROUPS=int(os.environ.get('MAX_DISCOVERED_GROUPS','30'))
GROUP_CACHE_LIMIT=int(os.environ.get('GROUP_CACHE_LIMIT','120'))
DEEP_GROUP_INTERVAL_MINUTES=int(os.environ.get('DEEP_GROUP_INTERVAL_MINUTES','180'))
DEEP_GROUP_SCAN_COUNT=int(os.environ.get('DEEP_GROUP_SCAN_COUNT','6'))
DEEP_GROUP_SEARCH_LIMIT=int(os.environ.get('DEEP_GROUP_SEARCH_LIMIT','15'))
WEB_INTERVAL_MINUTES=int(os.environ.get('WEB_INTERVAL_MINUTES','60'))
MARKET_INTERVAL_MINUTES=int(os.environ.get('MARKET_INTERVAL_MINUTES','30'))
ENABLE_WEB=os.environ.get('ENABLE_WEB','0').strip().lower() in {'1','true','yes','on'}
ENABLE_MARKETS=os.environ.get('ENABLE_MARKETS','1').strip().lower() in {'1','true','yes','on'}
DELIVERY_ENABLED=os.environ.get('DELIVERY_ENABLED','0').strip().lower() in {'1','true','yes','on'}
ENABLE_FEEDBACK=os.environ.get('ENABLE_FEEDBACK','0').strip().lower() in {'1','true','yes','on'}
FEEDBACK_LIMIT=int(os.environ.get('FEEDBACK_LIMIT','500'))
FORCE_RUN=os.environ.get('FORCE_RUN','0').strip().lower() in {'1','true','yes','on'}
SEND_STATUS=os.environ.get('SEND_STATUS','0').strip().lower() in {'1','true','yes','on'}
STATUS_INTERVAL_HOURS=int(os.environ.get('STATUS_INTERVAL_HOURS','24'))
BOT_SEND_RETRIES=int(os.environ.get('BOT_SEND_RETRIES','2'))
BOT_RETRY_MAX_SECONDS=int(os.environ.get('BOT_RETRY_MAX_SECONDS','30'))
DISPLAY_TZ_OFFSET=int(os.environ.get('DISPLAY_TZ_OFFSET','3'))
EXCLUDED_CHAT_USERNAMES={x.strip().lstrip('@').lower() for x in os.environ.get('EXCLUDED_CHAT_USERNAMES','VAbkhaziiLeadsBot').split(',') if x.strip()}
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
    'сколько стоит логопед','стоимость логопеда','ребенок шепелявит','ребёнок шепелявит',
    'ребенок заикается','ребёнок заикается','говорит невнятно ребенок','говорит невнятно ребёнок',
    'путает буквы ребенок','путает буквы ребёнок','задержка речи ребенок','задержка речи ребёнок',
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
DEEP_GROUP_QUERIES=['логопед','дефектолог','нейрологопед','не говорит','не выговаривает','зрр','зпрр','картавит','шепелявит','заикается','задержка речи','запуск речи','дисграфия','говорит невнятно','мало слов','путает буквы','ошибки на письме']
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
    state.setdefault('pending',[])
    state.setdefault('feedback',{})
    state.setdefault('feedback_index',{})
    state.setdefault('bot_update_offset',0)
    state.setdefault('groups',{})
    state.setdefault('group_last_ids',{})
    state.setdefault('group_backfill_ids',{})
    state['groups']={k:v for k,v in state['groups'].items() if k.strip().lstrip('@').lower() not in EXCLUDED_CHAT_USERNAMES}
    state['group_last_ids']={k:v for k,v in state['group_last_ids'].items() if k.strip().lstrip('@').lower() not in EXCLUDED_CHAT_USERNAMES}
    state['group_backfill_ids']={k:v for k,v in state['group_backfill_ids'].items() if k.strip().lstrip('@').lower() not in EXCLUDED_CHAT_USERNAMES}
    if state.get('classifier_version')!=CLASSIFIER_VERSION:
        state['seen']=[]
        state['group_last_ids']={}
        state['group_backfill_ids']={}
        state['classifier_version']=CLASSIFIER_VERSION
        for name in ('last_run','last_deep_scan','last_market_run','last_web_run'):
            state.pop(name,None)
    state['version']=STATE_VERSION
    return state

def save_state(state):
    state['version']=STATE_VERSION
    STATE_FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2),'utf-8')

def message_key(chat_id,msg_id):
    chat_ref=str(chat_id).strip().lstrip('@').lower()
    return hashlib.sha256(f'{chat_ref}:{msg_id}'.encode()).hexdigest()

def delivery_key(url,text):
    return hashlib.sha256(content_signature(text,url).encode()).hexdigest()


def freshness_text(dt,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now=now.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    seconds=max(0,int((now-dt).total_seconds()))
    minutes=seconds//60
    if minutes<1:
        return 'только что'
    if minutes<60:
        return f'{minutes} мин назад'
    hours=minutes//60
    if hours<24:
        return f'{hours} ч назад'
    days=hours//24
    return f'{days} дн назад'


def format_published(dt,now=None):
    local=dt.astimezone(timezone(timedelta(hours=DISPLAY_TZ_OFFSET)))
    suffix='МСК' if DISPLAY_TZ_OFFSET==3 else f'UTC{DISPLAY_TZ_OFFSET:+d}'
    return local.strftime('%d.%m %H:%M ') + suffix + ' · ' + freshness_text(dt,now)


def chat_allowed(chat):
    if chat is None or isinstance(chat,User):
        return False
    if getattr(chat,'broadcast',False):
        return False
    username=(getattr(chat,'username',None) or '').strip().lstrip('@')
    if not username:
        return False
    if username.lower() in EXCLUDED_CHAT_USERNAMES:
        return False
    return True


PROVIDER_SENDER_MARKERS=('logoped','defektolog','speechtherapist','speech_therapist','логопед','дефектолог')

async def sender_info(message):
    try:
        sender=await message.get_sender()
    except Exception:
        return True,'',''
    if isinstance(sender,User) and getattr(sender,'bot',False):
        return False,'','сообщение бота'
    username=(getattr(sender,'username',None) or '').strip()
    first=(getattr(sender,'first_name',None) or '').strip()
    last=(getattr(sender,'last_name',None) or '').strip()
    identity=' '.join(x for x in (username,first,last) if x).lower()
    if any(marker in identity for marker in PROVIDER_SENDER_MARKERS):
        return False,'','профиль специалиста'
    return True,('@'+username if username else ''),''

def telegram_source(title,author=''):
    base=f'Telegram: {title}'
    return base+(f' · автор {author}' if author else '')


def pending_to_candidate(item,cutoff,sent_keys):
    try:
        source=item.get('source') or 'Pending'
        source_label=source.split(':',1)[-1].strip().lstrip('@').lower() if source.lower().startswith('telegram:') else ''
        if source_label in EXCLUDED_CHAT_USERNAMES:
            return None
        published=datetime.fromisoformat(item.get('published',''))
        if published.tzinfo is None:
            published=published.replace(tzinfo=timezone.utc)
        if published<cutoff:
            return None
        text=item.get('text') or ''
        url=item.get('url') or ''
        value,reasons=score(text)
        if value<MIN_SCORE:
            return None
        sent_key=delivery_key(url,text)
        if sent_key in sent_keys:
            return None
        return (value,published,text,url,reasons,source,'pending:'+sent_key,sent_key)
    except Exception:
        return None

def candidate_to_pending(item):
    value,published,text,url,reasons,source,seen_key,sent_key=item
    return {
        'published':published.isoformat(),
        'text':text[:2000],
        'url':url,
        'source':source,
        'score':value,
        'sent_key':sent_key,
    }

def pending_stats(items):
    sources={}
    hot=0
    for item in items:
        source=(item.get('source') or 'Unknown').split(':',1)[0]
        sources[source]=sources.get(source,0)+1
        if int(item.get('score') or 0)>=75:
            hot+=1
    top_sources=sorted(sources.items(),key=lambda x:x[1],reverse=True)[:8]
    return {'total':len(items),'hot':hot,'sources':top_sources}

def select_delivery_candidates(items,now=None):
    now=now or datetime.now(timezone.utc)
    cutoff=now-timedelta(hours=DELIVERY_MAX_AGE_HOURS)
    deliverable=[item for item in items if item[1]>=cutoff]
    stale_count=len(items)-len(deliverable)
    return deliverable[:MAX_LEADS_PER_RUN],deliverable[MAX_LEADS_PER_RUN:],stale_count

def author_url_from_source(source):
    match=re.search(r'автор\s+@([A-Za-z0-9_]{5,32})\b',source or '',re.I)
    return f'https://t.me/{match.group(1)}' if match else None

def feedback_id(sent_key):
    return (sent_key or '')[:16]

def parse_feedback_callback(data):
    match=re.fullmatch(r'll:(good|bad):([0-9a-f]{8,24})',data or '')
    return (match.group(1),match.group(2)) if match else None

def feedback_counts(feedback):
    values=[(item or {}).get('label') for item in (feedback or {}).values()]
    return {'good':values.count('good'),'bad':values.count('bad'),'total':len(values)}

def bot_api(method,payload=None):
    if not BOT_TOKEN:
        return {'ok':False,'result':[]}
    data=urllib.parse.urlencode(payload or {}).encode()
    req=urllib.request.Request(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',data=data)
    with urllib.request.urlopen(req,timeout=20) as response:
        return json.loads(response.read(2_000_000).decode('utf-8','ignore'))

async def process_feedback_updates(state):
    if not ENABLE_FEEDBACK or not BOT_TOKEN or not CHAT_ID:
        return
    offset=int(state.get('bot_update_offset',0) or 0)
    payload={
        'offset':offset,
        'timeout':0,
        'allowed_updates':json.dumps(['callback_query']),
    }
    try:
        data=await asyncio.to_thread(bot_api,'getUpdates',payload)
    except Exception as exc:
        print('FEEDBACK_POLL_WARN',type(exc).__name__)
        return
    updates=data.get('result') or []
    feedback=state.get('feedback') or {}
    index=state.get('feedback_index') or {}
    for update in updates:
        try:
            state['bot_update_offset']=max(int(state.get('bot_update_offset',0) or 0),int(update.get('update_id',0))+1)
            callback=update.get('callback_query') or {}
            parsed=parse_feedback_callback(callback.get('data'))
            if not parsed:
                continue
            label,key=parsed
            chat=((callback.get('message') or {}).get('chat') or {}).get('id')
            if str(chat)!=str(CHAT_ID):
                continue
            feedback[key]={
                'label':label,
                'at':datetime.now(timezone.utc).isoformat(),
                'lead':index.get(key,{})
            }
            answer='Отмечено: подходит' if label=='good' else 'Отмечено: не лид'
            try:
                await asyncio.to_thread(bot_api,'answerCallbackQuery',{
                    'callback_query_id':callback.get('id',''),
                    'text':answer,
                    'show_alert':'false',
                })
            except Exception:
                pass
        except Exception as exc:
            print('FEEDBACK_UPDATE_WARN',type(exc).__name__)
    if len(feedback)>FEEDBACK_LIMIT:
        feedback=dict(list(feedback.items())[-FEEDBACK_LIMIT:])
    state['feedback']=feedback
    counts=feedback_counts(feedback)
    if updates:
        print('FEEDBACK_STATS',json.dumps(counts,ensure_ascii=False,sort_keys=True))

async def notify(text,source_url=None,author_url=None,feedback_key=None):
    if not BOT_TOKEN or not CHAT_ID:
        print('DRY_SEND',text.encode('ascii','backslashreplace').decode()[:400])
        return
    payload={
        'chat_id':CHAT_ID,
        'text':text,
        'disable_web_page_preview':'true',
    }
    rows=[]
    buttons=[]
    if source_url:
        buttons.append({'text':'Открыть источник','url':source_url})
    if author_url:
        buttons.append({'text':'Написать автору','url':author_url})
    if buttons:
        rows.append(buttons)
    if ENABLE_FEEDBACK and feedback_key:
        rows.append([
            {'text':'👍 Подходит','callback_data':f'll:good:{feedback_key}'},
            {'text':'👎 Не лид','callback_data':f'll:bad:{feedback_key}'},
        ])
    if rows:
        payload['reply_markup']=json.dumps({'inline_keyboard':rows},ensure_ascii=False)
    data=urllib.parse.urlencode(payload).encode()
    url=f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

    def send():
        last_error=None
        for attempt in range(BOT_SEND_RETRIES+1):
            req=urllib.request.Request(url,data=data)
            try:
                with urllib.request.urlopen(req,timeout=20) as response:
                    response.read(2000)
                    return
            except urllib.error.HTTPError as exc:
                last_error=exc
                if attempt>=BOT_SEND_RETRIES:
                    raise
                wait=2
                if exc.code==429:
                    try:
                        payload=json.loads(exc.read().decode('utf-8','ignore'))
                        wait=int(((payload.get('parameters') or {}).get('retry_after')) or 2)
                    except Exception:
                        wait=2
                elif exc.code<500:
                    raise
                time.sleep(max(1,min(BOT_RETRY_MAX_SECONDS,wait)))
            except Exception as exc:
                last_error=exc
                if attempt>=BOT_SEND_RETRIES:
                    raise
                time.sleep(min(BOT_RETRY_MAX_SECONDS,2*(attempt+1)))
        if last_error:
            raise last_error

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
                if not chat_allowed(chat):
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

def validate_config():
    if not (TG_API_ID and TG_API_HASH and TG_SESSION):
        raise RuntimeError('Missing Telegram user credentials')
    if (DELIVERY_ENABLED or SEND_STATUS or ENABLE_FEEDBACK) and not (BOT_TOKEN and CHAT_ID):
        raise RuntimeError('Missing Telegram bot delivery credentials')
    return True

async def main():
    validate_config()

    state=load_state()
    await process_feedback_updates(state)
    seen=dict.fromkeys(state.get('seen',[]))
    sent_keys=dict.fromkeys(state.get('sent',[]))
    found=[]
    seed_groups={}
    stats={'global_checked':0,'global_candidates':0,'group_checked':0,'group_candidates':0,'backfill_checked':0,'backfill_candidates':0,'deep_checked':0,'deep_candidates':0,'market_checked':0,'market_candidates':0,'web_checked':0,'web_candidates':0}
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
                save_state(state)
                print('SKIP_INTERVAL',state['last_run'])
                return
        except Exception:
            pass

    client=TelegramClient(StringSession(TG_SESSION),TG_API_ID,TG_API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError('TG_SESSION not authorized')

    cutoff=now-timedelta(hours=MAX_AGE_HOURS)
    restored_pending=[]
    for item in state.get('pending',[]):
        candidate=pending_to_candidate(item,cutoff,sent_keys)
        if candidate is not None:
            restored_pending.append(candidate)
    if restored_pending:
        print('PENDING_RESTORED',len(restored_pending))
    found.extend(restored_pending)

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
                chat_id=getattr(chat,'id',0)
                key=message_key(username or chat_id,message.id)
                if key in seen:
                    continue
                seen[key]=None
                if not chat_allowed(chat):
                    reject_counts['не публичная группа']=reject_counts.get('не публичная группа',0)+1
                    continue
                low_title=(title or '').lower()
                if any(x in low_title for x in COMMERCIAL_CHAT_MARKERS):
                    reject_counts['коммерческий чат']=reject_counts.get('коммерческий чат',0)+1
                    continue
                seed_groups[username]=title or username
                value,reasons=score(message.message)
                record_score(value,reasons)
                if value<MIN_SCORE:
                    reason=reasons[0] if reasons else f'score<{MIN_SCORE}'
                    reject_counts[reason]=reject_counts.get(reason,0)+1
                    continue
                sender_ok,author,sender_reason=await sender_info(message)
                if not sender_ok:
                    reject_counts[sender_reason]=reject_counts.get(sender_reason,0)+1
                    continue
                url=f'https://t.me/{username}/{message.id}' if username else ''
                sent_key=delivery_key(url,message.message)
                if sent_key in sent_keys:
                    continue
                stats['global_candidates']+=1
                found.append((value,message.date,message.message,url,reasons,telegram_source(title,author),key,sent_key))
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
    group_backfill_ids=state.get('group_backfill_ids') or {}

    all_groups=[item for item in groups.items() if item[0].strip().lstrip('@').lower() not in EXCLUDED_CHAT_USERNAMES]
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
        oldest_id=None
        iterated=0
        hit_cutoff=False
        try:
            scan_limit=INITIAL_GROUP_SCAN_LIMIT if min_id==0 else GROUP_SCAN_LIMIT
            async for message in client.iter_messages(username,limit=scan_limit,min_id=min_id):
                iterated+=1
                newest_id=max(newest_id,message.id)
                oldest_id=message.id if oldest_id is None else min(oldest_id,message.id)
                if not message.message or not message.date:
                    continue
                if message.date<cutoff:
                    hit_cutoff=True
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
                sender_ok,author,sender_reason=await sender_info(message)
                if not sender_ok:
                    reject_counts[sender_reason]=reject_counts.get(sender_reason,0)+1
                    continue
                url=f'https://t.me/{username}/{message.id}'
                sent_key=delivery_key(url,message.message)
                if sent_key in sent_keys:
                    continue
                stats['group_candidates']+=1
                found.append((value,message.date,message.message,url,reasons,telegram_source(title or username,author),key,sent_key))
            if newest_id>min_id:
                group_last_ids[username]=newest_id
            if min_id==0:
                if hit_cutoff or iterated<scan_limit or oldest_id is None:
                    group_backfill_ids.pop(username,None)
                else:
                    group_backfill_ids[username]=oldest_id
        except FloodWaitError as exc:
            if exc.seconds<=60:
                await asyncio.sleep(exc.seconds+1)
            else:
                print('GROUP_FLOOD_WAIT',username,exc.seconds)
                break
        except Exception as exc:
            print('SCAN_WARN',username,type(exc).__name__)

    state['group_last_ids']=group_last_ids

    backfill_items=list(group_backfill_ids.items())[:BACKFILL_GROUPS_PER_RUN]
    if backfill_items:
        print('BACKFILL_SET',len(backfill_items),'PENDING',len(group_backfill_ids))
    for username,offset_id in backfill_items:
        if username not in groups:
            group_backfill_ids.pop(username,None)
            continue
        title=groups.get(username) or username
        start_id=int(offset_id or 0)
        oldest_id=start_id
        iterated=0
        hit_cutoff=False
        try:
            async for message in client.iter_messages(username,limit=BACKFILL_SCAN_LIMIT,offset_id=start_id):
                iterated+=1
                oldest_id=min(oldest_id,message.id)
                if not message.message or not message.date:
                    continue
                if message.date<cutoff:
                    hit_cutoff=True
                    break
                stats['backfill_checked']+=1
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
                sender_ok,author,sender_reason=await sender_info(message)
                if not sender_ok:
                    reject_counts[sender_reason]=reject_counts.get(sender_reason,0)+1
                    continue
                url=f'https://t.me/{username}/{message.id}'
                sent_key=delivery_key(url,message.message)
                if sent_key in sent_keys:
                    continue
                stats['backfill_candidates']+=1
                found.append((value,message.date,message.message,url,reasons,telegram_source(title,author),key,sent_key))
            if hit_cutoff or iterated<BACKFILL_SCAN_LIMIT or oldest_id>=start_id:
                group_backfill_ids.pop(username,None)
            else:
                group_backfill_ids[username]=oldest_id
        except FloodWaitError as exc:
            if exc.seconds<=60:
                await asyncio.sleep(exc.seconds+1)
            else:
                print('BACKFILL_FLOOD_WAIT',username,exc.seconds)
                break
        except Exception as exc:
            print('BACKFILL_WARN',username,type(exc).__name__)
    state['group_backfill_ids']=group_backfill_ids

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
                        sender_ok,author,sender_reason=await sender_info(message)
                        if not sender_ok:
                            reject_counts[sender_reason]=reject_counts.get(sender_reason,0)+1
                            continue
                        url=f'https://t.me/{username}/{message.id}'
                        sent_key=delivery_key(url,message.message)
                        if sent_key in sent_keys:
                            continue
                        stats['deep_candidates']+=1
                        found.append((value,message.date,message.message,url,reasons,telegram_source(title or username,author),key,sent_key))
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
        web_items=await asyncio.to_thread(collect_cloud_web,MAX_AGE_HOURS) if web_due else []
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

    found=merge_unique(found)
    found=[item for item in found if item[0]>=MIN_SCORE and item[7] not in sent_keys]
    found.sort(key=lambda item:(item[0],item[1]),reverse=True)

    sent=0
    failed=0
    remaining=[]
    if DELIVERY_ENABLED:
        batch,queued_after_batch,stale_count=select_delivery_candidates(found)
        if stale_count:
            print('STALE_PENDING_DROPPED',stale_count)
        remaining.extend(queued_after_batch)
        for value,published,text,url,reasons,source,seen_key,sent_key in batch:
            card=build(text,url,source,value,reasons,format_published(published))
            try:
                fid=feedback_id(sent_key) if ENABLE_FEEDBACK else None
                await notify(card,url,author_url_from_source(source),fid)
                sent_keys[sent_key]=None
                if fid:
                    index=state.get('feedback_index') or {}
                    index[fid]={
                        'score':value,
                        'source':source,
                        'url':url,
                        'published':published.isoformat(),
                    }
                    if len(index)>FEEDBACK_LIMIT*2:
                        index=dict(list(index.items())[-FEEDBACK_LIMIT*2:])
                    state['feedback_index']=index
                sent+=1
            except Exception as exc:
                failed+=1
                remaining.append((value,published,text,url,reasons,source,seen_key,sent_key))
                print('SEND_WARN',source,type(exc).__name__)
    else:
        remaining=list(found)
        print('DELIVERY_PAUSED','PENDING',len(remaining))

    remaining=merge_unique([item for item in remaining if item[7] not in sent_keys])
    remaining.sort(key=lambda item:(item[0],item[1]),reverse=True)
    state['pending']=[candidate_to_pending(item) for item in remaining[:PENDING_LIMIT]]
    print('PENDING_STATS',json.dumps(pending_stats(state['pending']),ensure_ascii=False))
    if ENABLE_FEEDBACK:
        print('FEEDBACK_TOTALS',json.dumps(feedback_counts(state.get('feedback')),ensure_ascii=False,sort_keys=True))

    status_due=DELIVERY_ENABLED and SEND_STATUS and not state.get('last_status')
    if DELIVERY_ENABLED and SEND_STATUS and state.get('last_status'):
        try:
            status_due=datetime.now(timezone.utc)-datetime.fromisoformat(state['last_status'])>=timedelta(hours=STATUS_INTERVAL_HOURS)
        except Exception:
            status_due=True
    if status_due:
        summary=(
            f'✅ LogoLead работает\nВерсия: {BUILD_SHA}\n'
            f'Проверено: Telegram global {stats["global_checked"]}, группы {stats["group_checked"]}, история {stats["backfill_checked"]}, глубокий поиск {stats["deep_checked"]}, площадки {stats["market_checked"]}\n'
            f'Публичных групп в базе: {len(groups)}\n'
            f'Подходящих лидов в очереди: {len(found)}, отправлено: {sent}, ожидают: {len(state["pending"])}'
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
    print('FOUND',len(found),'SENT',sent,'SEND_FAILED',failed,'PENDING',len(state['pending']),'GROUPS',len(groups),'SEEN',len(state['seen']))

if __name__=='__main__':
    asyncio.run(main())
