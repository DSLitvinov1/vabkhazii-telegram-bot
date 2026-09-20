from classifier import extract


def detect_issue(text):
    t=' '.join((text or '').lower().split())
    if any(x in t for x in ['не говорит','запуск речи','не говорит предложениями','задержка речи']): return 'запуск речи'
    if 'зрр' in t or 'зпрр' in t: return 'ЗРР/ЗПРР'
    if 'дисграф' in t: return 'дисграфия'
    if 'дислекс' in t: return 'дислексия'
    if 'заика' in t: return 'заикание'
    if any(x in t for x in ['шепеляв','дизартр','ффнр','онр']): return 'звукопроизношение и речь'
    if any(x in t for x in ['картавит','звук р','звука р','звук «р»','звук "р"','не выговаривает р','не произносит р']): return 'звук Р'
    if any(x in t for x in ['звук л','звука л','звук «л»','звук "л"','не выговаривает л','не произносит л']): return 'звук Л'
    if any(x in t for x in ['не выговаривает','не произносит','постановка звуков']): return 'постановка звуков'
    return 'речь и произношение'


def format_age(age):
    if age is None: return None
    return str(age).replace('.0','').replace('.',',')


def age_word(age):
    if age is None: return ''
    if isinstance(age,float) and not age.is_integer(): return 'года'
    value=int(age)
    if value%100 in (11,12,13,14): return 'лет'
    if value%10==1: return 'год'
    if value%10 in (2,3,4): return 'года'
    return 'лет'


def draft_reply(text):
    issue=detect_issue(text)
    meta=extract(text)
    lead=f'Здравствуйте! Вижу ваш запрос по теме «{issue}».'
    if meta['age'] is None:
        question=' Подскажите, пожалуйста, возраст ребёнка и что именно сейчас вызывает наибольшие трудности?'
    else:
        question=f' Ребёнку {format_age(meta["age"])} {age_word(meta["age"])} — подскажите, пожалуйста, что именно сейчас вызывает наибольшие трудности и были ли уже занятия со специалистом?'
    finish=' После этого можно понять, какой формат занятий лучше подойдёт.'
    if meta['mode']=='онлайн':
        finish=' После уточнений можно сразу понять, как лучше выстроить занятия в онлайн-формате.'
    return lead+question+finish


def draft_market_reply(text):
    issue=detect_issue(text)
    meta=extract(text)
    parts=[f'Здравствуйте! Готов(а) помочь с вашим запросом по теме «{issue}».']
    if meta['age'] is None:
        parts.append('Подскажите, пожалуйста, возраст ребёнка и какие трудности сейчас наиболее заметны.')
    else:
        parts.append(f'Вижу, что ребёнку {format_age(meta["age"])} {age_word(meta["age"])}. Подскажите, пожалуйста, какие трудности сейчас наиболее заметны и были ли занятия со специалистом.')
    if meta['mode']=='онлайн':
        parts.append('Онлайн-формат возможен; после уточнений можно подобрать подходящий план занятий.')
    else:
        parts.append('После уточнений можно предложить подходящий формат и план занятий.')
    return ' '.join(parts)
