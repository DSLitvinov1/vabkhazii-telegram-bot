import lead_bot
cases=[
 ('direct','Посоветуйте логопеда ребенку 5 лет, не выговаривает Р, онлайн',85),
 ('seller','Я логопед, набираю детей на занятия',0),
 ('urgent','Нужен дефектолог срочно, ребенку 4 года',70),
 ('seller2','Услуги логопеда, запись на занятия',0),
]
failed=0
for name,text,minimum in cases:
 score,reasons=lead_bot.score(text)
 print(name,score,reasons)
 if score < minimum: failed+=1
raise SystemExit(1 if failed else 0)
