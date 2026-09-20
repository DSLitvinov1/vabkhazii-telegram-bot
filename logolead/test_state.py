import json,tempfile
from pathlib import Path
import lead_bot

def use_state(payload):
 tmp=tempfile.TemporaryDirectory()
 state_dir=Path(tmp.name)/'.lead_state'; state_file=state_dir/'state.json'; state_dir.mkdir()
 state_file.write_text(json.dumps(payload),encoding='utf-8')
 old_dir,old_file=lead_bot.STATE_DIR,lead_bot.STATE_FILE
 lead_bot.STATE_DIR,lead_bot.STATE_FILE=state_dir,state_file
 try:
  state=lead_bot.load_state(); lead_bot.save_state(state)
  saved=json.loads(state_file.read_text(encoding='utf-8'))
  return state,saved
 finally:
  lead_bot.STATE_DIR,lead_bot.STATE_FILE=old_dir,old_file
  tmp.cleanup()

state,saved=use_state({'version':2,'classifier_version':1,'seen':['a','b'],'sent':['sent1'],'pending':[{'text':'lead'}],'group_last_ids':{'x':10},'last_run':'2026-09-20T10:00:00+00:00','last_market_run':'2026-09-20T10:00:00+00:00'})
assert state['seen']==[]
assert state['group_last_ids']=={}
assert state['sent']==['sent1']
assert state['pending']==[{'text':'lead'}]
assert 'last_run' not in state and 'last_market_run' not in state
assert state['classifier_version']==lead_bot.CLASSIFIER_VERSION
assert saved['version']==lead_bot.STATE_VERSION

state,_=use_state({
 'version':lead_bot.STATE_VERSION,'classifier_version':lead_bot.CLASSIFIER_VERSION,
 'seen':['a','b'],'sent':['sent1','sent2'],'groups':{'abc':'ABC'},
 'group_last_ids':{'abc':123},'group_scan_cursor':4,
})
assert state['seen']==['a','b']
assert state['sent']==['sent1','sent2']
assert state['groups']=={'abc':'ABC'}
assert state['group_last_ids']=={'abc':123}

assert lead_bot.message_key(123,456)==lead_bot.message_key(123,456)
assert lead_bot.message_key('ParentsChat',456)==lead_bot.message_key('@parentschat',456)
assert lead_bot.message_key(123,456)!=lead_bot.message_key(123,457)
assert lead_bot.delivery_key('https://t.me/a/1','one')==lead_bot.delivery_key('https://t.me/a/1','two')
assert lead_bot.delivery_key('','  Same   Text ')==lead_bot.delivery_key('','same text')
long_text='Ищу хорошего логопеда для ребёнка пяти лет. Не выговаривает несколько звуков и хотелось бы начать занятия в ближайшее время.'
assert lead_bot.delivery_key('https://t.me/a/2',long_text)==lead_bot.delivery_key('https://t.me/b/3',long_text)
assert lead_bot.delivery_key('https://t.me/a/2','short')!=lead_bot.delivery_key('https://t.me/b/3','short')
from datetime import datetime,timedelta,timezone
published=datetime(2026,9,20,18,0,tzinfo=timezone.utc)
now=published+timedelta(minutes=37)
assert lead_bot.format_published(published,now)=='20.09 21:00 МСК · 37 мин назад'
assert lead_bot.freshness_text(published,published+timedelta(hours=2,minutes=5))=='2 ч назад'
assert lead_bot.freshness_text(published,published+timedelta(days=2,hours=1))=='2 дн назад'
print('STATE_TEST_OK')
