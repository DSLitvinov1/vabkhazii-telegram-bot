# LogoLead

Standalone private repository for LogoLead — a lead finder for a speech therapist.

LogoLead searches public Telegram messages, public parent groups, selected public web sources and public marketplace projects for people actively looking for a speech therapist/defectologist or describing a speech problem that may require one.

The system filters specialist advertising, vacancies, bots, expert/media requests and duplicate cross-posts, scores buyer intent from 0 to 100, keeps only fresh leads, and prepares a compact Telegram card with a personalized reply draft plus source/contact buttons.

## Production safeguards

- public/searchable sources only;
- no private-group auto-join;
- no credential or anti-bot bypass;
- no automatic unsolicited messaging to leads;
- delivered-history and pending queues are separate;
- stale backlog is not delivered;
- high-intent global-search phrases run every scan while the larger query set rotates to reduce Telegram FloodWait risk;
- public-group discovery queries rotate too, expanding city coverage without hammering Telegram search;
- equally strong leads are freshness-ranked so recent requests are processed before older ones;
- public marketplace collection includes Kwork plus a no-login Profi.ru adapter that only reads public order pages;
- canary mode currently limits delivery to one fresh lead per run;
- optional recipient feedback buttons (`👍 Подходит` / `👎 Не лид`) are implemented but disabled until a dedicated LogoLead bot token is used;
- Telegram user-session workflows are serialized to avoid simultaneous use from different runner IPs.

## Deployment state

This repository is now the canonical standalone LogoLead codebase. Automatic schedule remains intentionally disabled until the renewed Telegram session and required repository secrets are migrated and validated here. Pushes run tests only; manual workflow dispatch is available after credentials are configured.
