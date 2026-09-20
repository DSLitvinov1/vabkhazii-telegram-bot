# LogoLead

Lead finder for a speech therapist, deployed inside the existing VAbkhazii GitHub Actions repository.

## Production pipeline
1. Search public Telegram messages for explicit and implicit demand for a speech therapist/defectologist.
2. Use public chats from matching global-search messages as high-priority source seeds.
3. Discover and cache public parent, child-development and city parent groups.
4. Rotate through the cached group pool and scan only messages newer than the last processed message.
5. Every few hours run a deeper keyword search inside a rotating subset of cached groups, so relevant requests are not lost inside very active chats.
6. Reject specialist advertising, vacancies and irrelevant educational content.
7. Score buyer intent from 0 to 100, including direct requests and question-based speech problems.
8. Extract child age, city and online/offline format when stated.
9. Keep separate scan deduplication and persistent delivered-lead history.
10. Generate a short personalized reply draft and send ranked lead cards to Telegram.

## Runtime
LogoLead runs from `.github/workflows/leads.yml` before the legacy VAbkhazii lead bot, so the slower travel-source scan does not delay LogoLead. Both still run sequentially in one concurrency-protected workflow and reuse repository Secrets without exposing them.

Production defaults:
- effective LogoLead scan cadence: about every 10 minutes;
- lead freshness window: 72 hours;
- delivery threshold: 50/100;
- max cards per run: 12;
- public-group discovery refresh: about every 6 hours;
- group cache: up to 120 public groups;
- up to 30 groups scanned per normal run, with priority for chats found by live message search;
- first chronological group scan: up to 180 recent messages, then incremental scans;
- deep group search: every 3 hours, 6 groups per cycle, targeted speech-therapy keywords;
- daily Telegram health/status message;
- delivered-lead history survives classifier rescans, preventing duplicate delivery.

## Diagnostics
Production logs report aggregate counts only: checked messages, score histogram, signal combinations, query hit counts and rejection reasons. They do not print user message bodies.

## Public marketplaces and web sources
The production bot also checks Kwork's public project exchange by speech-therapy keywords every 30 minutes. It reads only publicly rendered project data, keeps real publication timestamps, and does not log in or automate responses.

The repository also contains Babyblog and U-mama adapters with real publication timestamps. Those sites reject GitHub-hosted runner traffic, so cloud web scanning is disabled rather than attempting to bypass their protections. The adapters remain available for permitted/local execution.

Set `MIN_SCORE=75` for hot-leads-only mode.

Only public/searchable sources are scanned. No private-group auto-join, credential bypass, anti-bot bypass, or automated unsolicited messaging.
