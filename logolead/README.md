# LogoLead

LogoLead is a public-source lead finder for a speech therapist.

## Production pipeline
1. Search public Telegram messages for explicit and implicit demand for a speech therapist, defectologist or related help.
2. Use matching public chats as high-priority source seeds.
3. Discover and cache public parent, child-development and city parent groups.
4. Rotate through the group pool and scan only messages newer than the last processed message.
5. Backfill very active groups in small chunks so older fresh requests are not missed.
6. Run periodic keyword search inside rotating groups.
7. Reject specialist advertising, jobs, bots, expert-content posts and other non-client requests.
8. Score buyer intent from 0 to 100 and extract child age, city, online/offline format and likely speech problem.
9. Deduplicate cross-posts, preserve delivered history and maintain a persistent pending queue.
10. Generate a short personalized reply draft and send a compact Telegram card with source/contact buttons.

## Runtime
LogoLead has its own GitHub Actions workflow: `.github/workflows/logolead.yml`. The legacy VAbkhazii lead bot stays in a separate workflow, so neither blocks the other.

- production schedule is temporarily paused while the Telegram user session is renewed;
- push: run the test suite only, never deliver leads;
- manual dispatch: run tests and allow a forced scan after the Telegram session is valid again;
- once the session is renewed, the intended schedule is a GitHub trigger every 5 minutes with an effective LogoLead scan interval of about 10 minutes;
- lead search window: 72 hours;
- delivery window: only leads newer than 24 hours;
- production threshold: 50/100;
- canary delivery: at most 1 card per run while accuracy is being validated;
- pending queue: up to 500 candidates;
- group cache: up to 120 public groups;
- group discovery refresh: about every 6 hours;
- deep Telegram search: about every 3 hours.

Scheduled runs skip the full regression suite to reduce latency and GitHub Actions usage. Every code push runs the complete tests before production code is manually/scheduled.

## Delivery target
The destination is stored in the repository secret `LOGOLEAD_CHAT_ID`; it is independent from the old travel-leads chat. `LOGOLEAD_BOT_TOKEN` is supported for a dedicated future LogoLead bot. Until that secret exists, the authorized legacy delivery bot token is used.

A separate manual workflow, `check-logolead-target.yml`, verifies that a Telegram user is reachable by the delivery bot without publishing numeric IDs in source code.

## Lead cards
Cards include:
- lead score and heat level;
- source and public Telegram author username when available;
- child age, location and requested format when detected;
- likely speech issue;
- reason for the score;
- publication freshness;
- original excerpt;
- a ready-to-send response draft;
- button to open the source;
- button to open the public author profile when a username is available.

## Quality controls
The repository has unit/integration tests plus a curated positive/negative lead quality gate. Provider accounts, bot-authored posts, vacancies, courses/webinars, promotional posts and media/expert requests are filtered before delivery.

## Public marketplaces and web sources
Kwork public projects are checked without login. Public Woman.ru threads can also be evaluated. Babyblog and U-mama adapters remain local-only because GitHub-hosted runners are rejected by those sites; LogoLead does not bypass their protections.

Only public/searchable sources are scanned. No private-group auto-join, credential bypass, anti-bot bypass or automated unsolicited messaging.
