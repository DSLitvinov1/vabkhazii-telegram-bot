def merge_unique(items):
    best={}
    for item in items:
        text=' '.join((item[2] or '').lower().split())[:600]
        url=item[3] or ''
        signature=url if url else text
        if not signature:
            continue
        previous=best.get(signature)
        if previous is None or item[0]>previous[0]:
            best[signature]=item
    return list(best.values())
