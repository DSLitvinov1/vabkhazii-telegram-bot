# LogoLead

Lead finder for speech therapists, deployed inside the existing VAbkhazii GitHub Actions repository.

## Current pipeline
1. Search public Telegram messages for explicit and implicit speech-therapy demand.
2. Discover public parent/speech-development Telegram groups and scan recent posts.
3. Scan public web sources with real publication timestamps (currently Babyblog and U-mama).
4. Reject specialist advertising, vacancies and irrelevant educational content.
5. Score lead intent from 0 to 100.
6. Extract child age, city and online/offline format when stated.
7. Deduplicate by Telegram message or public URL.
8. Generate a short personalized reply draft.
9. Send ranked lead cards to the configured Telegram chat.

## Deployment
LogoLead runs from the repository workflow `.github/workflows/leads.yml` after the existing VAbkhazii lead bot. It reuses repository Secrets without exposing them.

Default production settings:
- Telegram scan cadence: about every 10 minutes.
- Public web scan cadence: about every 60 minutes.
- Lead freshness: 72 hours.
- Delivery threshold: 50/100.
- Max cards per run: 12.

Set `MIN_SCORE=75` for hot-leads-only mode.

Only public/searchable sources are scanned. No private-group auto-join, credential bypass, anti-bot bypass or automated unsolicited messaging.
