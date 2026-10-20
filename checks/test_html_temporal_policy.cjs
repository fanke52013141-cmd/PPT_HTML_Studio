"use strict";
const assert=require('node:assert/strict');
const {timeCoverage,overlapPolicy}=require('../html_engine/tools/temporal-review.cjs');
const policy=require('../html_engine/visual/qa/overlap-policy.json');
const scene={durationMs:1000,motion:[{startMs:123,durationMs:150}],templateRef:{id:'explanation-cards-v1',version:'0.1.0'},nodes:[{id:'panel',slot:'figure',type:'figure'},{id:'subject',slot:'subject',type:'image'},{id:'title',slot:'header',type:'header'}]};
const coverage=timeCoverage(scene,{sampling_mode:'output_frames',fps:30});
for(let i=0;i<=30;i++) assert(coverage.times.includes(Math.round(i*1000/30)));
assert(coverage.times.includes(123) && coverage.times.includes(273));
assert(coverage.frame_complete && !coverage.continuous_time_verified);
assert.throws(()=>timeCoverage({...scene,durationMs:120000},{sampling_mode:'sampled'}),/BUDGET/);
const pairs=overlapPolicy(scene,{overlap_policy:'registered'},policy);
assert.equal(pairs.pairs.length,2);assert.equal(pairs.exclusions[0].source,'template:explanation-cards-v1@0.1.0:figure/subject');
assert.throws(()=>overlapPolicy({...scene,templateRef:{id:'unknown',version:'0.1.0'}},{overlap_policy:'registered'},policy),/UNREGISTERED/);
for (const id of ['science-relations-v1','chart-explanation-v1','process-three-stages-v1']) {
  const template=require(`../html_engine/visual/templates/${id}.json`);
  assert.equal(policy.templates[id].version,template.version);
  const candidate={...scene,templateRef:{id,version:template.version},nodes:[
    ...scene.nodes,{id:'connector',slot:'relation-1',type:'arrow'}]};
  const result=overlapPolicy(candidate,{overlap_policy:'registered'},policy);
  assert.equal(result.exclusions.length,id==='science-relations-v1'?1:0);
  assert(result.pairs.some(pair=>pair.includes('connector') && pair.includes('subject')));
  assert.throws(()=>overlapPolicy({...candidate,templateRef:{id,version:'99.0.0'}},{overlap_policy:'registered'},policy),/UNREGISTERED/);
}
console.log('Temporal policy: output-frame completeness, action boundaries, budgets and registered exclusion provenance passed');
