'use strict';
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/output_render.js', 'utf8');
(async () => {
  let enabled = false, calls = 0;
  const box = {hidden: false, style: {}}, message = {innerText: ''};
  const scope = {
    window: {PPTFlow: {distributionFeatures: () => ({digital_human: enabled})},
      DigitalHumanPanel: {getOutputStatus: async () => {calls++; return {enabled: true, canRender: false, message: 'pending'};}}},
    document: {getElementById: id => id === 'step8-digital-human-status' ? box : id === 'step8-digital-human-message' ? message : null},
    isCurrentWorkspaceProject: () => true,
  };
  vm.createContext(scope);
  vm.runInContext(source, scope);
  const disabled = await scope.refreshStep8DigitalHumanStatus('p1', 1);
  assert.equal(disabled.enabled, false);
  assert.equal(disabled.canRender, true);
  assert.equal(box.hidden, true);
  assert.equal(calls, 0);
  enabled = true;
  const pending = await scope.refreshStep8DigitalHumanStatus('p1', 1);
  assert.equal(pending.canRender, false);
  assert.equal(box.hidden, false);
  assert.equal(calls, 1);
  scope.window.DigitalHumanPanel = null;
  const unknown = await scope.refreshStep8DigitalHumanStatus('p1', 1);
  assert.equal(unknown.unknown, true);
  assert.equal(unknown.canRender, false);
  console.log('output distribution checks passed: disabled bypass, full readiness, unknown blocks');
})().catch(error => {console.error(error); process.exitCode = 1;});
