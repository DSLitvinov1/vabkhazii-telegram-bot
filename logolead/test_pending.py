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
excluded=dict(stored); excluded['source']='Telegram: VAbkhaziiLeadsBot'
assert lead_bot.pending_to_candidate(excluded,cutoff,{}) is None
stats=lead_bot.pending_stats([
    {'source':'Telegram: moms','score':90},
    {'source':'Telegram: parents','score':60},
    {'source':'Kwork','score':80},
])
assert stats['total']==3 and stats['hot']==2
assert ('Telegram',2) in stats['sources'] and ('Kwork',1) in stats['sources']
old_age,old_max=lead_bot.DELIVERY_MAX_AGE_HOURS,lead_bot.MAX_LEADS_PER_RUN
lead_bot.DELIVERY_MAX_AGE_HOURS=24
lead_bot.MAX_LEADS_PER_RUN=1
now=datetime(2026,9,21,0,0,tzinfo=timezone.utc)
fresh=(90,now-timedelta(hours=2),'fresh','https://t.me/a/1',[],'Telegram','k1','s1')
fresh2=(80,now-timedelta(hours=3),'fresh2','https://t.me/a/2',[],'Telegram','k2','s2')
stale=(95,now-timedelta(hours=30),'stale','https://t.me/a/3',[],'Telegram','k3','s3')
try:
    batch,queued,stale_count=lead_bot.select_delivery_candidates([stale,fresh,fresh2],now)
    assert batch==[fresh]
    assert queued==[fresh2]
    assert stale_count==1
finally:
    lead_bot.DELIVERY_MAX_AGE_HOURS,lead_bot.MAX_LEADS_PER_RUN=old_age,old_max

print('PENDING_TEST_OK')
