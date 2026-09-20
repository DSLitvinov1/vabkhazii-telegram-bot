import html, json, re, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) LogoLead/1.0'
BABYBLOG_BASE='https://www.babyblog.ru'
UMAMA_BASE='https://u-mama.ru'
WOMAN_BASE='https://www.woman.ru'
WOMAN_FORUM='/forum/?sort=new'
WOMAN_STRONG_TERMS=('логопед','дефектолог','нейрологопед','зрр','зпрр','дисграф','дислекс','задержка речи','запуск речи')
WOMAN_SPEECH_TERMS=('речь','говорит','разговаривает','выговаривает','произносит','картавит','шепеляв','заика','не говорит','не разговаривает')
WOMAN_CHILD_TERMS=('ребенок','ребёнок','ребенку','ребёнку','дочь','дочка','сын','сыну','малыш','малышка','дети','ребята')
UMAMA_INDEXES=('/forum/last/','/forum/kids/1-3/','/forum/kids/3-7/','/forum/kids/special-child/','/forum/kids/child-health/')
UMAMA_CATEGORIES=('/forum/kids/1-3/','/forum/kids/3-7/','/forum/kids/schoolboy/','/forum/kids/special-child/','/forum/kids/child-health/')
BABYBLOG_FEEDS=[
    '/community/3_6_study',
    '/community/education',
    '/community/bolshiedeti',
    '/community/logoped-defectolog',
]
POST_RE=re.compile(
    r'\{likesInfo:[^,]*,id:(\d+).*?addDate:"([^"]+)".*?title:"((?:\\.|[^"])*)".*?URL:"((?:\\.|[^"])*)"',
    re.S,
)

def fetch_text(url, limit=2_500_000):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ru-RU,ru;q=0.9'})
    with urllib.request.urlopen(req,timeout=15) as r:
        return r.read(limit).decode('utf-8','ignore')

def js_decode(value):
    value=value or ''
    for _ in range(2):
        try:value=json.loads('"'+value.replace('"','\\"')+'"')
        except Exception:break
    return html.unescape(value)

def meta_description(page):
    for tag in re.findall(r'<meta\b[^>]*>',page or '',re.I):
        low=tag.lower()
        if 'og:description' not in low and 'name="description"' not in low and "name='description'" not in low:continue
        m=re.search(r"content=['\"]([^'\"]*)",tag,re.I)
        if m:return ' '.join(html.unescape(m.group(1)).split())
    return ''

def parse_dt(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:return None

def collect_babyblog(max_age_hours=72, max_posts_per_feed=12):
    cutoff=datetime.now(timezone.utc)-timedelta(hours=max_age_hours)
    out={}
    for feed in BABYBLOG_FEEDS:
        try:page=fetch_text(BABYBLOG_BASE+feed)
        except Exception as e:
            print('BABYBLOG_FEED_WARN',feed,type(e).__name__);continue
        fresh=[]
        for _,raw_dt,raw_title,raw_path in POST_RE.findall(page):
            dt=parse_dt(raw_dt)
            if not dt or dt<cutoff:continue
            title=js_decode(raw_title);path=js_decode(raw_path)
            if not path.startswith('/'):continue
            fresh.append((dt,title,BABYBLOG_BASE+path))
        fresh.sort(key=lambda x:x[0],reverse=True)
        for dt,title,url in fresh[:max_posts_per_feed]:
            if url in out:continue
            try:desc=meta_description(fetch_text(url,600_000))
            except Exception as e:
                print('BABYBLOG_POST_WARN',type(e).__name__);desc=''
            text=' '.join((title+' '+desc).split())
            if len(text)>=8:out[url]={'source':'Babyblog','text':text[:2200],'url':url,'published':dt}
    return list(out.values())

def clean_fragment(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',value or '')).split())

def collect_umama(max_age_hours=72, max_topics=30):
    cutoff=datetime.now(timezone.utc)-timedelta(hours=max_age_hours)
    link_re=re.compile(r'<a[^>]+href="(?P<href>(?:https://u-mama\.ru)?/forum/kids/[^"]+/\d+/)"[^>]*>(?P<label>.*?)</a>',re.S|re.I)
    topics=[];seen=set()
    for index_path in UMAMA_INDEXES:
        try:index=fetch_text(UMAMA_BASE+index_path,900_000)
        except Exception as e:
            print('UMAMA_INDEX_WARN',index_path,type(e).__name__);continue
        for m in link_re.finditer(index):
            path=m.group('href')
            if path.startswith('http'):path=urllib.parse.urlsplit(path).path
            if not any(path.startswith(cat) for cat in UMAMA_CATEGORIES):continue
            url=UMAMA_BASE+path
            if url in seen:continue
            title=clean_fragment(m.group('label'))
            if not title or title.isdigit():continue
            seen.add(url);topics.append((url,title))
            if len(topics)>=max_topics:break
        if len(topics)>=max_topics:break
    out=[]
    for url,title in topics:
        try:page=fetch_text(url,700_000)
        except Exception as e:
            print('UMAMA_TOPIC_WARN',type(e).__name__);continue
        m=re.search(r'class="[^"]*message-date[^"]*"[^>]*data-utime="(\d+)"',page,re.I)
        if not m:continue
        dt=datetime.fromtimestamp(int(m.group(1)),timezone.utc)
        if dt<cutoff:continue
        desc=meta_description(page)
        text=' '.join((title+' '+desc).split())
        if len(text)>=8:out.append({'source':'U-mama','text':text[:2200],'url':url,'published':dt})
    return out

def woman_title_relevant(title):
    low=(title or '').lower()
    strong=any(term in low for term in WOMAN_STRONG_TERMS)
    speech_child=any(term in low for term in WOMAN_SPEECH_TERMS) and any(term in low for term in WOMAN_CHILD_TERMS)
    return strong or speech_child


def woman_thread_datetime(page):
    match=re.search(r'"datePublished"\s*:\s*"([^"]+)"',page or '',re.I)
    if match:
        value=match.group(1)
        try:
            return datetime.strptime(value,'%Y-%m-%dT%H:%M:%S%z').astimezone(timezone.utc)
        except Exception:
            dt=parse_dt(value)
            if dt:return dt.astimezone(timezone.utc)
    match=re.search(r'publicationDate\\":\{\\"timestamp\\":(\d+)',page or '',re.I)
    if match:
        return datetime.fromtimestamp(int(match.group(1)),timezone.utc)
    return None

def collect_woman(max_age_hours=72,max_threads=80,max_fetch=15):
    cutoff=datetime.now(timezone.utc)-timedelta(hours=max_age_hours)
    try:
        index=fetch_text(WOMAN_BASE+WOMAN_FORUM,1_000_000)
    except Exception as exc:
        print('WOMAN_INDEX_WARN',type(exc).__name__)
        return []
    link_re=re.compile(r'<a[^>]+href=["\'](?P<href>(?:https://www\.woman\.ru)?/[^"\']*thread-[^"\']+)["\'][^>]*>(?P<label>.*?)</a>',re.S|re.I)
    topics=[];seen=set()
    for match in link_re.finditer(index):
        href=html.unescape(match.group('href'))
        if href.startswith('http'):
            path=urllib.parse.urlsplit(href).path
        else:
            path=href
        url=WOMAN_BASE+path
        if url in seen:continue
        title=clean_fragment(match.group('label'))
        if not title:continue
        seen.add(url)
        if woman_title_relevant(title):
            topics.append((url,title))
        if len(seen)>=max_threads:break
    out=[]
    for url,title in topics[:max_fetch]:
        try:
            page=fetch_text(url,800_000)
        except Exception as exc:
            print('WOMAN_TOPIC_WARN',type(exc).__name__)
            continue
        published=woman_thread_datetime(page)
        if not published or published<cutoff:continue
        desc=meta_description(page)
        text=' '.join((title+' '+desc).split())
        if len(text)>=8:
            out.append({'source':'Woman.ru','text':text[:2200],'url':url,'published':published})
    return out

def collect_cloud_web(max_age_hours=72):
    return collect_woman(max_age_hours=max_age_hours)

def collect_web(max_age_hours=72):
    merged={}
    for item in (
        collect_babyblog(max_age_hours=max_age_hours)
        +collect_umama(max_age_hours=max_age_hours)
        +collect_woman(max_age_hours=max_age_hours)
    ):
        merged[item['url']]=item
    return list(merged.values())

if __name__=='__main__':
    xs=collect_cloud_web(72)
    print('WEB_ITEMS',len(xs))
    for x in xs[:30]:
        print(x['published'].isoformat(),x['source'],x['url'],x['text'][:120].encode('unicode_escape').decode())
