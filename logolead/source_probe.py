"""Read-only public-source smoke checks, no Telegram or private credentials."""
import json
from datetime import datetime, timezone
from classifier import score_market_order
from market_sources import (
    PROFI_PAGES, collect_kwork, fetch_text as market_fetch, parse_profi_page)
from web_sources import collect_cloud_web


def main():
    result = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'public pages only', 'lookback_hours': 72}
    try:
        rows = collect_kwork(72)
        qualified = [x for x in rows
                     if score_market_order(x['text'], x['source'])[0] >= 60]
        result['kwork'] = {'reachable_or_empty': True,
                           'fresh_public_orders': len(rows),
                           'qualified': len(qualified)}
    except Exception as exc:
        result['kwork'] = {'error': type(exc).__name__}
    try:
        city, url = PROFI_PAGES[0]
        page = market_fetch(url)
        rows = parse_profi_page(page, url, city, 72)
        qualified = [x for x in rows
                     if score_market_order(x['text'], x['source'])[0] >= 60]
        result['profi'] = {
            'public_page_readable': bool(page),
            'public_client_section_present': 'Актуальные заказы от клиентов' in page,
            'fresh_visible_cards': len(rows),
            'qualified_visible_cards': len(qualified),
            'app_login_required_for_personalized_orders': True}
    except Exception as exc:
        result['profi'] = {'error': type(exc).__name__}
    try:
        posts = collect_cloud_web(72)
        result['parent_forum'] = {'fresh_public_posts': len(posts)}
    except Exception as exc:
        result['parent_forum'] = {'error': type(exc).__name__}
    print('LOGOLEAD_SOURCE_PROBE', json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
