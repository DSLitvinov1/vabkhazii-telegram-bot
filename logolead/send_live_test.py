"""One explicitly labelled test to dedicated speech lead recipient only."""
import os
from datetime import datetime, timezone
from delivery_preflight import verify, bot_call


def send_test(token, chat_id, caller=bot_call, verifier=verify):
    verifier(token, chat_id)
    text = (
        '🧪 Проверка LogoLead — тестовое сообщение, не заявка клиента.\\n'
        'Подтверждаем доставку уведомлений в @logopedutkina.\\n'
        'Время проверки (UTC): ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    )
    result = caller(token, 'sendMessage', {
        'chat_id': str(chat_id), 'text': text,
        'disable_web_page_preview': 'true',
    })
    mid = result.get('message_id')
    if not isinstance(mid, int) or mid <= 0:
        raise RuntimeError('Test delivery lacked Telegram message_id')
    print('LOGOLEAD_LIVE_TEST_CONFIRMED=1')
    print('LOGOLEAD_TEST_MESSAGE_ID=' + str(mid))
    return mid


if __name__ == '__main__':
    send_test(os.environ.get('LOGOLEAD_BOT_TOKEN',''),
              os.environ.get('LOGOLEAD_CHAT_ID',''))
