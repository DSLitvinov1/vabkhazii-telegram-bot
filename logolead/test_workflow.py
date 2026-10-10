from pathlib import Path

logo=Path('../.github/workflows/logolead.yml').read_text(encoding='utf-8')
legacy=Path('../.github/workflows/leads.yml').read_text(encoding='utf-8')
target=Path('../.github/workflows/check-logolead-target.yml').read_text(encoding='utf-8')
renew=Path('../.github/workflows/renew-telegram-session.yml').read_text(encoding='utf-8')

assert 'name: LogoLead' in logo
assert 'push:' in logo and 'workflow_dispatch:' in logo
assert 'schedule:' not in logo
assert 'actions/checkout@v7' in logo
assert 'actions/cache@v6' in logo
assert 'actions/setup-python@v7' in logo
assert 'cache: "pip"' in logo
assert 'cache-dependency-path: "logolead/requirements.txt"' in logo
assert 'pip install -r logolead/requirements.txt' in logo
assert "if: github.event_name != 'push'" in logo
assert "FORCE_RUN: ${{ inputs.force_logolead || '0' }}" in logo
assert 'ENABLE_WEB: "1"' in logo
assert 'ENABLE_MARKETS: "1"' in logo
assert "DELIVERY_ENABLED: ${{ github.event_name == 'schedule' && '1' || (inputs.deliver || '0') }}" in logo
assert 'deliver:' in logo
assert 'min_score:' in logo
assert "MIN_SCORE: ${{ inputs.min_score || '50' }}" in logo
assert 'ENABLE_KWORK: "1"' in logo
assert 'ENABLE_PROFI: "1"' in logo
assert 'MAX_LEADS_PER_RUN: "1"' in logo
assert 'DELIVERY_MAX_AGE_HOURS: "24"' in logo
assert 'PENDING_LIMIT: "500"' in logo
assert 'LOGOLEAD_CHAT_ID: ${{ secrets.LOGOLEAD_CHAT_ID }}' in logo
assert '@logopedutkina' not in logo
assert 'python test_quality.py' in logo
assert 'python test_notify.py' in logo
assert 'python test_feedback.py' in logo
assert 'python test_pipeline.py' in logo
assert 'GLOBAL_ROTATING_QUERIES_PER_RUN: "12"' in logo
assert 'DISCOVERY_ROTATING_QUERIES_PER_REFRESH: "18"' in logo
assert 'python test_target.py' in logo
assert 'group: telegram-user-session' in logo
assert 'statuses: write' in logo
assert "'context':'logolead/tests'" in logo
assert 'if: always()' in logo

assert 'group: telegram-user-session' in legacy
assert 'name: VAbkhazii Leads Bot' in legacy
assert 'Run LogoLead' not in legacy
assert 'LOGOLEAD_CHAT_ID' not in legacy
assert 'Run VAbkhazii Leads Bot' in legacy
assert 'schedule:' not in legacy

assert 'workflow_dispatch:' in target
assert 'schedule:' not in target
assert 'TARGET_USERNAME: ${{ inputs.username }}' in target
assert 'python target_ready.py' in target
assert 'group: telegram-user-session' in target

assert 'workflow_dispatch:' in renew
assert 'schedule:' not in renew
assert 'TG_2FA_PASSWORD: ${{ secrets.TG_2FA_PASSWORD }}' in renew
assert 'python logolead/renew_session.py' in renew
assert 'group: telegram-user-session' in renew

print('WORKFLOW_TEST_OK')
