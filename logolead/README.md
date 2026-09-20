# LogoLead

Lead finder for a speech therapist, deployed inside the existing VAbkhazii GitHub Actions repository.

## Production pipeline
1. Search public Telegram messages for explicit and implicit demand for a speech therapist/defectologist.
2. Use public chats from matching global-search messages as high-priority source seeds.
3. Discover and cache public parent, child-development and city parent groups.
4. Rotate through the cached group pool and scan only messages newer than the last processed message.
5. Backfill very active groups in small chunks so a useful request is not lost below the newest messages.
6. Every few hours run deeper keyword search inside a rotating subset of cached groups.
7. Reject specialist advertising, vacancies and irrelevant educational content.
8. Score buyer intent from 0 to 100 and extract age, city, format and speech problem when stated.
9. Keep separate scan deduplication, delivered-lead history and a persistent pending queue.
10. Generate a personalized reply draft and deliver ranked cards only when delivery is enabled.

## Runtime
LogoLead runs from `.github/workflows/leads.yml` before the legacy VAbkhazii lead bot. Both run sequentially in one concurrency-protected workflow and reuse the authorized Telegram user session.

Production defaults:
- effective LogoLead scan cadence: about every 10 minutes;
- lead freshness window: 72 hours;
- delivery threshold: 50/100;
- max cards per delivery run: 12;
- pending queue capacity: 500 candidates;
- public-group discovery refresh: about every 6 hours;
- group cache: up to 120 public groups;
- up to 30 groups scanned per normal run;
- first chronological group scan: up to 180 recent messages, followed by incremental/backfill scans;
- deep group search: every 3 hours across a rotating subset;
- delivered-lead history survives classifier rescans.

## Delivery pause
Production delivery is currently controlled by `DELIVERY_ENABLED`. When it is `0`, LogoLead keeps searching and qualifying leads but does not send Telegram messages. Eligible leads are stored in the persistent pending queue, so pausing delivery does not intentionally discard them.

The LogoLead destination is separate from the legacy bot destination and comes from the `LOGOLEAD_CHAT_ID` GitHub Secret. This avoids accidentally sending speech-therapy leads to the old travel-leads chat.

## Diagnostics
Production logs report aggregate counts only: checked messages, score histogram, signal combinations, query hit counts and rejection reasons. They do not print user message bodies.

## Public marketplaces and web sources
The production bot checks Kwork's public project exchange by speech-therapy keywords, validates project text for speech-therapy terms, keeps publication timestamps, and does not log in or automate responses.

Production web scanning can check recent public Woman.ru forum threads, prefilter titles for child/speech intent, and validate publication timestamps before scoring.

Babyblog and U-mama adapters are also present. Those sites reject GitHub-hosted runner traffic, so the cloud bot does not attempt to bypass their protections.

Set `MIN_SCORE=75` for hot-leads-only mode.

Only public/searchable sources are scanned. No private-group auto-join, credential bypass, anti-bot bypass, or automated unsolicited messaging.
