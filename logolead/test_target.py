import io, json
import target_ready

class Response:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return json.dumps({'ok':True,'result':{'id':123}}).encode()

seen=[]
def fake_urlopen(url,timeout=20):
    seen.append(str(url))
    return Response()

old=target_ready.urllib.request.urlopen
target_ready.urllib.request.urlopen=fake_urlopen
try:
    result=target_ready.bot_get_chat('token',123)
    assert result['ok'] is True
    assert seen and 'chat_id=123' in seen[0]
finally:
    target_ready.urllib.request.urlopen=old

print('TARGET_TEST_OK')
