import asyncio, base64, io, os, time
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
TWOFA_PASSWORD=os.environ.get('TG_2FA_PASSWORD','')

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
    response=requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
        data={
            'chat_id':CHAT_ID,
            'caption':'LogoLead: отсканируйте этот QR телефоном: Telegram → Настройки → Устройства → Подключить устройство. Если QR успеет истечь, я автоматически пришлю новый.'
        },
        files={'photo':('logolead-login.png',buf.getvalue(),'image/png')},
        timeout=30,
    )
    response.raise_for_status()
    return int((response.json().get('result') or {}).get('message_id') or 0)

def delete_message(message_id):
    if not message_id:
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage',
            data={'chat_id':CHAT_ID,'message_id':message_id},
            timeout=15,
        ).raise_for_status()
    except Exception:
        pass

def encrypt_session(session):
    key=public.PublicKey(PUBLIC_KEY.encode(),encoding.Base64Encoder())
    encrypted=public.SealedBox(key).encrypt(session.encode())
    return base64.b64encode(encrypted).decode()

async def main():
    client=TelegramClient(StringSession(),API_ID,API_HASH)
    await client.connect()
    qr_message_id=0
    try:
        qr=await client.qr_login()
        deadline=time.monotonic()+300
        while True:
            delete_message(qr_message_id)
            qr_message_id=send_qr(qr.url)
            print('QR_SENT=1',flush=True)
            try:
                await qr.wait()
                break
            except asyncio.TimeoutError:
                if time.monotonic()>=deadline:
                    raise TimeoutError('QR approval timed out')
                await qr.recreate()
                print('QR_REFRESHED=1',flush=True)
                continue
            except SessionPasswordNeededError:
                if not TWOFA_PASSWORD:
                    delete_message(qr_message_id)
                    print('SESSION_RENEW_2FA_REQUIRED=1',flush=True)
                    send_text('LogoLead: QR подтверждён, но включён облачный пароль Telegram 2FA. Добавьте его как временный GitHub Secret TG_2FA_PASSWORD и повторите обновление. Пароль в чат не отправляйте.')
                    return
                await client.sign_in(password=TWOFA_PASSWORD)
                break
        delete_message(qr_message_id)
        session=client.session.save()
        print('SESSION_RENEW_OK=1',flush=True)
        print('ENCRYPTED_SESSION='+encrypt_session(session),flush=True)
        send_text('LogoLead: новый Telegram-вход подтверждён. Система завершает безопасное обновление сессии.')
    finally:
        await client.disconnect()

if __name__=='__main__':
    asyncio.run(main())
