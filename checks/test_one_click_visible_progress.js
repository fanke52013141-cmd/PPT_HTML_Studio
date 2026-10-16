const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/one_click_extension.js'), 'utf8');
const block = source.slice(source.indexOf('    const visibleStages = ('), source.indexOf('    // 阶段变化时同步切换'));
function render(list, state, features = {}, status = {backend:'image'}) {
  const stages = {innerHTML: '', querySelectorAll: () => []};
  vm.runInNewContext(block, {list, state, stages, features, status, esc: x => String(x), statusLabel: x => x});
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
const html = render([{id:'html_pages',status:'waiting_for_review',message:'confirm actual design'}], 'waiting_for_review', {}, {backend:'html'});
assert.equal((html.match(/<article/g) || []).length, 6);
assert.match(html, /设计图 → HTML 还原与动画.*?paused/s);
assert.match(html, /逐句语义审核|当前签收/);
assert.doesNotMatch(html, /AI 标注|勾画标注/);

async function reviewCheckpointRefresh() {
  const live = source.slice(source.indexOf('  async function syncLivePanel('), source.indexOf('  function renderStatus('));
  let reads = 0;
  const runtime = {currentProject:{id:'fixture'},currentStep:2};
  const context = {window:{PPTStudio:{runtime:{state:runtime}},loadStep2Data:async()=>{reads++;}},
    activeProjectId:()=>runtime.currentProject.id,console};
  vm.runInNewContext('let panelRefreshInFlight=false, previousPanelStage="", oneClickContentStage="", loadedScriptReviewKey="";'+live+';globalThis.sync=syncLivePanel;',context);
  const waiting = {status:'waiting_for_user',current_stage:'storyboard',job_id:'original',review_checkpoint:'script_review'};
  await context.sync(waiting);
  await context.sync(waiting);
  assert.equal(reads,1,'polling must not reload the review editor while typing');
  await context.sync({status:'running',current_stage:'storyboard'});
  await context.sync(waiting);
  assert.equal(reads,2,'a later review boundary must be readable again');
  runtime.currentStep=3;
  await context.sync({...waiting,job_id:'another'});
  assert.equal(reads,2,'other panels must not load storyboard review');
}
reviewCheckpointRefresh().catch(error=>{console.error(error);process.exitCode=1;});
