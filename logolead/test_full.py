import asyncio, tempfile
from datetime import datetime,timezone
import lead_bot
from classifier import score,extract
from card import build
async def run():
 samples=['Ищу логопеда ребенку 6 лет, картавит. Москва, онлайн','Требуется логопед в детский центр. Зарплата 90000','Я логопед, приглашаю на занятия','Подскажите логопеда, ребенок плохо говорит']
 scores=[score(x)[0] for x in samples]
 assert scores[0]>=85 and scores[1]==0 and scores[2]==0 and scores[3]>=80
 s,r=score(samples[0]); c=build(samples[0],'https://t.me/a/1','Telegram',s,r,'now')
 assert '6' in c and 'Москва' in c and 'https://t.me/a/1' in c
 await lead_bot.notify(c)
 print('FULL_OK',scores,extract(samples[0]))
asyncio.run(run())
