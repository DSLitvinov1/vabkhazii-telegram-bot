from classifier import extract, norm
from reply import draft_reply


def heat(score):
    if score >= 75:
        return '🔥 ГОРЯЧИЙ'
    if score >= 50:
        return '🟠 ПОДХОДЯЩИЙ'
    return '🟡 ВОЗМОЖНЫЙ'


def build(text, url, source, score, reasons, published=None):
    meta = extract(text)
    details = []
    if meta['age'] is not None:
        details.append(f"Возраст: {meta['age']} лет")
    if meta['city']:
        details.append(f"Город: {meta['city']}")
    if meta['mode']:
        details.append(f"Формат: {meta['mode']}")
    if published:
        details.append('Опубликовано: ' + published)
    lines = [f'{heat(score)} ЛИД — {score}/100', f'Источник: {source}', *details]
    if reasons:
        lines.append('Причины: ' + ', '.join(reasons))
    lines += ['', '💬 ' + norm(text)[:750], '', '✍️ Готовый ответ:', draft_reply(text)]
    if url:
        lines += ['', '🔗 ' + url]
    return '\n'.join(lines)
