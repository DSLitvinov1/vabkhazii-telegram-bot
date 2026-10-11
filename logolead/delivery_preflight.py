"""Fail closed unless the dedicated speech bot can address its intended user."""
import json
import os
import urllib.parse
import urllib.request

BOT_USERNAME = 'logoleadspeechfinderbot'
RECIPIENT_USERNAME = 'logopedutkina'


def bot_call(token, method, data=None, opener=None):
    opener = opener or urllib.request.urlopen
    payload = urllib.parse.urlencode(data or {}).encode('utf-8')
    request = urllib.request.Request(
        'https://api.telegram.org/bot' + token + '/' + method,
        data=payload, method='POST')
    with opener(request, timeout=20) as response:
        result = json.loads(response.read(12000))
    if result.get('ok') is not True or not isinstance(result.get('result'), dict):
        raise RuntimeError('Telegram preflight returned no valid result')
    return result['result']


def verify(token, chat_id, caller=bot_call):
    if not token:
        raise RuntimeError('LOGOLEAD_BOT_TOKEN missing')
    if not chat_id or not str(chat_id).isdigit() or int(chat_id) <= 0:
        raise RuntimeError('LOGOLEAD_CHAT_ID must be a positive private user ID')
    me = caller(token, 'getMe')
    if me.get('is_bot') is not True or str(me.get('username','')).lower() != BOT_USERNAME:
        raise RuntimeError('Unexpected bot identity; delivery blocked')
    chat = caller(token, 'getChat', {'chat_id': str(chat_id)})
    if str(chat.get('id')) != str(chat_id) or chat.get('type') != 'private':
        raise RuntimeError('Unexpected target chat; delivery blocked')
    if str(chat.get('username','')).lower() != RECIPIENT_USERNAME:
        raise RuntimeError('Target username does not match; delivery blocked')
    return True


if __name__ == '__main__':
    verify(os.environ.get('LOGOLEAD_BOT_TOKEN',''),
           os.environ.get('LOGOLEAD_CHAT_ID',''))
    print('LOGOLEAD_DELIVERY_TARGET_VERIFIED=1')
