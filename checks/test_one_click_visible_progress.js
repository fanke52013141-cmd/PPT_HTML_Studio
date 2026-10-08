const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/one_click_extension.js'), 'utf8');
const block = source.slice(source.indexOf('    const visibleStages = ['), source.indexOf('    // 阶段变化时同步切换'));
function render(list, state, features = {}) {
  const stages = {innerHTML: '', querySelectorAll: () => []};
  vm.runInNewContext(block, {list, state, stages, features, esc: x => String(x), statusLabel: x => x});
  return stages.innerHTML;
}
const paused = render([{id:'narration',status:'done'},{id:'tts',status:'running',message:'synthesizing'}], 'paused');
assert.equal((paused.match(/<article/g) || []).length, 8);
assert.match(paused, /5 旁白与音频.*?paused/s);
assert.doesNotMatch(paused, /button-spinner/);
assert.match(paused, /6 勾画标注.*?pending/s);
const failed = render([{id:'tts',status:'failed',blocking_errors:['full error']}], 'failed');
assert.match(failed, /data-copy-error="4"/);
assert.match(failed, /错误：full error/);
const completed = render([{id:'render',status:'done'}], 'completed');
assert.match(completed, /6 勾画标注.*?done/s);
assert.match(completed, /7 数字人讲解.*?done/s);
const light = render([{id:'render',status:'done'}], 'completed', {handwritten_annotations:false, digital_human:false});
assert.equal((light.match(/<article/g) || []).length, 6);
assert.doesNotMatch(light, /勾画标注|数字人讲解/);
assert.match(light, /8 作品输出.*?done/s);
const partial = render([{id:'render',status:'done'}], 'completed', {handwritten_annotations:false, digital_human:true});
assert.equal((partial.match(/<article/g) || []).length, 7);
assert.match(partial, /7 数字人讲解.*?done/s);
console.log('one-click visible progress checks passed');
