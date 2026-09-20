import asyncio, io, json, urllib.error
import lead_bot

class Response:
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,*args):
        return b'{"ok":true}'

calls=[]
def fake_urlopen(req,timeout=20):
    calls.append(req)
    if len(calls)==1:
        body=io.BytesIO(json.dumps({'ok':False,'parameters':{'retry_after':1}}).encode())
        raise urllib.error.HTTPError(req.full_url,429,'Too Many Requests',None,body)
    return Response()

old=(lead_bot.BOT_TOKEN,lead_bot.CHAT_ID,lead_bot.BOT_SEND_RETRIES,lead_bot.urllib.request.urlopen,lead_bot.time.sleep)
lead_bot.BOT_TOKEN='test'
lead_bot.CHAT_ID='1'
lead_bot.BOT_SEND_RETRIES=1
lead_bot.urllib.request.urlopen=fake_urlopen
lead_bot.time.sleep=lambda _:None
try:
    asyncio.run(lead_bot.notify('test message'))
    assert len(calls)==2,len(calls)
finally:
    lead_bot.BOT_TOKEN,lead_bot.CHAT_ID,lead_bot.BOT_SEND_RETRIES,lead_bot.urllib.request.urlopen,lead_bot.time.sleep=old

print('NOTIFY_TEST_OK')
