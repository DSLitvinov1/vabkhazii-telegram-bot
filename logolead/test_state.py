import json, tempfile
from pathlib import Path
import lead_bot

with tempfile.TemporaryDirectory() as tmp:
    state_dir=Path(tmp)/'.lead_state'
    state_file=state_dir/'state.json'
    state_dir.mkdir()
    state_file.write_text(json.dumps({
        'version':2,
        'seen':['a','b'],
        'last_run':'2026-09-20T10:00:00+00:00'
    }),encoding='utf-8')
    old_dir,old_file=lead_bot.STATE_DIR,lead_bot.STATE_FILE
    lead_bot.STATE_DIR,lead_bot.STATE_FILE=state_dir,state_file
    try:
        state=lead_bot.load_state()
        assert state['seen']==['a','b']
        assert state['groups']=={}
        assert state['group_last_ids']=={}
        assert state['version']==lead_bot.STATE_VERSION
        lead_bot.save_state(state)
        saved=json.loads(state_file.read_text(encoding='utf-8'))
        assert saved['version']==lead_bot.STATE_VERSION
    finally:
        lead_bot.STATE_DIR,lead_bot.STATE_FILE=old_dir,old_file

assert lead_bot.message_key(123,456)==lead_bot.message_key(123,456)
assert lead_bot.message_key(123,456)!=lead_bot.message_key(123,457)
print('STATE_TEST_OK')
