'use strict';
const assert = require('assert'), fs = require('fs'), vm = require('vm');
const source = fs.readFileSync('static/settings.js', 'utf8');
const load = source.slice(source.indexOf('async function loadSettings('), source.indexOf('function openSettingsModal('));
const read = source.slice(source.indexOf('function readSettingsForm('), source.indexOf('async function saveSettings('));
(async () => {
  for (const light of [true, false]) {
    const inputs = new Map();
    const document = {getElementById: id => {
      if (light && ['setting-annotation-ocr-key', 'setting-annotation-ocr-secret'].includes(id)) return null;
      if (!inputs.has(id)) inputs.set(id, {value: ''});
      return inputs.get(id);
    }};
    const ctx = vm.createContext({document, state: {settings: {}},
      API: {get: async () => ({annotation_ocr_baidu_api_key:'fixture-key', annotation_ocr_baidu_secret_key:'fixture-secret'})},
      detectLlmProvider: () => 'fixture', updateTtsProviderHint: () => {}});
    vm.runInContext(load + read, ctx);
    await ctx.loadSettings();
    const payload = ctx.readSettingsForm();
    if (light) {
      assert(!Object.hasOwn(payload, 'annotation_ocr_baidu_api_key'));
      assert(!Object.hasOwn(payload, 'annotation_ocr_baidu_secret_key'));
    } else {
      assert.equal(payload.annotation_ocr_baidu_api_key, 'fixture-key');
      assert.equal(payload.annotation_ocr_baidu_secret_key, 'fixture-secret');
    }
  }
  console.log('settings distribution checks passed: missing OCR inputs do not erase saved values');
})().catch(error => {console.error(error); process.exitCode = 1;});
