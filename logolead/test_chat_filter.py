import lead_bot

class FakeUser:
    username='realperson'
    broadcast=False

class FakeChat:
    def __init__(self,username,broadcast=False):
        self.username=username
        self.broadcast=broadcast

old_user=lead_bot.User
try:
    lead_bot.User=FakeUser
    assert not lead_bot.chat_allowed(FakeUser())
    assert lead_bot.chat_allowed(FakeChat('parents_public'))
    assert not lead_bot.chat_allowed(FakeChat('parents_news',broadcast=True))
    assert not lead_bot.chat_allowed(FakeChat(''))
    assert not lead_bot.chat_allowed(FakeChat('VAbkhaziiLeadsBot'))
finally:
    lead_bot.User=old_user

print('CHAT_FILTER_TEST_OK')
