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
