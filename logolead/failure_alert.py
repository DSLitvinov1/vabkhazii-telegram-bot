"""Send errors only to the speech-therapy recipient, never travel groups."""
import os
from delivery_preflight import bot_call, verify


def alert():
    token = os.environ.get('LOGOLEAD_BOT_TOKEN', '')
    chat_id = os.environ.get('LOGOLEAD_CHAT_ID', '')
    try:
        verify(token, chat_id)
        result = bot_call(token, 'sendMessage', {
            'chat_id': chat_id,
            'text': '⚠️ LogoLead: проверка заявок завершилась ошибкой. '
                    'Состояние запуска: ' + os.environ.get('RUN_URL',''),
            'disable_web_page_preview': 'true',
        })
        if not result.get('message_id'):
            raise RuntimeError('Alert not acknowledged by Telegram')
        print('LOGOLEAD_FAILURE_ALERT_CONFIRMED=1')
    except Exception as exc:
        print('LOGOLEAD_FAILURE_ALERT_UNAVAILABLE', type(exc).__name__)


if __name__ == '__main__':
    alert()
