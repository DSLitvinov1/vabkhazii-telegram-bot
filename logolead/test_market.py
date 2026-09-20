import json
from datetime import timezone
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
print('MARKET_TEST_OK')
