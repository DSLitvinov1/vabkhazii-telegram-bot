from web_sources import POST_RE,js_decode,parse_dt,woman_thread_datetime,woman_title_relevant

sample=r'{likesInfo:a,id:123,foo:1,addDate:"2026-09-20T10:00:00+00:00",title:"Need logoped",post:a,URL:"\\u002Fcommunity\\u002Fx"}'
rows=POST_RE.findall(sample)
assert len(rows)==1,rows
_,raw_dt,title,path=rows[0]
assert js_decode(title)=='Need logoped'
assert js_decode(path)=='/community/x',repr(js_decode(path))
assert parse_dt(raw_dt).year==2026

woman_page='<script>{"datePublished":"2026-09-20T08:08:58+0300"}</script>'
dt=woman_thread_datetime(woman_page)
assert dt is not None and dt.year==2026 and dt.tzinfo is not None
assert woman_title_relevant('Нужен логопед ребенку 5 лет')
assert woman_title_relevant('Ребёнок плохо говорит, что делать?')
assert not woman_title_relevant('Мужчина говорит, что любит, но денег нет')
assert not woman_title_relevant('Дочь поздно возвращается домой')

print('WEB_TEST_OK')

# The production forum collector must include all three independent sources.
import web_sources as ws
from datetime import datetime,timezone
now=datetime.now(timezone.utc)
def make_item(source, url):
    return {'source':source, 'url':url,'text':'Ребёнку 3 года нужен логопед',
            'published':now}
_originals=(ws.collect_babyblog,ws.collect_umama,ws.collect_woman)
try:
    ws.collect_babyblog=lambda max_age_hours=72:[make_item('Babyblog','https://babyblog.ru/test')]
    ws.collect_umama=lambda max_age_hours=72:[make_item('U-mama','https://u-mama.ru/test')]
    ws.collect_woman=lambda max_age_hours=72:[make_item('Woman.ru','https://woman.ru/test')]
    sources=ws.collect_web(72)
    assert len(sources)==3
    assert {item['source'] for item in sources}=={'Babyblog','U-mama','Woman.ru'}
finally:
    ws.collect_babyblog,ws.collect_umama,ws.collect_woman=_originals

from web_sources import choose_umama_topics, UMAMA_INDEXES
items=[('https://u-mama.ru/a','Новый сад'),
       ('https://u-mama.ru/b','Новости школы'),
       ('https://u-mama.ru/c','Нужен логопед, ребенок не говорит'),
       ('https://u-mama.ru/d','Задержка речи, что делать')]
subset=choose_umama_topics(items,3)
assert len(subset)==3
assert any('логопед' in title.lower() for _,title in subset)
assert any('задержка речи' in title.lower() for _,title in subset)
assert '/forum/kids/kindergarten/' in UMAMA_INDEXES
assert '/forum/kids/schoolboy/' in UMAMA_INDEXES
