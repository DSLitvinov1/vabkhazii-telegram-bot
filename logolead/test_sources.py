from datetime import datetime, timezone
from sources import merge_unique

now=datetime.now(timezone.utc)
items=[
    (60,now,'same text','https://x/1',['a'],'A','k1'),
    (80,now,'same text','https://x/1',['b'],'B','k2'),
    (55,now,'other','','c'.split(),'C','k3'),
    (70,now,' other  ','','d'.split(),'D','k4'),
]
merged=merge_unique(items)
assert len(merged)==2,merged
by_url={x[3]:x for x in merged}
assert by_url['https://x/1'][0]==80
assert by_url[''][0]==70
print('SOURCES_TEST_OK')
