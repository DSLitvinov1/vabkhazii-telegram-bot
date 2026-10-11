from telethon.sessions import StringSession
from telethon.crypto.authkey import AuthKey
from session_compat import normalize_tg_session

session = StringSession()
session.set_dc(2, '149.154.167.50', 443)
session.auth_key = AuthKey(bytes(range(256)))
secret = session.save()
assert secret.startswith('1')
assert normalize_tg_session(secret) == secret
assert normalize_tg_session('\nOut: ' + secret + '\nDone') == secret
assert normalize_tg_session('') == ''
try:
    normalize_tg_session('bad string')
except RuntimeError:
    pass
else:
    raise AssertionError('invalid session must fail closed')
print('SESSION_COMPAT_TEST_OK')
