"""Normalize stored Telethon sessions using the same tolerant method as VAbkhazii."""
import re
from telethon.sessions import StringSession


def normalize_tg_session(raw_value):
    raw_value = (raw_value or '').strip().strip('"').strip("'")
    if not raw_value:
        return ''
    compact = re.sub(r'\s+', '', raw_value)
    tested = set()

    def try_candidate(candidate):
        if not candidate or candidate in tested:
            return None
        tested.add(candidate)
        try:
            StringSession(candidate)
            return candidate
        except Exception:
            return None

    exact = try_candidate(compact)
    if exact:
        return exact
    # Telethon v1 IPv4 / IPv6 session string lengths.
    for start, char in enumerate(compact):
        if char != '1':
            continue
        for length in (353, 369):
            end = start + length
            if end <= len(compact):
                recovered = try_candidate(compact[start:end])
                if recovered:
                    print('LOGOLEAD_SESSION_NORMALIZED=1')
                    return recovered
    for match in re.finditer(r'1[A-Za-z0-9_\-=]{200,500}', compact):
        chunk = match.group(0)
        for length in range(len(chunk), 199, -1):
            recovered = try_candidate(chunk[:length])
            if recovered:
                print('LOGOLEAD_SESSION_NORMALIZED=1')
                return recovered
    raise RuntimeError('TG_SESSION is malformed and cannot be normalized')
