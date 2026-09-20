from classifier import extract,norm
from reply import draft_reply
def heat(score):
 return '🔥 ГОРЯЧИЙ' if score>=75 else ('🟠 ПОДХОДЯЩИЙ' if score>=50 else '🟡 ВОЗМОЖНЫЙ')
def build(text,url,source,score,reasons,published=None):
 m=extract(text); details=[]
 if m['age']:details.append(f"Возраст: {m['age']} лет")
 if m['city']:details.append(f"Город: {m['city']}")
 if m['mode']:details.append(f"Формат: {m['mode']}")
 if published:details.append('Опубликовано: '+published)
 lines=[f'{heat(score)} ЛИД — {score}/100',f'Источник: {source}',*details,'Причины: '+', '.join(reasons),'','💬 '+norm(text)[:750],'','✍️ Готовый ответ:',draft_reply(text),'','🔗 '+url]
 return '\\n'.join(lines)
