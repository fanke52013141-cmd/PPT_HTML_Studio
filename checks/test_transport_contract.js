const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function main() {
  const requests = [];
  const timeouts = [];
  const cleared = [];
  const sandbox = {
    AbortController, Headers, FormData, Blob, ArrayBuffer,
    setTimeout: (_fn, delay) => { timeouts.push(delay); return timeouts.length; },
    clearTimeout: id => cleared.push(id),
    showToast() {},
    fetch: async (url, options) => {
      requests.push({ url, options });
      return { ok: true, headers: new Headers({ 'content-type': 'application/json' }), text: async () => '{"success":true}' };
    },
  };
  sandbox.window = sandbox;
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/api_client.js'), 'utf8'), sandbox);
  const result = await sandbox.API.post('/export-audio', { gap_sec: 0.6 }, { timeoutMs: 900000 });
  assert.equal(result.success, true);
  assert.equal(timeouts[0], 900000);
  assert.equal(requests[0].options.headers.get('X-PPT-Studio-Request'), '1');
  const form = new FormData();
  form.append('file', new Blob(['pixels']), 'background.png');
  await sandbox.API.post('/background/image', form);
  assert.equal(requests[1].options.body, form);
  assert.equal(requests[1].options.headers.has('Content-Type'), false);
  assert.equal(requests[1].options.headers.get('X-PPT-Studio-Request'), '1');
  assert.equal(timeouts[1], 120000);
  assert.equal(cleared.length, 2);
  console.log('shared transport contract checks passed');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
