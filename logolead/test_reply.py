from reply import detect_issue,draft_reply,draft_market_reply,age_word

cases={
 'Ребенок картавит':'звук Р',
 'Нужна постановка звука Р':'звук Р',
 'Не выговаривает Л':'звук Л',
 'ЗРР, ищу специалиста':'ЗРР/ЗПРР',
 'Ребенок не говорит предложениями':'запуск речи',
 'Дисграфия у школьника':'дисграфия',
 'Ищу логопеда рядом с метро':'речь и произношение',
}
for text,want in cases.items():
 got=detect_issue(text)
 print(got)
 assert got==want,(text,got,want)

assert age_word(1)=='год'
assert age_word(2)=='года'
assert age_word(5)=='лет'
assert age_word(1.5)=='года'
reply=draft_reply('Ищу логопеда ребёнку 5 лет, не выговаривает Р, онлайн')
assert 'Ребёнку 5 лет' in reply
assert 'возраст ребёнка' not in reply
assert 'онлайн-формате' in reply
market=draft_market_reply('Нужен логопед ребёнку 5 лет, не выговаривает Р')
assert 'Готов(а) помочь' in market and '5 лет' in market
print('REPLY_OK')
