from classifier import score,extract
from card import build

cases=[
 ('direct','Посоветуйте логопеда ребенку 5 лет, не выговаривает Р, онлайн',85),
 ('consult','Нужна консультация логопеда для ребенка 4 года',60),
 ('seller','Я логопед, набираю детей на занятия',0),
 ('seller2','Логопед онлайн. Провожу занятия, запись открыта',0),
 ('job','Вакансия логопед. Ищем логопеда в команду, зарплата 80000',0),
 ('job2','Ищем логопеда на работу, график работы 2/2',0),
 ('urgent','Срочно нужен дефектолог, ребенку 4 года, Москва',75),
 ('problem','Ребенок плохо говорит, ЗРР. Ищу логопеда очно в Краснодаре',85),
 ('implicit','Ребенок 3 года не говорит, куда обратиться?',55),
 ('implicit2','Ребёнку 4, мало говорит. Что делать?',55),
 ('need-question','Нужен ли логопед? Ребёнок не строит предложения',50),
 ('speech-specialist','Порекомендуйте специалиста по речи ребенку 6 лет',60),
 ('direct-question','Кто-нибудь знает хорошего логопеда?',55),
 ('short-request','Логопед ребенку 5 лет, Москва',60),
 ('contact-request','Поделитесь контактом логопеда для ребёнка',55),
]
for name,text,minimum in cases:
 value,reasons=score(text)
 print(name,value,extract(text),reasons)
 assert (value==0) if minimum==0 else (value>=minimum),(name,value,minimum)

assert extract('Ребенку 1,5 года, почти не говорит')['age']==1.5
assert extract('Дочке 5, не выговаривает Р')['age']==5
assert extract('Пишу сочинение про развитие речи')['city'] is None
assert extract('Ищу логопеда в СПб')['city']=='Санкт-Петербург'
value,reasons=score(cases[0][1])
card=build(cases[0][1],'https://t.me/test/1','TEST',value,reasons,'now')
assert '90/100' in card and 'https://t.me/test/1' in card and 'TEST' in card
assert '\n' in card and '\\n' not in card
print('ALL_TESTS_OK')
