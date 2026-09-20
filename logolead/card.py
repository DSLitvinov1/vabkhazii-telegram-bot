from classifier import extract, norm
from reply import draft_reply, detect_issue, format_age, age_word


def heat(score):
    if score>=75: return '🔥 ГОРЯЧИЙ'
    if score>=50: return '🟠 ПОДХОДЯЩИЙ'
    return '🟡 ВОЗМОЖНЫЙ'


def build(text,url,source,score,reasons,published=None):
    meta=extract(text); details=[]
    issue=detect_issue(text)
    if meta['age'] is not None: details.append(f"Возраст: {format_age(meta['age'])} {age_word(meta['age'])}")
    if meta['city']: details.append(f"Город: {meta['city']}")
    if meta['mode']: details.append(f"Формат: {meta['mode']}")
    if issue!='речь и произношение': details.append(f"Запрос: {issue}")
    if published: details.append('Опубликовано: '+published)
    lines=[f'{heat(score)} ЛИД — {score}/100',f'Источник: {source}',*details]
    if reasons: lines.append('Почему: '+', '.join(reasons))
    lines+=['','💬 '+norm(text)[:750],'','✍️ Готовый ответ:',draft_reply(text)]
    if url: lines+=['','🔗 '+url]
    return '\n'.join(lines)
