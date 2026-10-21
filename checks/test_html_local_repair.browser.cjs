'use strict';
// Scripted proposal; real editor, renderer, checks, save key and version restore. No network/provider.
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const {spawn} = require('node:child_process');
const {createInterface} = require('node:readline');
const {chromium} = require('../html_engine/node_modules/playwright');
const {captureLaunchOptions} = require('../html_engine/tools/browser-runtime.cjs');
const root = path.resolve(__dirname, '..');
const run = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'hps-editor-browser-local-repair-'));
(async () => {
  const server = spawn(require('./browser_python.cjs').pythonExecutable(root), [path.join(__dirname,'fixtures/html_handoff_bridge.py'),run,'--local-repair'],
    {cwd:root,stdio:['pipe','pipe','pipe']});
  let browser, stderr = '', held = null, holdNext = false; const pending = [], errors = [], writes = [];
  server.stderr.on('data', c => {stderr += c;});
  createInterface({input:server.stdout}).on('line', line => pending.shift()?.resolve(JSON.parse(line)));
  server.on('exit',code => {while(pending.length) pending.shift().reject(Error(`bridge exit ${code}: ${stderr}`));});
  const request = (method,url,payload) => new Promise((resolve,reject) => {
    pending.push({resolve,reject}); server.stdin.write(JSON.stringify({method,url,payload})+'\n');
  });
  try {
    const base = 'https://local-repair-fixture.test', endpoint = `${base}/api/projects/isolated/html-visual/condensation/editor`;
    const read = async () => JSON.parse(Buffer.from((await request('GET',endpoint)).body,'base64'));
    browser = await chromium.launch(captureLaunchOptions(chromium));
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/*', async route => {
      const req = route.request(), payload = req.postData() ? req.postDataJSON() : null;
      if (req.url().endsWith('/repair/save') || req.method() === 'PUT') writes.push(req.url());
      const response = await request(req.method(),req.url(),payload);
      if (holdNext && req.url().endsWith('/repair/generate')) {
        holdNext = false; await new Promise(resolve => {held = resolve;});
      }
      await route.fulfill({...response,body:Buffer.from(response.body,'base64')});
    });
    await page.goto(base);
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    await page.locator('[data-object="headline"]').click();
    const initial = await read();
    let panel = page.locator('[data-local-repair]'); await panel.locator('summary').click();
    const generate = () => panel.getByRole('button',{name:'生成避让候选',exact:true});
    await generate().click();
    await panel.getByRole('status').filter({hasText:'候选检查通过，尚未保存'}).waitFor({timeout:180000});
    assert.equal((await read()).revision,initial.revision);
    assert.deepEqual(writes,[]);
    assert.ok(await panel.locator('img').count() >= 2);
    assert.ok((await panel.textContent()).includes('水平偏移：自动（槽位） → 8px'));
    assert.ok((await panel.textContent()).includes('几何试算（未调用模型）'));
    await page.screenshot({path:path.join(run,'local-repair-candidate.png'),fullPage:true});
    await panel.getByRole('button',{name:'放弃避让候选',exact:true}).click();
    assert.ok(await panel.getByRole('button',{name:'保存避让候选',exact:true}).isDisabled());
    assert.equal((await read()).revision,initial.revision);
    await generate().click();
    await panel.getByRole('status').filter({hasText:'候选检查通过，尚未保存'}).waitFor({timeout:180000});
    await panel.getByRole('button',{name:'保存避让候选',exact:true}).click();
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    const saved = await read();
    assert.equal(saved.revision,initial.revision+1);
    assert.equal(saved.scene.nodes.find(n=>n.id==='headline').presentation.offsetX,8);
    assert.equal(writes.length,1);
    await page.getByRole('button',{name:'读取保存版本',exact:true}).click();
    const versions = page.getByLabel('保存版本');
    await versions.selectOption(String(initial.revision));
    await page.getByRole('button',{name:'预览恢复所选版本',exact:true}).click();
    await page.getByText('历史版本已进入当前草稿；核对后点击保存修改，产生新修订。',{exact:true}).waitFor();
    assert.equal((await read()).revision,saved.revision);
    panel = page.locator('[data-local-repair]'); await panel.locator('summary').click();
    await generate().click();
    await panel.getByRole('status').filter({hasText:'请先保存草稿'}).waitFor();
    assert.equal(writes.length,1);
    // Switch pages while a response is delayed: the old panel cannot repopulate or save.
    await page.evaluate(() => HtmlSceneEditor.open(document.getElementById('host'),'isolated','condensation'));
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    // The reopened editor keeps its unsaved recovery draft; save it explicitly for this lifecycle case.
    await page.getByRole('button',{name:'保存修改',exact:true}).click();
    await page.getByText(/^(已保存；本页需要重新审阅，音频保留。|已展示本次重建影响；查看后再次点击保存修改。)$/).waitFor();
    if (await page.getByText('已展示本次重建影响；查看后再次点击保存修改。',{exact:true}).isVisible())
      await page.getByRole('button',{name:'保存修改',exact:true}).click();
    await page.getByText('已保存；本页需要重新审阅，音频保留。',{exact:true}).waitFor();
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    await page.locator('[data-object="headline"]').click();
    panel = page.locator('[data-local-repair]'); await panel.locator('summary').click();
    holdNext = true; await generate().click();
    await page.waitForFunction(() => document.querySelector('[data-local-repair] [role=status]')?.textContent.includes('正在试算'));
    // Wait for the actual checker result to reach the held transport boundary.
    const deadline = Date.now()+180000;
    while (!held && Date.now()<deadline) await new Promise(resolve => setTimeout(resolve, 50));
    assert.ok(held, 'Delayed candidate response did not arrive');
    await page.evaluate(() => HtmlSceneEditor.open(document.getElementById('host'),'isolated','condensation'));
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    held(); held = null;
    await page.waitForLoadState('networkidle');
    await page.locator('[data-local-repair] summary').click();
    assert.equal(await page.locator('[data-local-repair] img').count(),0);
    assert.ok(await page.locator('[data-local-repair]').getByRole('button',{name:'保存避让候选',exact:true}).isDisabled());
    assert.deepEqual(errors,[]);
    const report = {passed:true,run,checks:['real renderer and full checks','scripted proposal only',
      'before/after images and changes','no automatic save','discard','explicit original save',
      'version restore enters draft without author write','dirty draft rejected','late page response discarded','no page errors']};
    fs.writeFileSync(path.join(run,'local-repair-browser-report.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally { if(held) held(); await browser?.close(); server.stdin.end(); server.kill(); }
})().catch(error => { console.error(error); process.exitCode=1; });
