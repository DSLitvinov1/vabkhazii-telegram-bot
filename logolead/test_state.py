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

# Rescoring after classifier update must not discard pending history backfill.
state,_ = use_state({
    'version':lead_bot.STATE_VERSION,
    'classifier_version':lead_bot.CLASSIFIER_VERSION-1,
    'seen':['old-message'],
    'group_last_ids':{'parents':900},
    'group_backfill_ids':{'parents':400},
    'sent':['already-delivered'],
})
assert state['seen'] == []
assert state['group_last_ids'] == {}
assert state['group_backfill_ids'] == {'parents':400}
assert state['sent'] == ['already-delivered']

# Persisted deliveries are never forgotten across subsequent state reloads.
state,saved=use_state({
 'version':lead_bot.STATE_VERSION,
 'classifier_version':lead_bot.CLASSIFIER_VERSION,
 'seen':[], 'sent':['acknowledged-lead'],
 'pending':[],
})
assert saved['sent']==['acknowledged-lead']

# A complete existing state must survive a failed atomic replacement.
import unittest.mock
with tempfile.TemporaryDirectory() as folder:
    d=Path(folder)
    original_dir,original_file=lead_bot.STATE_DIR,lead_bot.STATE_FILE
    try:
        lead_bot.STATE_DIR=d
        lead_bot.STATE_FILE=d/'state.json'
        lead_bot.save_state({'sent':['already-sent'],'pending':[]})
        original=d.joinpath('state.json').read_text(encoding='utf-8')
        with unittest.mock.patch.object(lead_bot.os,'replace',side_effect=OSError('storage interrupted')):
            try:
                lead_bot.save_state({'sent':['should-not-replace'],'pending':[]})
            except OSError:
                pass
            else:
                raise AssertionError('Storage failure should be exposed')
        assert d.joinpath('state.json').read_text(encoding='utf-8')==original
        assert not d.joinpath('state.json.tmp').exists()
    finally:
        lead_bot.STATE_DIR,lead_bot.STATE_FILE=original_dir,original_file

# Corruption must not silently clear sent keys and redeliver everything.
with tempfile.TemporaryDirectory() as folder:
    d=Path(folder)
    old_dir,old_file=lead_bot.STATE_DIR,lead_bot.STATE_FILE
    try:
        lead_bot.STATE_DIR=d
        lead_bot.STATE_FILE=d/'state.json'
        lead_bot.STATE_FILE.write_text('{"sent": ["already-sent"],',encoding='utf-8')
        try:
            lead_bot.load_state()
        except RuntimeError as exc:
            assert 'refusing to reset' in str(exc)
        else:
            raise AssertionError('Corrupt state was silently forgotten')
    finally:
        lead_bot.STATE_DIR,lead_bot.STATE_FILE=old_dir,old_file

# Simulate an interrupted delivery batch. A confirmed first delivery is
# checkpointed while a second unconfirmed lead remains queued for retry.
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder)
    original=(lead_bot.STATE_DIR,lead_bot.STATE_FILE)
    try:
        lead_bot.STATE_DIR=root
        lead_bot.STATE_FILE=root/'state.json'
        now=datetime.now(timezone.utc)
        pending_a={
            'text':'Ищу логопеда для дочери 7 лет. Отсутствует звук Р',
            'url':'https://t.me/example/111',
            'published':now.isoformat(),
            'source':'Telegram: parents',
        }
        pending_b={
            'text':'Ищу логопеда ребенку 5 лет, не говорит',
            'url':'https://t.me/example/222',
            'published':now.isoformat(),
            'source':'Telegram: parents',
        }
        k1=lead_bot.delivery_key(pending_a['url'],pending_a['text'])
        k2=lead_bot.delivery_key(pending_b['url'],pending_b['text'])
        lead_bot.save_state({'classifier_version':lead_bot.CLASSIFIER_VERSION,
                             'pending':[pending_a,pending_b],'sent':[]})
        state=lead_bot.load_state()
        state['sent']=[k1]
        state['pending']=[pending_b]
        lead_bot.save_state(state)
        recovered=lead_bot.load_state()
        cutoff=now-timedelta(hours=72)
        assert recovered['sent']==[k1]
        assert lead_bot.pending_to_candidate(pending_a,cutoff,{k1:None}) is None
        retried=lead_bot.pending_to_candidate(pending_b,cutoff,{k1:None})
        assert retried is not None and retried[7]==k2
        # An independent hourly run must see the same recovery snapshot.
        assert lead_bot.load_state()['pending']==[pending_b]
    finally:
        lead_bot.STATE_DIR,lead_bot.STATE_FILE=original

print('RECOVERY_AND_DEDUP_REGRESSION_OK')
