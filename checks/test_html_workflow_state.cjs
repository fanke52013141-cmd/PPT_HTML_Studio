'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={window:{},API:{get:async()=>({})}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/html_workflow_state.js','utf8'),ctx);
const owner=ctx.window.HtmlWorkflowState,project={id:'p',visual_backend:'html',step_status:{'1':'completed','4':'completed','7':'completed'}};
function response(designs,pages,audio='not_started',sync='not_started'){
 return {workflow:{stages:[{id:'content_planning',status:'ready',facts:{slide_ids:['a','b']}},{id:'design_and_assets',design_candidates:designs,slides:pages},{id:'audio',status:audio},{id:'animation',status:sync},{id:'digital_human',status:'skipped'},{id:'review_and_output',targets:{mp4_video:{ready:true}}}]}};
}
const approved={status:'accepted_for_reconstruction',stale:false};
let facts=response({a:approved,b:{status:'needs_review'}},{a:{status:'ready'},b:{status:'not_started'}});
let s=owner.projectStates(project,facts);assert.equal(s[3],'pending_review');assert.equal(s[5],'in_progress');assert.equal(s[6],'pending');assert.equal(s[9],'skipped');assert.equal(s[8],'ready_to_export');
facts=response({a:approved,b:approved},{a:{status:'ready'},b:{status:'ready'}},'ready','needs_review');
s=owner.projectStates(project,facts);assert.equal(s[3],'completed');assert.equal(s[5],'completed');assert.equal(s[6],'pending_review');
facts.workflow.stages.find(s=>s.id==='animation').status='ready';assert.equal(owner.projectStates(project,facts)[6],'completed');
facts.workflow.stages.find(s=>s.id==='design_and_assets').design_candidates.b={...approved,stale:true};assert.equal(owner.projectStates(project,facts)[3],'pending_reconfirmation');
assert.equal(owner.projectStates(project,{})[5],'pending');assert.equal(owner.projectStates(project,{})[8],'pending');
(async()=>{
 ctx.API.get=async url=>url.endsWith('/videos')?{videos:[{artifact_state:'historical',historical:true}]}:facts;
 await owner.load(project,{force:true});assert.equal(owner.get('p').states[8],'ready_to_export');
 ctx.API.get=async url=>url.endsWith('/videos')?{videos:[{artifact_state:'current',historical:false}]}:facts;
 await owner.load(project,{force:true});assert.equal(owner.get('p').states[8],'completed');
 let resolveOld;ctx.API.get=url=>url.endsWith('/videos')?Promise.resolve({videos:[]}):new Promise(r=>{resolveOld=r;});
 const old=owner.load(project,{force:true});
 ctx.API.get=async url=>url.endsWith('/videos')?{videos:[]}:{workflow:{stages:[]}};
 await owner.load(project,{force:true});resolveOld(facts);await old;
 assert.equal(owner.get('p').states[5],'pending','late old read must not replace latest facts');
 ctx.API.get=async()=>{throw Error('offline');};await assert.rejects(owner.load(project,{force:true}));assert.equal(owner.get('p'),null);
 console.log('HTML workflow facts, output currentness and stale response checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
