import asyncio, base64, io, os
import qrcode, requests
from nacl import encoding, public
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

API_ID=int(os.environ['TG_API_ID'])
API_HASH=os.environ['TG_API_HASH']
BOT_TOKEN=os.environ['LEADS_BOT_TOKEN']
CHAT_ID=os.environ['LEADS_CHAT_ID']
PUBLIC_KEY=os.environ['ENCRYPTION_PUBLIC_KEY']

def send_text(text):
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id':CHAT_ID,'text':text},
        timeout=30,
    ).raise_for_status()

def send_qr(url):
    image=qrcode.make(url)
    buf=io.BytesIO()
    image.save(buf,format='PNG')
    buf.seek(0)
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
        data={
            'chat_id':CHAT_ID,
            'caption':'LogoLead: отсканируйте этот QR телефоном: Telegram → Настройки → Устройства → Подключить устройство. QR действует около 3 минут.'
        },
        files={'photo':('logolead-login.png',buf.getvalue(),'image/png')},
        timeout=30,
    ).raise_for_status()

def encrypt_session(session):
    key=public.PublicKey(PUBLIC_KEY.encode(),encoding.Base64Encoder())
    encrypted=public.SealedBox(key).encrypt(session.encode())
    return base64.b64encode(encrypted).decode()

async def main():
    client=TelegramClient(StringSession(),API_ID,API_HASH)
    await client.connect()
    try:
        qr=await client.qr_login()
        send_qr(qr.url)
        print('QR_SENT=1',flush=True)
        try:
            await qr.wait(timeout=180)
        except SessionPasswordNeededError:
            print('SESSION_RENEW_2FA_REQUIRED=1',flush=True)
            send_text('LogoLead: QR подтверждён, но в Telegram включён облачный пароль 2FA. Для завершения потребуется ещё один безопасный шаг.')
            raise
        session=client.session.save()
        print('SESSION_RENEW_OK=1',flush=True)
        print('ENCRYPTED_SESSION='+encrypt_session(session),flush=True)
        send_text('LogoLead: новый Telegram-вход подтверждён. Система завершает безопасное обновление сессии.')
    finally:
        await client.disconnect()

if __name__=='__main__':
    asyncio.run(main())
