import hashlib, html, json, os, re, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
KWORK_BASE='https://kwork.ru'
PROFI_PAGES=[
    ('Москва','https://profi.ru/rabota/repetitor/logopedy/'),
    ('Санкт-Петербург','https://profi.ru/geo-spb/registration/repetitor/logoped/'),
    ('Екатеринбург','https://profi.ru/geo-ekt/registration/repetitor/logoped/'),
    ('Ростов-на-Дону','https://profi.ru/geo-rnd/registration/repetitor/logoped/'),
    ('Уфа','https://profi.ru/geo-ufa/registration/repetitor/logoped/'),
    ('Владивосток','https://profi.ru/geo-primorie/registration/repetitor/logoped/'),
    ('Калининград','https://profi.ru/geo-kaliningrad/registration/repetitor/logoped/'),
    ('Ставрополь','https://profi.ru/geo-stavropol/registration/repetitor/logoped/'),
    ('Ярославль','https://profi.ru/geo-yar/registration/repetitor/logoped/'),
]
PROFI_REQUIRED_TERMS=('логопед','дефектолог','нейрологопед','речь','произнош','дисграф','дислекс','зрр','зпрр','звук')
RU_MONTHS={'января':1,'февраля':2,'марта':3,'апреля':4,'мая':5,'июня':6,'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12}
ENABLE_KWORK=os.environ.get('ENABLE_KWORK','1').strip().lower() in {'1','true','yes','on'}
ENABLE_PROFI=os.environ.get('ENABLE_PROFI','1').strip().lower() in {'1','true','yes','on'}
KWORK_QUERIES=['логопед','дефектолог','нейрологопед','дисграфия','дислексия']
KWORK_REQUIRED_TERMS=['логопед','дефектолог','нейрологопед','дисграф','дислекс','зрр','зпрр','запуск речи','постановка звуков']

def fetch_text(url,limit=2_000_000):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ru-RU,ru;q=0.9'})
    with urllib.request.urlopen(req,timeout=20) as response:
        return response.read(limit).decode('utf-8','ignore')

def extract_json_object_after(page,marker):
    start=page.find(marker)
    if start<0:
        return None
    start=page.find('{',start+len(marker))
    if start<0:
        return None
    depth=0; in_string=False; escaped=False
    for idx in range(start,len(page)):
        ch=page[idx]
        if in_string:
            if escaped:
                escaped=False
            elif ch=='\\':
                escaped=True
            elif ch=='"':
                in_string=False
            continue
        if ch=='"':
            in_string=True
        elif ch=='{':
            depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:
                return page[start:idx+1]
    return None

def parse_kwork_datetime(value):
    if not value:
        return None
    try:
        local=datetime.strptime(value,'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=3)))
        return local.astimezone(timezone.utc)
    except Exception:
        return None

def kwork_project_text(item):
    name=' '.join(str(item.get('name') or '').split())
    description=' '.join(str(item.get('description') or '').split())
    parts=[name,description]
    price=item.get('priceLimit')
    if price not in (None,''):
        parts.append(f'Бюджет: {price}')
    return ' '.join(x for x in parts if x).strip()


def is_kwork_relevant(text):
    low=(text or '').lower()
    return any(term in low for term in KWORK_REQUIRED_TERMS)

def fetch_kwork_query(query):
    url=KWORK_BASE+'/projects?'+urllib.parse.urlencode({'keyword':query})
    page=fetch_text(url)
    raw=extract_json_object_after(page,'"wantsListData":')
    if not raw:
        raise ValueError('no_state')
    state=json.loads(raw)
    return ((state.get('pagination') or {}).get('data') or state.get('wants') or [])

def collect_kwork(max_age_hours=72):
    cutoff=datetime.now(timezone.utc)-timedelta(hours=max_age_hours)
    merged={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(fetch_kwork_query,query):query for query in KWORK_QUERIES}
        for future in as_completed(futures):
            query=futures[future]
            try:
                rows=future.result()
            except Exception as exc:
                print('KWORK_WARN',query,type(exc).__name__)
                continue
            for item in rows:
                if not item.get('isWantActive',item.get('status')=='active'):
                    continue
                published=parse_kwork_datetime(item.get('date_create'))
                if not published or published<cutoff:
                    continue
                project_id=item.get('id')
                if not project_id:
                    continue
                text=kwork_project_text(item)
                if len(text)<8 or not is_kwork_relevant(text):
                    continue
                project_url=f'{KWORK_BASE}/projects/{project_id}/view'
                merged[project_url]={
                    'source':'Kwork',
                    'text':text[:2400],
                    'url':project_url,
                    'published':published,
                }
    return list(merged.values())

def visible_text(page):
    value=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',page or '',flags=re.I|re.S)
    value=re.sub(r'<br\s*/?>','\n',value,flags=re.I)
    value=re.sub(r'</(?:p|div|li|h[1-6]|section)>','\n',value,flags=re.I)
    value=re.sub(r'<[^>]+>',' ',value)
    lines=[' '.join(html.unescape(line).split()) for line in value.splitlines()]
    return '\n'.join(line for line in lines if line)

def parse_profi_datetime(text,now=None):
    now=now or datetime.now(timezone.utc)
    low=(text or '').lower()
    matches=list(re.finditer(r'(\d+)\s+минут(?:у|ы)?\s+назад',low))
    if matches:
        return now-timedelta(minutes=int(matches[-1].group(1)))
    matches=list(re.finditer(r'(\d+)\s+час(?:а|ов)?\s+назад',low))
    if matches:
        return now-timedelta(hours=int(matches[-1].group(1)))
    matches=list(re.finditer(r'(\d+)\s+(?:день|дня|дней)\s+назад',low))
    if matches:
        return now-timedelta(days=int(matches[-1].group(1)))
    if re.search(r'\bсегодня\b',low):
        return now
    if re.search(r'\bвчера\b',low):
        return now-timedelta(days=1)
    if re.search(r'\bпозавчера\b',low):
        return now-timedelta(days=2)
    date_re=r'(?<!\d)(\d{1,2})\s+('+'|'.join(RU_MONTHS)+r')\s+(20\d{2})(?!\d)'
    matches=list(re.finditer(date_re,low))
    if not matches:
        return None
    m=matches[-1]
    local=datetime(int(m.group(3)),RU_MONTHS[m.group(2)],int(m.group(1)),12,0,tzinfo=timezone(timedelta(hours=3)))
    return local.astimezone(timezone.utc)

def parse_profi_page(page,page_url,region,max_age_hours=72,now=None):
    now=now or datetime.now(timezone.utc)
    cutoff=now-timedelta(hours=max_age_hours)
    text=visible_text(page)
    marker='Актуальные заказы от клиентов'
    start=text.find(marker)
    if start<0:
        return []
    section=text[start+len(marker):]
    endings=[section.find(x) for x in ('Сортировка','Заказы за последние 6 месяцев','Как это работает?') if section.find(x)>=0]
    if endings:
        section=section[:min(endings)]
    if 'Заказов не найдено' in section[:300]:
        return []
    parts=section.split('Откликнуться')
    out=[]
    for raw in parts[:-1]:
        chunk=' '.join(raw.split()).strip(' -')
        if len(chunk)<20:
            continue
        published=parse_profi_datetime(chunk,now)
        if not published or published<cutoff:
            continue
        low=chunk.lower()
        if not any(term in low for term in PROFI_REQUIRED_TERMS):
            continue
        fingerprint=hashlib.sha1((region+'|'+chunk).encode('utf-8')).hexdigest()[:14]
        out.append({
            'source':f'Profi.ru · {region}',
            'text':chunk[-2400:],
            'url':page_url+'#logolead-'+fingerprint,
            'published':published,
        })
    return out

def collect_profi(max_age_hours=72):
    merged={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch_text,url): (region,url) for region,url in PROFI_PAGES}
        for future in as_completed(futures):
            region,url=futures[future]
            try:
                page=future.result()
                rows=parse_profi_page(page,url,region,max_age_hours=max_age_hours)
            except Exception as exc:
                print('PROFI_WARN',region,type(exc).__name__)
                continue
            for item in rows:
                merged[item['url']]=item
    return list(merged.values())

def collect_markets(max_age_hours=72):
    merged={}
    items=[]
    if ENABLE_KWORK:
        items.extend(collect_kwork(max_age_hours=max_age_hours))
    if ENABLE_PROFI:
        items.extend(collect_profi(max_age_hours=max_age_hours))
    for item in items:
        merged[item['url']]=item
    return list(merged.values())

if __name__=='__main__':
    items=collect_markets(72)
    print('MARKET_ITEMS',len(items))
    for item in items[:20]:
        print(item['published'].isoformat(),item['source'],item['url'],item['text'][:140].encode('unicode_escape').decode())
