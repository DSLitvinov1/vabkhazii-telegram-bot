import lead_bot

saved={
    'TG_API_ID':lead_bot.TG_API_ID,
    'TG_API_HASH':lead_bot.TG_API_HASH,
    'TG_SESSION':lead_bot.TG_SESSION,
    'BOT_TOKEN':lead_bot.BOT_TOKEN,
    'CHAT_ID':lead_bot.CHAT_ID,
    'DELIVERY_ENABLED':lead_bot.DELIVERY_ENABLED,
    'SEND_STATUS':lead_bot.SEND_STATUS,
}
try:
    lead_bot.TG_API_ID=1
    lead_bot.TG_API_HASH='hash'
    lead_bot.TG_SESSION='session'
    lead_bot.BOT_TOKEN=''
    lead_bot.CHAT_ID=''
    lead_bot.DELIVERY_ENABLED=False
    lead_bot.SEND_STATUS=False
    assert lead_bot.validate_config() is True

    lead_bot.DELIVERY_ENABLED=True
    try:
        lead_bot.validate_config()
        raise AssertionError('delivery without bot credentials should fail')
    except RuntimeError as exc:
        assert 'delivery credentials' in str(exc)

    lead_bot.BOT_TOKEN='token'
    lead_bot.CHAT_ID='123'
    assert lead_bot.validate_config() is True
finally:
    for key,value in saved.items():
        setattr(lead_bot,key,value)

print('CONFIG_TEST_OK')
