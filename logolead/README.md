# LogoLead

MVP lead finder for speech therapists.

## Pipeline
1. Discover public Telegram parent/speech-development groups.
2. Scan recent public messages (default 72h).
3. Score buyer intent and reject specialist ads/jobs.
4. Extract child age, city and online/offline format when stated.
5. Deduplicate leads.
6. Generate a short personalized reply draft.
7. Send ranked lead cards to Telegram.

Only public/searchable sources are scanned. No private-group auto-join or protection bypass.

Set environment variables from .env.example and run: python lead_bot.py
GitHub Actions workflow: logolead.yml
MIN_SCORE=75 enables hot-leads-only mode.
