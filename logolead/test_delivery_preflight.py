from delivery_preflight import verify


def fake(token, method, data=None):
    if method == 'getMe':
        return {'is_bot': True, 'username': 'LogoLeadSpeechFinderBot'}
    if method == 'getChat':
        return {'id': int(data['chat_id']), 'type': 'private',
                'username': 'logopedutkina'}
    raise AssertionError(method)


assert verify('test-token', '123', fake)
for token, chat in [('', '123'), ('test-token', ''), ('test-token', 'abc')]:
    try:
        verify(token, chat, fake)
    except RuntimeError:
        pass
    else:
        raise AssertionError('unconfigured delivery should be blocked')


def wrong_bot(token, method, data=None):
    if method == 'getMe':
        return {'is_bot': True, 'username': 'VAbkhaziiLeadsBot'}
    return fake(token, method, data)


try:
    verify('token', '123', wrong_bot)
except RuntimeError:
    pass
else:
    raise AssertionError('wrong bot should be blocked')


def wrong_user(token, method, data=None):
    if method == 'getChat':
        return {'id': 123, 'type': 'private', 'username': 'otheruser'}
    return fake(token, method, data)


try:
    verify('token', '123', wrong_user)
except RuntimeError:
    pass
else:
    raise AssertionError('wrong target should be blocked')
print('DELIVERY_PREFLIGHT_TEST_OK')
