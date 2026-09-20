import json, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) LogoLead/1.0'
KWORK_BASE='https://kwork.ru'
KWORK_QUERIES=['логопед','дефектолог','нейрологопед','дисграфия','дислексия']

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
                if len(text)<8:
                    continue
                project_url=f'{KWORK_BASE}/projects/{project_id}/view'
                merged[project_url]={
                    'source':'Kwork',
                    'text':text[:2400],
                    'url':project_url,
                    'published':published,
                }
    return list(merged.values())

def collect_markets(max_age_hours=72):
    return collect_kwork(max_age_hours=max_age_hours)

if __name__=='__main__':
    items=collect_markets(72)
    print('MARKET_ITEMS',len(items))
    for item in items[:20]:
        print(item['published'].isoformat(),item['source'],item['url'],item['text'][:140].encode('unicode_escape').decode())
