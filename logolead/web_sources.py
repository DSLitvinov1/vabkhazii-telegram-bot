import html,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
SOURCES=[
 {'name':'Babyblog','domain':'babyblog.ru','queries':['site:babyblog.ru логопед "нужен логопед"','site:babyblog.ru "посоветуйте логопеда"','site:babyblog.ru "не выговаривает" логопед']},
 {'name':'Woman.ru','domain':'woman.ru','queries':['site:woman.ru логопед ребенку "нужен"','site:woman.ru "посоветуйте логопеда"']},
 {'name':'U-mama','domain':'u-mama.ru','queries':['site:u-mama.ru "нужен логопед"','site:u-mama.ru "посоветуйте логопеда"']},
 {'name':'Littleone','domain':'littleone.com','queries':['site:littleone.com "нужен логопед"','site:littleone.com "посоветуйте логопеда"']},
]
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) LogoLead/1.0'
def clean(s):return html.unescape(re.sub(r'<[^>]+>',' ',s or '')).strip()
def bing_rss(query,source,limit=20):
 params={'q':query,'format':'rss','count':str(limit),'mkt':'ru-RU','setlang':'ru'}
 url='https://www.bing.com/search?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml'})
 with urllib.request.urlopen(req,timeout=15) as r: raw=r.read(1500000)
 root=ET.fromstring(raw); out=[]
 for node in root.findall('.//item'):
  link=clean(node.findtext('link')); title=clean(node.findtext('title')); desc=clean(node.findtext('description'))
  if source['domain'] not in urllib.parse.urlparse(link).netloc.lower():continue
  text=' '.join((title+' '+desc).split()).strip()
  if len(text)>=8:out.append({'source':source['name'],'text':text[:2200],'url':link})
 return out
def collect_web(max_per_source=20):
 merged={}
 for source in SOURCES:
  for q in source['queries']:
   try:
    for item in bing_rss(q,source,max_per_source):merged[item['url']]=item
   except Exception as e:print('WEB_WARN',source['name'],type(e).__name__)
 return list(merged.values())
if __name__=='__main__':
 xs=collect_web(5);print('WEB_ITEMS',len(xs))
 for x in xs[:10]:print(x['source'],x['url'],x['text'][:100])
