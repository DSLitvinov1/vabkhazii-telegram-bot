import asyncio
import lead_bot

assert lead_bot.parse_feedback_callback('ll:good:abcdef1234567890')==('good','abcdef1234567890')
assert lead_bot.parse_feedback_callback('ll:bad:0123456789abcdef')==('bad','0123456789abcdef')
assert lead_bot.parse_feedback_callback('bad-data') is None
assert lead_bot.feedback_counts({
    'a':{'label':'good'},
    'b':{'label':'bad'},
    'c':{'label':'good'},
})=={'good':2,'bad':1,'total':3}

calls=[]
def fake_bot_api(method,payload=None):
    calls.append((method,payload or {}))
    if method=='getUpdates':
        return {
            'ok':True,
            'result':[{
                'update_id':7,
                'callback_query':{
                    'id':'cb1',
                    'data':'ll:good:abcdef1234567890',
                    'message':{'chat':{'id':123}},
                }
            }]
        }
    return {'ok':True,'result':True}

saved=(lead_bot.ENABLE_FEEDBACK,lead_bot.BOT_TOKEN,lead_bot.CHAT_ID,lead_bot.bot_api)
lead_bot.ENABLE_FEEDBACK=True
lead_bot.BOT_TOKEN='token'
lead_bot.CHAT_ID='123'
lead_bot.bot_api=fake_bot_api
state={
    'bot_update_offset':0,
    'feedback':{},
    'feedback_index':{
        'abcdef1234567890':{'score':90,'source':'Telegram: Moms'}
    },
}
try:
    asyncio.run(lead_bot.process_feedback_updates(state))
    assert state['bot_update_offset']==8
    assert state['feedback']['abcdef1234567890']['label']=='good'
    assert state['feedback']['abcdef1234567890']['lead']['score']==90
    assert any(method=='answerCallbackQuery' for method,_ in calls)
finally:
    lead_bot.ENABLE_FEEDBACK,lead_bot.BOT_TOKEN,lead_bot.CHAT_ID,lead_bot.bot_api=saved

print('FEEDBACK_TEST_OK')
