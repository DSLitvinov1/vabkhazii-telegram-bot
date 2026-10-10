import json
from datetime import datetime,timezone
import market_sources

payload={
  'pagination':{
    'data':[{
      'id':123,
      'status':'active',
      'isWantActive':True,
      'name':'Нужен логопед ребёнку',
      'description':'Ребёнку 5 лет, не выговаривает Р',
      'date_create':'2026-09-20 17:43:21',
      'priceLimit':'1500.00',
    }]
  }
}
page='prefix "wantsListData":'+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+',suffix'
raw=market_sources.extract_json_object_after(page,'"wantsListData":')
assert raw is not None
state=json.loads(raw)
assert state['pagination']['data'][0]['id']==123
dt=market_sources.parse_kwork_datetime('2026-09-20 17:43:21')
assert dt is not None and dt.tzinfo==timezone.utc
text=market_sources.kwork_project_text(payload['pagination']['data'][0])
assert 'Нужен логопед ребёнку' in text and 'Бюджет: 1500.00' in text
assert market_sources.is_kwork_relevant(text)
assert not market_sources.is_kwork_relevant('Нужен монтаж видео и дизайн лендинга')

now=datetime(2026,10,10,12,0,tzinfo=timezone.utc)
profi_page='''
<html><body>
<h2>Актуальные заказы от клиентов</h2>
<div><h3>Логопед (постановка звуков)</h3>
<p>Ребёнку 5 лет, не выговаривает звук Р. Нужны занятия онлайн.</p>
<span>2 часа назад</span><button>Откликнуться</button></div>
<div><h3>Логопед-дефектолог</h3><p>Ребёнку 6 лет, ЗРР.</p>
<span>9 октября 2026</span><button>Откликнуться</button></div>
<div>Сортировка</div>
</body></html>
'''
rows=market_sources.parse_profi_page(
    profi_page,'https://profi.ru/rabota/repetitor/logopedy/','Москва',72,now)
assert len(rows)==2,rows
assert rows[0]['source']=='Profi.ru · Москва'
assert rows[0]['published']==datetime(2026,10,10,10,0,tzinfo=timezone.utc)
assert rows[0]['url'].startswith('https://profi.ru/rabota/repetitor/logopedy/#logolead-')
assert rows[1]['published'].date().isoformat()=='2026-10-09'
assert market_sources.parse_profi_datetime('3 дня назад',now)==datetime(2026,10,7,12,0,tzinfo=timezone.utc)
assert market_sources.parse_profi_datetime('позавчера',now)==datetime(2026,10,8,12,0,tzinfo=timezone.utc)
assert market_sources.parse_profi_datetime('35 минут назад',now)==datetime(2026,10,10,11,25,tzinfo=timezone.utc)
assert market_sources.parse_profi_page(
    '<h2>Актуальные заказы от клиентов</h2><p>Заказов не найдено</p><div>Сортировка</div>',
    'https://profi.ru/x','Москва',72,now)==[]

print('MARKET_TEST_OK')
