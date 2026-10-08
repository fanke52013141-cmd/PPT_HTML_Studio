const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/ui_foundation.js'), 'utf8');
const ctx = {};
vm.runInNewContext(source.slice(source.indexOf('function setUiTaskState(')), ctx);
const node = {classList:{add(){}},dataset:{},attrs:{},setAttribute(k,v){this.attrs[k]=v;}};
ctx.setUiTaskState(null, 'running', '生成中');
ctx.setUiTaskState(node, 'running', '生成中');
assert.equal(node.attrs['aria-busy'], 'true');
ctx.setUiTaskState(node, 'error', '请求失败');
assert.equal(node.attrs['aria-busy'], 'false');
assert.equal(node.textContent, '请求失败');
ctx.setUiTaskState(node, 'done', '完成');
assert.equal(node.dataset.taskState, 'done');
assert.equal(node.attrs['aria-live'], 'polite');
console.log('task presentation checks passed');

const storyboardSource = fs.readFileSync(path.join(__dirname, '../static/storyboard.js'), 'utf8');
const scriptNode = {classList:{add(){}},dataset:{},setAttribute(){}};
const visualNode = {classList:{add(){}},dataset:{},setAttribute(){}};
ctx.state = {step2ScriptPlan:{slides:[{}]},step2VisualExists:true,step2VisualStale:false};
ctx.document = {getElementById: id => id === 'step2-script-task-status' ? scriptNode : id === 'step2-visual-task-status' ? visualNode : null};
vm.runInNewContext(storyboardSource.slice(storyboardSource.indexOf('let step2TaskPhases'), storyboardSource.indexOf('function step2CurrentProjectId')), ctx);
ctx.refreshStep2TaskStates();
assert.equal(visualNode.dataset.taskState, 'done');
ctx.setStep2TaskPhase('visual','done');
ctx.state.step2VisualStale = true;
ctx.refreshStep2TaskStates();
assert.equal(visualNode.dataset.taskState, 'pending');
ctx.setStep2TaskPhase('script','running');
assert.equal(scriptNode.dataset.taskState, 'running');
assert.equal(visualNode.dataset.taskState, 'pending');
ctx.setStep2TaskPhase('script','error');
assert.equal(scriptNode.dataset.taskState, 'error');
console.log('storyboard independent task checks passed');

const outputSource = fs.readFileSync(path.join(__dirname, '../static/output_render.js'), 'utf8');
const outputText = {classList:{add(){}},dataset:{},setAttribute(){},textContent:''};
const loadingBox = {dataset:{}};
ctx.document = {getElementById: id => id === 'step8-loading-text' ? outputText : loadingBox};
vm.runInNewContext(outputSource.slice(outputSource.indexOf('function updateStep8LoadingText('), outputSource.indexOf('async function refreshStep8DigitalHumanStatus')), ctx);
ctx.updateStep8LoadingText(null, 0, 0);
assert.equal(outputText.innerText, '排队中，等待渲染');
assert.equal(loadingBox.dataset.taskState, 'queued');
ctx.updateStep8LoadingText('构建场景', 12);
assert.equal(loadingBox.dataset.taskState, 'running');
assert.match(outputText.innerText, /构建场景/);
console.log('output queued/running presentation checks passed');

// A content loader reserves geometry, announces real state, and drops skeletons
// on completion while retaining the readable completion message.
function element() {
  return {dataset:{},children:[],attrs:{},hidden:false,classList:{toggle(){}},
    setAttribute(k,v){this.attrs[k]=v;},
    append(...nodes){this.children.push(...nodes);},
    appendChild(node){this.children.push(node);},
    prepend(node){this.children.unshift(node);},
    querySelector(selector){return this.children.find(n=>'.'+n.className===selector);}};
}
ctx.document = {createElement: element};
const host = element();
ctx.renderPageTaskState(host, 'audio', 'running', '正在生成本页音频', 'audio');
assert.equal(host.children.length, 1);
const surface = host.children[0];
assert.equal(surface.attrs['aria-busy'], 'true');
assert.equal(surface.querySelector('.page-task-skeleton').children.length, 4);
ctx.renderPageTaskState(host, 'audio', 'done', '音频已完成', 'audio');
assert.equal(host.children.length, 1);
assert.equal(surface.querySelector('.page-task-skeleton').hidden, true);
assert.equal(surface.hidden, true);
assert.equal(surface.querySelector('.page-task-title').textContent, '音频已完成');
ctx.renderPageTaskState(host, 'audio', null, '', 'audio');
assert.equal(surface.hidden, true);
console.log('page-level task surface checks passed');

const content = element();
host.append(content);
ctx.renderPageTaskState(host, 'audio', 'running', '生成中', 'audio');
assert.equal(content.hidden, true);
ctx.renderPageTaskState(host, 'audio', 'done', '已完成', 'audio');
assert.equal(content.hidden, false);
console.log('output replacement and restoration checks passed');
