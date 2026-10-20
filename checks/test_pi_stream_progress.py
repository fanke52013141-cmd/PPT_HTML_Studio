"""Pure SDK-event projection: no provider or credentials."""
from pathlib import Path
import subprocess


def test_stream_event_projection_is_private_and_throttled():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['node', '--input-type=module', '-e', """
import assert from 'node:assert/strict';
import { streamProgress } from './agent_runner/progress.mjs';
let now = 0; const events = [];
const progress = streamProgress(e => events.push(e), () => now);
progress({type:'message_start',message:{role:'assistant'}});
now = 100; progress({type:'message_update',assistantMessageEvent:{type:'thinking_delta',delta:'PRIVATE'}});
now = 200; progress({type:'message_update',assistantMessageEvent:{type:'toolcall_delta',delta:'SECRET'}});
assert.equal(events.length,2);
assert.equal(events[1].reasoning_chars,7);
assert.equal(events[1].tool_argument_chars,6);
assert.equal(events[1].first_content_seconds,0.2);
now=300; progress({type:'message_update',assistantMessageEvent:{type:'toolcall_delta',delta:'x'}});
assert.equal(events.length,2);
progress({type:'message_end',message:{role:'assistant'}});
assert.equal(events.at(-1).tool_argument_chars,7);
assert(!JSON.stringify(events).includes('PRIVATE'));
assert(!JSON.stringify(events).includes('SECRET'));
"""], cwd=root, check=True, capture_output=True, text=True)
