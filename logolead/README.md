# LogoLead

Lead finder for a speech therapist, deployed inside the existing VAbkhazii GitHub Actions repository.

## Production pipeline
1. Search public Telegram messages for explicit and implicit demand for a speech therapist/defectologist.
2. Discover public parent and child-development Telegram groups.
3. Cache discovered public groups and scan only messages newer than the last processed message.
4. Reject specialist advertising, vacancies and irrelevant educational content.
5. Score buyer intent from 0 to 100.
6. Extract child age, city and online/offline format when stated.
7. Deduplicate messages and public URLs while preserving retry on delivery errors.
8. Generate a short personalized reply draft.
9. Send ranked lead cards to the configured Telegram chat.

## Runtime
LogoLead runs from `.github/workflows/leads.yml` after the existing VAbkhazii lead bot and reuses the repository Secrets without exposing them.

Production defaults:
- effective LogoLead scan cadence: about every 10 minutes;
- lead freshness window: 72 hours;
- delivery threshold: 50/100;
- max cards per run: 12;
- public-group discovery refresh: about every 6 hours;
- first group scan: up to 180 recent messages, then incremental scans.

The repository also contains public Babyblog and U-mama adapters with real publication timestamps. Those sites reject GitHub-hosted runner traffic, so cloud web scanning is currently disabled rather than trying to bypass their protections. The adapters remain available for permitted/local execution.

Set `MIN_SCORE=75` for hot-leads-only mode.

Only public/searchable sources are scanned. No private-group auto-join, credential bypass, anti-bot bypass, or automated unsolicited messaging.
