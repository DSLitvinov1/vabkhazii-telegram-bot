from pathlib import Path

workflow=Path('../.github/workflows/leads.yml').read_text(encoding='utf-8')
assert 'actions/checkout@v7' in workflow
assert 'actions/cache@v6' in workflow
assert 'actions/setup-python@v7' in workflow
assert "FORCE_RUN: ${{ inputs.force_logolead || '0' }}" in workflow
assert 'ENABLE_WEB: "1"' in workflow
assert 'ENABLE_MARKETS: "1"' in workflow
assert 'DELIVERY_ENABLED: "0"' in workflow
assert 'MAX_LEADS_PER_RUN: "12"' in workflow
assert 'PENDING_LIMIT: "500"' in workflow
assert 'LOGOLEAD_CHAT_ID: ${{ secrets.LOGOLEAD_CHAT_ID }}' in workflow
assert '@logopedutkina' not in workflow
assert workflow.index('- name: Run LogoLead') < workflow.index('- name: Run VAbkhazii Leads Bot')
assert 'python test_notify.py' in workflow
assert 'python test_target.py' in workflow
target_workflow=Path('../.github/workflows/check-logolead-target.yml').read_text(encoding='utf-8')
assert 'workflow_dispatch:' in target_workflow
assert 'schedule:' not in target_workflow
assert 'TARGET_USERNAME: ${{ inputs.username }}' in target_workflow
assert 'python target_ready.py' in target_workflow
print('WORKFLOW_TEST_OK')
