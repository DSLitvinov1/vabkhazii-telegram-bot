from web_sources import POST_RE,js_decode,parse_dt
sample=r'{likesInfo:a,id:123,foo:1,addDate:"2026-09-20T10:00:00+00:00",title:"Need logoped",post:a,URL:"\\u002Fcommunity\\u002Fx"}'
rows=POST_RE.findall(sample)
assert len(rows)==1,rows
_,raw_dt,title,path=rows[0]
assert js_decode(title)=='Need logoped'
assert js_decode(path)=='/community/x',repr(js_decode(path))
assert parse_dt(raw_dt).year==2026
print('WEB_TEST_OK')
