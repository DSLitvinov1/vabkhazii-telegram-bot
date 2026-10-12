import asyncio, base64, io, os, time
import qrcode, requests
from nacl import public
from delivery_preflight import verify
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

API_ID=os.environ.get('TG_API_ID','')
API_HASH=os.environ.get('TG_API_HASH','')
BOT_TOKEN=os.environ.get('LOGOLEAD_BOT_TOKEN','')
CHAT_ID=os.environ.get('LOGOLEAD_CHAT_ID','')
PUBLIC_KEY=os.environ.get('ENCRYPTION_PUBLIC_KEY','')
TWOFA_PASSWORD=os.environ.get('LOGOLEAD_TG_2FA_PASSWORD','')

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
    payload=response.json()
    result=payload.get('result') if isinstance(payload,dict) else None
    message_id=result.get('message_id') if isinstance(result,dict) else None
    if not isinstance(payload,dict) or payload.get('ok') is not True or type(message_id) is not int or message_id<=0:
        raise RuntimeError('Telegram did not confirm QR delivery')
    return message_id

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

def validate_public_key():
    key=public.PublicKey(base64.b64decode(PUBLIC_KEY,validate=True))
    # Reject unusable curve points before requesting any Telegram login.
    public.SealedBox(key).encrypt(b'')
    return key

def encrypt_session(session,key):
    encrypted=public.SealedBox(key).encrypt(session.encode())
    return base64.b64encode(encrypted).decode()

async def main():
    key=validate_public_key()
    verify(BOT_TOKEN,CHAT_ID)
    print('LOGOLEAD_DELIVERY_TARGET_VERIFIED=1',flush=True)
    client=TelegramClient(StringSession(),int(API_ID),API_HASH)
    qr_message_id=0
    try:
        await client.connect()
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
                    send_text('LogoLead: QR подтверждён, но включён облачный пароль Telegram 2FA. Добавьте его как временный GitHub Secret LOGOLEAD_TG_2FA_PASSWORD и повторите обновление. Пароль в чат не отправляйте.')
                    return
                await client.sign_in(password=TWOFA_PASSWORD)
                break
        delete_message(qr_message_id)
        me=await client.get_me()
        username=(getattr(me,'username',None) or '').strip().lstrip('@').casefold()
        if getattr(me,'bot',False) or username!='logopedutkina':
            await client.log_out()
            print('SESSION_OWNER_REJECTED=1',flush=True)
            send_text('LogoLead: вход отклонён: подтверждён не аккаунт @logopedutkina. Эта сессия не сохранена.')
            return
        session=client.session.save()
        # Only the encrypted payload can enter logs; key stays on user's device.
        encrypted_session=encrypt_session(session,key)
        print('ENCRYPTED_SESSION='+encrypted_session,flush=True)
        print('SESSION_RENEW_OK=1',flush=True)
        send_text('LogoLead: вход аккаунта @logopedutkina подтверждён. Передайте только зашифрованную сессию владельцу ключа для установки в GitHub Secret.')
    finally:
        delete_message(qr_message_id)
        await client.disconnect()

def run():
    try:
        asyncio.run(main())
    except Exception as exc:
        # Exceptions may contain credentials or login URLs; never print them.
        print('SESSION_RENEW_FAILED=1',flush=True)
        print('SESSION_RENEW_ERROR_TYPE='+type(exc).__name__,flush=True)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(run())

