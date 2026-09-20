import asyncio
import lead_bot

class FakeUser:
    username='realperson'
    broadcast=False
    def __init__(self,bot=False):
        self.bot=bot

class FakeChat:
    def __init__(self,username,broadcast=False):
        self.username=username
        self.broadcast=broadcast

class FakeMessage:
    def __init__(self,sender=None,fail=False):
        self.sender=sender
        self.fail=fail
    async def get_sender(self):
        if self.fail:
            raise RuntimeError('lookup failed')
        return self.sender

old_user=lead_bot.User
try:
    lead_bot.User=FakeUser
    assert not lead_bot.chat_allowed(FakeUser())
    assert lead_bot.chat_allowed(FakeChat('parents_public'))
    assert not lead_bot.chat_allowed(FakeChat('parents_news',broadcast=True))
    assert not lead_bot.chat_allowed(FakeChat(''))
    assert not lead_bot.chat_allowed(FakeChat('VAbkhaziiLeadsBot'))
    assert not asyncio.run(lead_bot.sender_allowed(FakeMessage(FakeUser(bot=True))))
    assert asyncio.run(lead_bot.sender_allowed(FakeMessage(FakeUser(bot=False))))
    assert asyncio.run(lead_bot.sender_allowed(FakeMessage(fail=True)))
finally:
    lead_bot.User=old_user

print('CHAT_FILTER_TEST_OK')
