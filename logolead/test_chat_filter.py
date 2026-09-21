import asyncio
import lead_bot

class FakeUser:
    username='realperson'
    first_name='Real'
    last_name='Person'
    broadcast=False
    def __init__(self,bot=False,username=None,first_name=None,last_name=None):
        self.bot=bot
        if username is not None:self.username=username
        if first_name is not None:self.first_name=first_name
        if last_name is not None:self.last_name=last_name

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

    ok,author,reason=asyncio.run(lead_bot.sender_info(FakeMessage(FakeUser(bot=True))))
    assert not ok and reason=='сообщение бота'
    ok,author,reason=asyncio.run(lead_bot.sender_info(FakeMessage(FakeUser(username='mama_anna'))))
    assert ok and author=='@mama_anna' and not reason
    ok,author,reason=asyncio.run(lead_bot.sender_info(FakeMessage(FakeUser(username='logoped_maria'))))
    assert not ok and reason=='профиль специалиста'
    ok,author,reason=asyncio.run(lead_bot.sender_info(FakeMessage(fail=True)))
    assert ok and author=='' and reason==''
    assert lead_bot.telegram_source('Мамы Москвы','@anna')=='Telegram: Мамы Москвы · автор @anna'
finally:
    lead_bot.User=old_user

print('CHAT_FILTER_TEST_OK')
