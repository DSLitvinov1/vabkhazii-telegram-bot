def normalize_content(text):
    return ' '.join((text or '').lower().split()).strip()


def content_signature(text,url=''):
    normalized=normalize_content(text)
    if len(normalized)>=40:
        return 'text:'+normalized[:1200]
    if url:
        return 'url:'+url.strip()
    return 'text:'+normalized[:1200]


def merge_unique(items):
    best={}
    for item in items:
        signature=content_signature(item[2],item[3])
        if not signature or signature=='text:':
            continue
        previous=best.get(signature)
        if previous is None or item[0]>previous[0]:
            best[signature]=item
    return list(best.values())
