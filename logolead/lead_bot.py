import asyncio, hashlib, json, os, re, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import User
from classifier import score, score_market_order
from session_compat import normalize_tg_session
from card import build
from web_sources import collect_web
from market_sources import collect_markets
from sources import merge_unique, content_signature

TG_API_ID=int(os.environ.get('TG_API_ID','0'))
TG_API_HASH=os.environ.get('TG_API_HASH','')
TG_SESSION=normalize_tg_session(os.environ.get('TG_SESSION',''))
BOT_TOKEN=os.environ.get('LOGOLEAD_BOT_TOKEN','')
CHAT_ID=os.environ.get('LOGOLEAD_CHAT_ID','')

STATE_VERSION=4
CLASSIFIER_VERSION=10
STATE_DIR=Path('.lead_state')
STATE_FILE=STATE_DIR/'state.json'
MAX_AGE_HOURS=int(os.environ.get('MAX_AGE_HOURS','72'))
SEARCH_LIMIT=int(os.environ.get('SEARCH_LIMIT','40'))
GLOBAL_ROTATING_QUERIES_PER_RUN=int(os.environ.get('GLOBAL_ROTATING_QUERIES_PER_RUN','12'))
MAX_LEADS_PER_RUN=int(os.environ.get('MAX_LEADS_PER_RUN','25'))
DELIVERY_MAX_AGE_HOURS=int(os.environ.get('DELIVERY_MAX_AGE_HOURS','24'))
PENDING_LIMIT=int(os.environ.get('PENDING_LIMIT','500'))
MIN_SCORE=int(os.environ.get('MIN_SCORE','35'))
RUN_INTERVAL_MINUTES=int(os.environ.get('RUN_INTERVAL_MINUTES','10'))
DISCOVERY_INTERVAL_MINUTES=int(os.environ.get('DISCOVERY_INTERVAL_MINUTES','360'))
DISCOVERY_ROTATING_QUERIES_PER_REFRESH=int(os.environ.get('DISCOVERY_ROTATING_QUERIES_PER_REFRESH','18'))
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

CORE_SEARCH_QUERIES=[
    'ищу логопеда','нужен логопед','посоветуйте логопеда','порекомендуйте логопеда',
    'подскажите логопеда','логопед ребенку','логопед ребёнку','нужен дефектолог',
    'нужен нейрологопед','ребенок не говорит','ребёнок не говорит','запуск речи',
]
SEARCH_QUERIES=[
    'ищу логопеда','ищем логопеда','нужен логопед','логопед нужен',
    'нужен логопед ребенку','нужен логопед ребёнку','логопед ребенку','логопед ребёнку',
    'посоветуйте логопеда','порекомендуйте логопеда','подскажите логопеда',
    'кто-нибудь знает логопеда','кто знает логопеда','хороший логопед',
    'где найти логопеда','контакты логопеда','логопед для ребенка','логопед для ребёнка',
    'логопед онлайн','ищу логопеда онлайн','нужен дефектолог','дефектолог нужен',
    'посоветуйте дефектолога','порекомендуйте дефектолога','нужен нейрологопед',
    'нужен специалист по речи','посоветуйте специалиста ребенок не говорит','куда вести ребенок не говорит',
    'не получается звук р','не получается звук л','поставить звук р','поставить звук л',
    'ребенок не говорит','ребёнок не говорит','не говорит предложениями',
    'плохо говорит ребенок','плохо говорит ребёнок','не выговаривает р',
    'не выговаривает л','не выговаривает звуки','запуск речи','ЗРР логопед',
    'ЗПРР логопед','дисграфия логопед','дислексия логопед',
    'сколько стоит логопед','стоимость логопеда','ребенок шепелявит','ребёнок шепелявит',
    'ребенок заикается','ребёнок заикается','говорит невнятно ребенок','говорит невнятно ребёнок',
    'путает буквы ребенок','путает буквы ребёнок','задержка речи ребенок','задержка речи ребёнок',
    'логопед','дефектолог','нейрологопед',
]
CORE_DISCOVERY_QUERIES=[
    'логопед родители чат','мамы дети развитие речи','запуск речи родители',
    'ЗРР родители чат','дефектолог родители','мамы дошкольников чат',
    'русскоязычный таиланд','русскоязычные паттайя',
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
    'мамы саратов чат','мамы ижевск чат','мамы оренбург чат','мамы иркутск чат',
    'мамы хабаровск чат','мамы владивосток чат','мамы калининград чат','мамы ярославль чат',
    'мамы тула чат','мамы рязань чат','мамы барнаул чат','мамы ставрополь чат',
    'русскоязычный таиланд','русскоязычные паттайя','русские в таиланде',
    'русскоязычные пхукет','мамы паттайя','мамы пхукет',
    'мамы бангкок','мамы чанмай','русскоязычный бангкок',
    'русскоязычные тбилиси','мамы тбилиси','мамы батуми',
    'русскоязычные дубай','мамы дубай','мамы ереван',
    'русскоязычные белграда','мамы сербия','мамы германия',
    'мамы стамбул','мамы анталия','мамы кипр',
    'русскоязычные казахстан','русскоязычные вьетнам','мамы нячанг',
]
DEEP_GROUP_QUERIES=['логопед','дефектолог','нейрологопед','нужен специалист','не говорит','не выговаривает','звук р','звук л','поставить звук','зрр','зпрр','картавит','шепелявит','заикается','задержка речи','запуск речи','дисграфия','говорит невнятно','мало слов','путает буквы','ошибки на письме']
COMMERCIAL_CHAT_MARKERS=[
    'услуги логопеда','логопедический центр','школа логопеда',
    'курсы логопедов','вакансии логопед','обучение логопедов',
    'логопедические услуги','логопедические занятия',
]

# Only read publicly addressable groups. Never join them or send messages.
PUBLIC_GROUP_SEEDS = (
    'ru_chat_thailand', 'ru_tai', 'russian_in_thailand',
    'chat_thailand', 'thailand_russia_ru', 'russian_thailand',
    'pattayadeti', 'thailand_chat_russ', 'russiansin_thailand',
    'pattayachat', 'forum_thailand',
    'phuket_parents_bg', 'phuket_deti', 'pattaya_women_bg',
    'phuket_women_bg', 'bangkokwoman',
)

FAMILY_GROUP_MARKERS = ('родител', 'мам', 'дети', 'детск', 'семейн', 'family', 'kids')


def discovery_priority(item, global_found=None):
    """Prioritize family-oriented chats, then verified public groups."""
    global_found = global_found or {}
    username, title = item
    if username in global_found:
        return 0
    if any(tag in (title or '').lower() for tag in FAMILY_GROUP_MARKERS):
        return 1
    if username.lower() in PUBLIC_GROUP_SEEDS:
        return 2
    return 3


def choose_group_scan(all_groups, global_found, state, max_groups):
    """Rotate high-priority public chats instead of permanently skipping the tail."""
    if max_groups<=0:
        return []
    mandatory=[item for item in all_groups if discovery_priority(item,global_found)==0]
    important=[item for item in all_groups if 0<discovery_priority(item,global_found)<3]
    others=[item for item in all_groups if discovery_priority(item,global_found)==3]
    chosen=mandatory[:max_groups]
    remaining=max(0,max_groups-len(chosen))
    if important and remaining:
        count=min(remaining,len(important))
        cursor=int(state.get('priority_scan_cursor',
                             state.get('group_scan_cursor',0)) or 0)%len(important)
        chosen.extend(important[(cursor+i)%len(important)] for i in range(count))
        state['priority_scan_cursor']=(cursor+count)%len(important)
        remaining-=count
    if others and remaining:
        count=min(remaining,len(others))
        cursor=int(state.get('group_scan_cursor',0) or 0)%len(others)
        chosen.extend(others[(cursor+i)%len(others)] for i in range(count))
        state['group_scan_cursor']=(cursor+count)%len(others)
    return chosen


def choose_backfill_groups(backfill_ids,state,limit):
    """Fairly process public-group history without starving busy groups."""
    items=list(backfill_ids.items())
    if limit<=0 or not items:
        return []
    cursor=int(state.get('backfill_cursor',0) or 0)%len(items)
    size=min(limit,len(items))
    chosen=[items[(cursor+i)%len(items)] for i in range(size)]
    state['backfill_cursor']=(cursor+size)%len(items)
    return chosen


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
        # Keep history offsets while rescoring already-seen speech requests.
        state['classifier_version']=CLASSIFIER_VERSION
        for name in ('last_run','last_deep_scan','last_market_run','last_web_run'):
            state.pop(name,None)
    state['version']=STATE_VERSION
    return state

def save_state(state):
    """Atomically update state so interrupted writes cannot truncate it."""
    state['version']=STATE_VERSION
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    temporary=STATE_FILE.with_name(STATE_FILE.name+'.tmp')
    try:
        temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2),'utf-8')
        os.replace(temporary,STATE_FILE)
    finally:
        if temporary.exists():
            temporary.unlink()

def select_search_queries(state):
    core=[]
    for query in CORE_SEARCH_QUERIES:
        if query in SEARCH_QUERIES and query not in core:
            core.append(query)
    rotating=[q for q in SEARCH_QUERIES if q not in core]
    if not rotating or GLOBAL_ROTATING_QUERIES_PER_RUN<=0:
        state['query_cursor']=0
        return core
    count=min(GLOBAL_ROTATING_QUERIES_PER_RUN,len(rotating))
    cursor=int(state.get('query_cursor',0) or 0)%len(rotating)
    batch=[rotating[(cursor+i)%len(rotating)] for i in range(count)]
    state['query_cursor']=(cursor+count)%len(rotating)
    return core+batch

def select_discovery_queries(state):
    core=[]
    for query in CORE_DISCOVERY_QUERIES:
        if query in DISCOVERY_QUERIES and query not in core:
            core.append(query)
    rotating=[q for q in DISCOVERY_QUERIES if q not in core]
    if not rotating or DISCOVERY_ROTATING_QUERIES_PER_REFRESH<=0:
        state['discovery_query_cursor']=0
        return core
    count=min(DISCOVERY_ROTATING_QUERIES_PER_REFRESH,len(rotating))
    cursor=int(state.get('discovery_query_cursor',0) or 0)%len(rotating)
    batch=[rotating[(cursor+i)%len(rotating)] for i in range(count)]
    state['discovery_query_cursor']=(cursor+count)%len(rotating)
    return core+batch

def candidate_priority(item,now=None):
    now=now or datetime.now(timezone.utc)
    published=item[1]
    if published.tzinfo is None:
        published=published.replace(tzinfo=timezone.utc)
    age_hours=max(0,(now-published).total_seconds()/3600)
    if age_hours<=1: freshness=10
    elif age_hours<=3: freshness=8
    elif age_hours<=6: freshness=5
    elif age_hours<=12: freshness=3
    else: freshness=0
    source=(item[5] or '').lower()
    if source.startswith('profi.ru'): source_bonus=6
    elif source.startswith('kwork'): source_bonus=3
    else: source_bonus=0
    return (item[0]+freshness+source_bonus,published.timestamp())

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
        if source.startswith(('Profi.ru', 'Kwork')):
            value,reasons=score_market_order(text,source)
        else:
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
    if MAX_LEADS_PER_RUN <= 0:
        return deliverable,[],stale_count
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
                    result=json.loads(response.read(2000).decode('utf-8','ignore'))
                    if not result.get('ok') or not (result.get('result') or {}).get('message_id'):
                        raise RuntimeError('Telegram delivery not confirmed by Bot API')
                    return result['result']['message_id']
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

JOINED_SOURCE_MARKERS = (
    'мам', 'родител', 'дети', 'детск', 'семейн', 'логопед',
    'дефектолог', 'развити', 'пхукет', 'паттая', 'пхатай',
    'таиланд', 'тайланд', 'пхукет', 'пхукет',
)


def is_relevant_joined_chat(title):
    lowered=(title or '').strip().lower()
    return any(word in lowered for word in JOINED_SOURCE_MARKERS)


async def discover_joined_public_groups(client, max_dialogs=None):
    """Include on-account, public family groups missing from global SearchRequest.

    Only publicly linked, non-broadcast groups; no private chat contents or
    dialog metadata are logged or forwarded.
    """
    found={}
    inspected=0
    async for dialog in client.iter_dialogs(limit=max_dialogs):
        inspected+=1
        entity=dialog.entity
        title=(getattr(dialog,'name','') or '').strip()
        if not is_relevant_joined_chat(title):
            continue
        if not chat_allowed(entity):
            continue
        if any(marker in title.lower() for marker in COMMERCIAL_CHAT_MARKERS):
            continue
        username=getattr(entity,'username',None)
        if username:
            found[username]=title
    print('MEMBER_GROUP_DISCOVERY',inspected,len(found))
    return found


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
    # SearchRequest only indexes public groups matching discovery terms. The
    # authorised account may already belong to relevant public parent chats
    # which cannot be discovered that way, even though it can read them.
    joined=await discover_joined_public_groups(client)
    for username,title in joined.items():
        if username in groups:
            continue
        groups[username]=title
        if len(groups)>=GROUP_CACHE_LIMIT:
            break
    discovery_queries=select_discovery_queries(state)
    print('DISCOVERY_QUERY_SET',len(discovery_queries),'OF',len(DISCOVERY_QUERIES),'CURSOR',state.get('discovery_query_cursor',0))
    for query in discovery_queries:
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

    # Explicitly verify a small list of public Russian-speaking communities.
    # They are candidates only: private, restricted and broadcast chats are skipped.
    for username in PUBLIC_GROUP_SEEDS:
        if username in groups:
            continue
        try:
            entity = await client.get_entity(username)
            if not chat_allowed(entity):
                continue
            title = (getattr(entity, 'title', '') or username).strip()
            if any(word in title.lower() for word in COMMERCIAL_CHAT_MARKERS):
                continue
            groups[username] = title
        except FloodWaitError as exc:
            print('SEED_GROUP_FLOOD_WAIT', exc.seconds)
            break
        except Exception as exc:
            print('SEED_GROUP_UNAVAILABLE', username, type(exc).__name__)

    if groups:
        state['groups']=groups
    state['last_discovery']=now.isoformat()
    print('DISCOVERED_GROUPS',len(state.get('groups') or {}))
    return state.get('groups') or {}

def require_logoped_owner(account):
    """Never scan somebody else's Telegram account for LogoLead."""
    identity=(getattr(account,'username',None) or '').strip().lstrip('@').casefold()
    if getattr(account,'bot',False) or identity!='logopedutkina':
        raise RuntimeError('LogoLead requires authorized @logopedutkina Telegram account')
    return True


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
        raise RuntimeError('Dedicated LogoLead Telegram session not authorized')
    account=await client.get_me()
    require_logoped_owner(account)

    cutoff=now-timedelta(hours=MAX_AGE_HOURS)
    restored_pending=[]
    for item in state.get('pending',[]):
        candidate=pending_to_candidate(item,cutoff,sent_keys)
        if candidate is not None:
            restored_pending.append(candidate)
    if restored_pending:
        print('PENDING_RESTORED',len(restored_pending))
    found.extend(restored_pending)

    active_queries=select_search_queries(state)
    print('GLOBAL_QUERY_SET',len(active_queries),'OF',len(SEARCH_QUERIES),'CURSOR',state.get('query_cursor',0))
    for query in active_queries:
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
    selected_groups=choose_group_scan(all_groups,seed_groups,state,MAX_DISCOVERED_GROUPS)
    priority_count=sum(discovery_priority(item,seed_groups)<3 for item in all_groups)
    print('GROUP_SCAN_SET',len(selected_groups),'PRIORITY',priority_count,
          'CACHE',len(all_groups),'CURSOR',state.get('priority_scan_cursor',0))

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

    backfill_items=choose_backfill_groups(group_backfill_ids,state,BACKFILL_GROUPS_PER_RUN)
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
        market_sources={}
        for item in market_items:
            source=(item.get('source') or 'Marketplace').split(' · ',1)[0]
            market_sources[source]=market_sources.get(source,0)+1
        print('MARKET_ITEMS',len(market_items),'BY_SOURCE',json.dumps(market_sources,ensure_ascii=False,sort_keys=True))
        for item in market_items:
            stats['market_checked']+=1
            key=hashlib.sha256(item['url'].encode()).hexdigest()
            if key in seen:
                continue
            seen[key]=None
            value,reasons=score_market_order(item['text'],item.get('source',''))
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

    found=merge_unique(found)
    found=[item for item in found if item[0]>=MIN_SCORE and item[7] not in sent_keys]
    found.sort(key=lambda item:candidate_priority(item,now),reverse=True)

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
                # Persist acknowledgement immediately: a later failure must not
                # cause successful Telegram messages to be delivered again.
                state['sent']=list(sent_keys.keys())[-10000:]
                save_state(state)
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
    remaining.sort(key=lambda item:candidate_priority(item,now),reverse=True)
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
