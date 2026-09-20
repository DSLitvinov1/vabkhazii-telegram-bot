from datetime import datetime,timedelta,timezone
import lead_bot

published=datetime(2026,9,20,18,0,tzinfo=timezone.utc)
item=(90,published,'Ищу логопеда ребенку 5 лет, не выговаривает Р','https://t.me/test/1',['прямой поиск специалиста'],'Telegram: test','seen','sent')
stored=lead_bot.candidate_to_pending(item)
assert stored['url']=='https://t.me/test/1'
assert stored['published']==published.isoformat()
long_item=(90,published,'x'*2500,'https://t.me/test/2',['reason'],'Telegram: test','seen2','sent2')
assert len(lead_bot.candidate_to_pending(long_item)['text'])==2000
assert stored['sent_key']=='sent'

cutoff=published-timedelta(hours=1)
restored=lead_bot.pending_to_candidate(stored,cutoff,{})
assert restored is not None
assert restored[0]>=50
assert restored[3]=='https://t.me/test/1'
assert restored[7]==lead_bot.delivery_key(restored[3],restored[2])

assert lead_bot.pending_to_candidate(stored,published+timedelta(seconds=1),{}) is None
assert lead_bot.pending_to_candidate(stored,cutoff,{restored[7]:None}) is None

print('PENDING_TEST_OK')
