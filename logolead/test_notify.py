import asyncio, io, json, urllib.error, urllib.parse
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
    asyncio.run(lead_bot.notify('test message','https://t.me/test/1','https://t.me/mama_anna'))
    assert len(calls)==2,len(calls)
    body=urllib.parse.parse_qs(calls[-1].data.decode())
    assert body['chat_id']==['1']
    markup=json.loads(body['reply_markup'][0])
    buttons=markup['inline_keyboard'][0]
    assert buttons[0]['url']=='https://t.me/test/1' and buttons[0]['text']=='Открыть источник'
    assert buttons[1]['url']=='https://t.me/mama_anna' and buttons[1]['text']=='Написать автору'
    assert lead_bot.author_url_from_source('Telegram: Moms · автор @mama_anna')=='https://t.me/mama_anna'
    assert lead_bot.author_url_from_source('Kwork') is None
finally:
    lead_bot.BOT_TOKEN,lead_bot.CHAT_ID,lead_bot.BOT_SEND_RETRIES,lead_bot.urllib.request.urlopen,lead_bot.time.sleep=old

print('NOTIFY_TEST_OK')
