from classifier import score,extract
from card import build
cases=[('direct','Посоветуйте логопеда ребенку 5 лет, не выговаривает Р, онлайн',85),('seller','Я логопед, набираю детей на занятия',0),('job','Вакансия логопед. Ищем логопеда в команду, зарплата 80000',0),('urgent','Срочно нужен дефектолог, ребенку 4 года, Москва',75),('problem','Ребенок плохо говорит, ЗРР. Ищу логопеда очно в Краснодаре',85),('weak','Кто-нибудь знает хорошего логопеда?',25)]
for name,text,minimum in cases:
 s,r=score(text); print(name,s,extract(text),r); assert (s==0) if minimum==0 else (s>=minimum)
s,r=score(cases[0][1]); card=build(cases[0][1],'https://t.me/test/1','TEST',s,r,'now')
assert '90/100' in card and 'https://t.me/test/1' in card and '5' in card
print('ALL_TESTS_OK')
