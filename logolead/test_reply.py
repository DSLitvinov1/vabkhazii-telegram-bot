from reply import detect_issue
cases={
 'Ребенок картавит':'звук Р',
 'Нужна постановка звука Р':'звук Р',
 'Не выговаривает Л':'звук Л',
 'ЗРР, ищу специалиста':'ЗРР/ЗПРР',
 'Ребенок не говорит предложениями':'запуск речи',
 'Дисграфия у школьника':'дисграфия',
 'Ищу логопеда рядом с метро':'речь и произношение'}
for text,want in cases.items():
 got=detect_issue(text); print(got); assert got==want,(text,got,want)
print('REPLY_OK')
