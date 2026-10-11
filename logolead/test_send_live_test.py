from send_live_test import send_test


calls = []
def fake_caller(token, method, data=None):
    calls.append((method, data))
    return {'message_id': 123}
def fake_verifier(token, chat_id):
    assert token == 'test_token'
    assert chat_id == '321'
    return True

assert send_test('test_token','321',fake_caller,fake_verifier) == 123
assert calls and calls[0][0] == 'sendMessage'
assert 'тестовое сообщение, не заявка' in calls[0][1]['text']
print('TEST_LIVE_DELIVERY_MOCK_OK')
