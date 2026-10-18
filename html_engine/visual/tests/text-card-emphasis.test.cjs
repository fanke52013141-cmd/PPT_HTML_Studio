"use strict";
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');
const {compile} = require('../compiler.cjs');
const root = path.resolve(__dirname, '..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
async function main() {
  const scene = read('fixtures/presentation-details/source-scene.json');
  scene.version = '0.7.0';
  const node = scene.nodes.find(n => n.type === 'text');
  node.runs = [{text:'过程',emphasis:false},{text:'温度保持0℃',emphasis:true}];
  node.presentation = {variant:'text-card-outline-emphasis',height:136,
    typography:{text:{fontSizePx:20,lineHeight:1.3,align:'center'}}};
  compile(scene, read('generated/catalog.json'));
  const bad = structuredClone(scene);
  bad.nodes.find(n => n.type === 'header').presentation = {variant:'text-card-outline-emphasis'};
  assert.throws(() => compile(bad, read('generated/catalog.json')), /UNSUPPORTED_PRESENTATION_VARIANT/);
  const browser = await chromium.launch(require('../../tools/browser-runtime.cjs').captureLaunchOptions(chromium));
  try {
    const page = await browser.newPage({viewport:{width:1648,height:1200}});
    await page.goto(pathToFileURL(path.join(root,'preview/index.html')).href);
    await page.waitForFunction(() => window.visualPlayer?.ready);
    const inspect = async variant => {
      const input = structuredClone(scene);
      input.nodes.find(n => n.id === node.id).presentation.variant = variant;
      assert.equal(await page.evaluate(s => window.visualPlayer.apply(s), input), true,
        await page.locator('#status').innerText());
      await page.evaluate(t => window.visualPlayer.seek(t), input.durationMs);
      return page.evaluate(id => {
        const panel = document.querySelector(`[data-object-id="${id}"]`);
        const copy = panel.querySelector('.v-panel-copy');
        const spans = [...copy.querySelectorAll('span')];
        return {text:copy.textContent,align:getComputedStyle(copy).textAlign,
          border:getComputedStyle(panel).borderTopWidth,
          weights:spans.map(s => getComputedStyle(s).fontWeight),
          gap:getComputedStyle(spans[1]).marginInlineStart};
      }, node.id);
    };
    const emphasized = await inspect('text-card-outline-emphasis');
    assert.equal(emphasized.text,'过程温度保持0℃');
    assert.deepEqual(emphasized.weights,['400','700']);
    assert.equal(emphasized.align,'center');
    assert.equal(emphasized.border,'1px');
    assert.equal(emphasized.gap,'5px');
    const legacy = await inspect('text-card-outline');
    assert.equal(legacy.text,emphasized.text);
    assert.deepEqual(legacy.weights,['400','400']);
    assert.equal(legacy.gap,'0px');
    console.log('text-card emphasis: type guard, unchanged text, panel, alignment, weights, spacing and legacy checks passed');
  } finally { await browser.close(); }
}
main().catch(error => {console.error(error);process.exitCode=1;});
