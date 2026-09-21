from datetime import datetime, timezone
from sources import merge_unique,content_signature

now=datetime.now(timezone.utc)
long_text='Ищу хорошего логопеда для ребёнка пяти лет. Не выговаривает несколько звуков и хотелось бы начать занятия в ближайшее время.'
items=[
    (60,now,'same text','https://x/1',['a'],'A','k1'),
    (80,now,'same text','https://x/1',['b'],'B','k2'),
    (55,now,'other','','c'.split(),'C','k3'),
    (70,now,' other  ','','d'.split(),'D','k4'),
    (75,now,long_text,'https://x/2',['e'],'E','k5'),
    (65,now,long_text,'https://x/3',['f'],'F','k6'),
]
merged=merge_unique(items)
assert len(merged)==3,merged
assert max(x[0] for x in merged if x[2]=='same text')==80
assert max(x[0] for x in merged if x[2].strip()=='other')==70
long_matches=[x for x in merged if x[2]==long_text]
assert len(long_matches)==1 and long_matches[0][0]==75
assert content_signature(long_text,'https://x/2')==content_signature(long_text,'https://x/3')
mid='Посоветуйте хорошего логопеда ребёнку пяти лет'
assert len(mid)>=40
assert content_signature(mid,'https://x/2')==content_signature(mid,'https://x/3')
assert content_signature('short','https://x/2')!=content_signature('short','https://x/3')
print('SOURCES_TEST_OK')
