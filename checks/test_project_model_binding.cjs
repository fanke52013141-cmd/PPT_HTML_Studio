'use strict';
const fs = require('fs'), assert = require('assert');
const {chromium} = require('../html_engine/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.HPS_CHROME ? {executablePath: process.env.HPS_CHROME} : {})});
  try {
    const page = await browser.newPage(); const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.setContent('<main id="settings"></main>');
    await page.addStyleTag({content: fs.readFileSync('static/style.css', 'utf8')});
    await page.addStyleTag({content: fs.readFileSync('static/stitch.css', 'utf8')});
    await page.addStyleTag({content: fs.readFileSync('static/project_model_binding.css', 'utf8')});
    await page.evaluate(() => {
      window.saved = null; window.conflict = false;
      window.API = {
        get: async url => url.includes('model-connections') ? {connections: [
          {id: 'text-one', name: '<script>unsafe</script>', kind: 'text', state: 'active', revision: {model: 'text-v1'}},
          {id: 'image-one', name: '图片', kind: 'image', state: 'active', revision: {model: 'image-v1'}}
        ]} : {revision: saved ? 1 : 0, bindings: saved || {text: {mode: 'legacy'}, image: {mode: 'legacy'}},
          effective: {text: {model: 'text-v1', provider: 'test', source: 'global', ready: true}, image: {model: 'image-v1', provider: 'test', source: 'global', ready: true}}},
        put: async (url, value) => { if (conflict) {const err = new Error('conflict'); err.status = 409; throw err;} saved = {text: value.text, image: value.image}; return {revision: 1, changed: true}; }
      };
      window.project = {id: 'project-a', visual_backend: 'html'};
    });
    await page.addScriptTag({content: fs.readFileSync('static/project_model_binding.js', 'utf8')});
    await page.evaluate(() => ProjectModelBinding.mount(document.querySelector('main'), project));
    await page.getByLabel('文字模型来源').selectOption('text-one');
    await page.getByLabel('图片模型来源').selectOption('image-one');
    await page.getByRole('button', {name: '保存模型配置'}).click();
    await page.getByRole('status').filter({hasText: '已保存'}).waitFor();
    assert.equal(await page.evaluate(() => saved.text.connection_id), 'text-one');
    await page.getByRole('button', {name: '重新读取配置'}).click();
    await page.waitForFunction(() => document.querySelector('select')?.value === 'text-one');
    await page.evaluate(() => { conflict = true; });
    await page.getByLabel('文字模型来源').selectOption('inherit');
    await page.getByRole('button', {name: '保存模型配置'}).click();
    await page.getByRole('status').filter({hasText: '本地选择已保留'}).waitFor();
    assert.equal(await page.getByLabel('文字模型来源').inputValue(), 'inherit');
    assert.equal(await page.locator('main script').count(), 0);
    if (process.env.HPS_MODEL_BINDING_SCREENSHOT) await page.screenshot({path: process.env.HPS_MODEL_BINDING_SCREENSHOT, fullPage: true});
    await page.evaluate(() => ProjectModelBinding.mount(document.querySelector('main'), {visual_backend: 'image'}));
    assert.equal(await page.locator('main section').count(), 0);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({passed: true, browser: 'Chromium', checks: ['select/save/reopen', 'conflict preserves draft', 'escaped labels', 'image backend hidden'], transport: 'stub; no live service'}));
  } finally { await browser.close(); }
})().catch(err => {console.error(err); process.exitCode = 1;});
