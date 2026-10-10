from datetime import datetime,timedelta,timezone
import lead_bot

old_count=lead_bot.GLOBAL_ROTATING_QUERIES_PER_RUN
try:
    lead_bot.GLOBAL_ROTATING_QUERIES_PER_RUN=5
    state={}
    first=lead_bot.select_search_queries(state)
    cursor1=state['query_cursor']
    second=lead_bot.select_search_queries(state)
    cursor2=state['query_cursor']
    assert all(q in first for q in lead_bot.CORE_SEARCH_QUERIES)
    assert all(q in second for q in lead_bot.CORE_SEARCH_QUERIES)
    assert len(first)==len(lead_bot.CORE_SEARCH_QUERIES)+5
    assert len(second)==len(lead_bot.CORE_SEARCH_QUERIES)+5
    assert cursor1!=cursor2
    first_rot=[q for q in first if q not in lead_bot.CORE_SEARCH_QUERIES]
    second_rot=[q for q in second if q not in lead_bot.CORE_SEARCH_QUERIES]
    assert first_rot!=second_rot
finally:
    lead_bot.GLOBAL_ROTATING_QUERIES_PER_RUN=old_count

old_discovery=lead_bot.DISCOVERY_ROTATING_QUERIES_PER_REFRESH
try:
    lead_bot.DISCOVERY_ROTATING_QUERIES_PER_REFRESH=4
    state={}
    first=lead_bot.select_discovery_queries(state)
    cursor1=state['discovery_query_cursor']
    second=lead_bot.select_discovery_queries(state)
    cursor2=state['discovery_query_cursor']
    assert all(q in first for q in lead_bot.CORE_DISCOVERY_QUERIES)
    assert len(first)==len(lead_bot.CORE_DISCOVERY_QUERIES)+4
    assert cursor1!=cursor2
finally:
    lead_bot.DISCOVERY_ROTATING_QUERIES_PER_REFRESH=old_discovery

assert 'нужен специалист по речи' in lead_bot.SEARCH_QUERIES
assert 'не получается звук р' in lead_bot.SEARCH_QUERIES
assert 'звук р' in lead_bot.DEEP_GROUP_QUERIES

now=datetime(2026,10,10,9,0,tzinfo=timezone.utc)
fresh=(60,now-timedelta(minutes=20),'fresh','u1',[],'Telegram','k1','s1')
old=(65,now-timedelta(hours=20),'old','u2',[],'Telegram','k2','s2')
very_hot=(90,now-timedelta(hours=20),'hot','u3',[],'Telegram','k3','s3')
profi=(60,now-timedelta(hours=2),'profi','u4',[],'Profi.ru · Москва','k4','s4')
kwork=(60,now-timedelta(hours=2),'kwork','u5',[],'Kwork','k5','s5')
telegram=(60,now-timedelta(hours=2),'telegram','u6',[],'Telegram: Moms','k6','s6')
assert lead_bot.candidate_priority(fresh,now)>lead_bot.candidate_priority(old,now)
assert lead_bot.candidate_priority(very_hot,now)>lead_bot.candidate_priority(fresh,now)
assert lead_bot.candidate_priority(profi,now)>lead_bot.candidate_priority(kwork,now)
assert lead_bot.candidate_priority(kwork,now)>lead_bot.candidate_priority(telegram,now)

print('PIPELINE_TEST_OK')
