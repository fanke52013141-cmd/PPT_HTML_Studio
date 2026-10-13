"use strict";
// Shared deterministic time/pair policy and actual DOM evidence, no alternate renderer.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
function timeCoverage(scene,spec) {
  const range=spec.time_range_ms || [0,scene.durationMs];
  const mode=spec.sampling_mode ?? 'sampled',step=spec.step_ms ?? 250,fps=spec.fps ?? 30;
  if(!['sampled','output_frames'].includes(mode) || range.length!==2 || !range.every(Number.isFinite) || range[0]<0 || range[1]>scene.durationMs || range[0]>range[1] || scene.durationMs>120000 || !Number.isInteger(step) || step<16 || step>1000 || !Number.isInteger(fps) || fps<1 || fps>60) throw Error('INVALID_TEMPORAL_RANGE');
  const times=new Set(range);
  if(mode==='sampled') for(let t=range[0];t<=range[1];t+=step) times.add(t);
  else for(let frame=Math.ceil(range[0]*fps/1000);frame<=Math.floor(range[1]*fps/1000);frame++) times.add(Math.round(frame*1000/fps));
  for(const a of scene.motion) for(const t of [a.startMs-1,a.startMs,a.startMs+a.durationMs/2,a.startMs+a.durationMs,a.startMs+a.durationMs+1]) if(t>=range[0] && t<=range[1]) times.add(t);
  const sorted=[...times].sort((a,b)=>a-b);
  if(sorted.length>(mode==='sampled'?240:7201)) throw Error('TEMPORAL_SAMPLE_BUDGET');
  return {times:sorted,rangeMs:range,mode,fps:mode==='output_frames'?fps:null,stepMs:mode==='sampled'?step:null,frame_complete:mode==='output_frames',continuous_time_verified:false,time_sha256:sha(JSON.stringify(sorted))};
}
function overlapPolicy(scene,spec,policy) {
  const nodes=scene.nodes.filter(n=>n.type!=='annotation'),ids=new Set(scene.nodes.map(n=>n.id));
  if(!['explicit','registered'].includes(spec.overlap_policy || 'explicit')) throw Error('INVALID_OVERLAP_POLICY');
  const key=pair=>[...pair].sort().join('\0'),excluded=new Map();
  if(spec.overlap_policy==='registered') {
    const template=policy?.templates?.[scene.templateRef?.id];
    if(policy.format!=='hps.html.overlap_policy' || policy.version!=='0.1.0' || !template || template.version!==scene.templateRef.version) throw Error('OVERLAP_POLICY_UNREGISTERED');
    for(const rule of template.allowed_pairs) {
      const a=nodes.find(n=>n.slot===rule.slots[0]),b=nodes.find(n=>n.slot===rule.slots[1]);
      if(a && b) excluded.set(key([a.id,b.id]),{targets:[a.id,b.id],reason:rule.reason,source:`template:${scene.templateRef.id}@${template.version}:${rule.slots.join('/')}`});
    }
    for(const n of scene.nodes.filter(n=>n.type==='annotation')) if(ids.has(n.targetId) && ids.has(n.labelId)) excluded.set(key([n.targetId,n.labelId]),{targets:[n.targetId,n.labelId],reason:'registered_anchor_label',source:`annotation:${n.id}`});
  }
  const pairs=spec.overlap_policy==='registered'?nodes.flatMap((a,i)=>nodes.slice(i+1).map(b=>[a.id,b.id])):(spec.overlap_pairs || []);
  for(const pair of pairs) if(!Array.isArray(pair) || pair.length!==2 || pair[0]===pair[1] || !pair.every(id=>ids.has(id))) throw Error('INVALID_OVERLAP_PAIR');
  return {pairs:[...new Map(pairs.filter(p=>!excluded.has(key(p))).map(p=>[key(p),p])).values()],exclusions:[...excluded.values()],scope:spec.overlap_policy || 'explicit'};
}
async function checkTemporalPage(page,scene,spec,dir,policy) {
  const coverage=timeCoverage(scene,spec),scope=overlapPolicy(scene,spec,policy),frames=[],issues=[],screenshots=[];
  const shotTimes=new Set([coverage.times[0],coverage.times[Math.floor(coverage.times.length/2)],coverage.times.at(-1)]);
  for(const t of coverage.times) {
    const frame=await page.evaluate(({t,annotationIds})=>{
      const result=window.visualPlayer.seek(t),stage=document.querySelector('.visual-stage').getBoundingClientRect(),scale=stage.width/1600,visible={},boxes={};
      for(const el of document.querySelectorAll('[data-object-id]')) {
        const id=el.dataset.objectId,style=getComputedStyle(el);
        let r=el.getBoundingClientRect();
        if(annotationIds.includes(id)) {
          const parts=[...el.querySelectorAll('svg circle,svg path,svg line')].map(p=>p.getBoundingClientRect()).filter(b=>b.width || b.height);
          if(parts.length) {
            const x=Math.min(...parts.map(b=>b.x)),y=Math.min(...parts.map(b=>b.y));
            r={x,y,width:Math.max(...parts.map(b=>b.right))-x,height:Math.max(...parts.map(b=>b.bottom))-y};
          }
        }
        visible[id]=style.display==='none'||style.visibility==='hidden'?0:Number(style.opacity);
        boxes[id]={x:(r.x-stage.x)/scale,y:(r.y-stage.y)/scale,width:r.width/scale,height:r.height/scale};
      }
      return {...result,visible,boxes};
    },{t,annotationIds:scene.nodes.filter(n=>n.type==='annotation').map(n=>n.id)});
    for(const [a,b] of scope.pairs) {
      if(frame.visible[a]<=0.01 || frame.visible[b]<=0.01) continue;
      const x=frame.boxes[a],y=frame.boxes[b];
      if(!x || !y) throw Error('UNSUPPORTED_PAIR_GEOMETRY');
      const width=Math.min(x.x+x.width,y.x+y.width)-Math.max(x.x,y.x),height=Math.min(x.y+x.height,y.y+y.height)-Math.max(x.y,y.y);
      if(width>1 && height>1) issues.push({code:'TEMPORAL_OVERLAP',timeMs:t,targets:[a,b],measured:{overlapWidth:width,overlapHeight:height},allowed_repairs:['layout_or_motion']});
    }
    for(const n of scene.nodes) {
      if(frame.visible[n.id]<=0.01) continue;
      const b=frame.boxes[n.id];
      if(b && (b.x < -1 || b.y < -1 || b.x+b.width>1601 || b.y+b.height>801)) issues.push({code:'TEMPORAL_SAFE_ZONE',timeMs:t,targets:[n.id],measured:b,allowed_repairs:['layout_or_motion']});
    }
    frames.push(frame);
    if(shotTimes.has(t) || (issues.some(i=>i.timeMs===t) && screenshots.length<6)) {
      const file=`frame-${screenshots.length}.png`;
      await page.locator('.visual-stage').screenshot({path:path.join(dir,file)});
      screenshots.push({timeMs:t,file});
    }
  }
  return {passed:issues.length===0,clock:spec.clock,rangeMs:coverage.rangeMs,stepMs:coverage.stepMs,finiteSampling:true,coverage,overlapPairs:scope.pairs,overlapExclusions:scope.exclusions,overlapScope:scope.scope,frames,issues,screenshots,browserVersion:page.context().browser().version()};
}
module.exports={timeCoverage,overlapPolicy,checkTemporalPage};
