"use strict";
const assert=require('node:assert/strict');
const {linearSegments,interval,vectorPair}=require('../html_engine/tools/vector-overlap.cjs');
const identity=[1,0,0,1,0,0];
assert.deepEqual(linearSegments('M 10 20 h 30 v 10 l -5 -5 Z',identity),[
  {a:{x:10,y:20},b:{x:40,y:20}}, {a:{x:40,y:20},b:{x:40,y:30}},
  {a:{x:40,y:30},b:{x:35,y:25}}, {a:{x:35,y:25},b:{x:10,y:20}}]);
assert.deepEqual(linearSegments('M0 0L2 3',[0,2,-2,0,10,20]),[{a:{x:10,y:20},b:{x:4,y:24}}]);
assert.equal(linearSegments('M0 0 Q20 10 40 40',identity),null);
assert.equal(linearSegments('M0',identity),null);
assert.equal(linearSegments('M0 0 L Infinity 1',identity),null);
assert.equal(linearSegments('H20',identity),null);
assert(interval({a:{x:0,y:10},b:{x:100,y:10}},{x:20,y:9,width:10,height:2}));
assert.equal(interval({a:{x:0,y:0},b:{x:100,y:100}},{x:10,y:70,width:10,height:10}),null);

const nodes=[{id:'line',type:'arrow',from:{objectId:'origin'},to:{objectId:'target'}},{id:'target',type:'chart'},{id:'other',type:'text'}];
function frame(d) {
  return {boxes:{target:{x:60,y:0,width:40,height:80},other:{x:10,y:70,width:10,height:10}},
    textRects:{target:[],other:[]},vectorPaths:{line:[{d,matrix:identity,radius:1,supported:true}]},
    geometry:{line:{from:{x:0,y:40},to:{x:80,y:40}}}};
}
let f=frame('M0 40L80 40 M70 35L80 40L70 45');
assert(vectorPair(f,'line','target',nodes).contact);
assert.equal(vectorPair(f,'line','target',nodes).overlap,false);
f.boxes.origin={x:-5,y:0,width:100,height:80};f.textRects.origin=[];
nodes.push({id:'origin',type:'image'});
assert(vectorPair(f,'line','origin',nodes).contact); // overlapping declared containers, not a global exclusion
f.boxes.origin.width=80; // target tip lies 5px past the source boundary; short canonical head returns across that edge
assert(vectorPair(f,'line','origin',nodes).contact);
f.textRects.target=[{x:65,y:35,width:10,height:10}];
assert.equal(vectorPair(f,'line','target',nodes).reason,'stroke_crosses_text');
f=frame('M0 0L100 100');
assert.equal(vectorPair(f,'line','other',nodes).overlap,false); // diagonal box overlap, path misses
f.boxes.other={x:30,y:30,width:10,height:10};
assert.equal(vectorPair(f,'line','other',nodes).reason,'stroke_crosses_object');
f=frame('M0 0 C10 10 20 20 80 40');
assert.equal(vectorPair(f,'line','target',nodes),null); // caller retains conservative fallback
f=frame('M0 40L398 40 M388 35L398 40L388 45');
f.geometry.line.to={x:400,y:40};f.boxes.target={x:360,y:0,width:80,height:80};
assert(vectorPair(f,'line','target',nodes).contact); // 99.5% draw: painted head has not yet reached final endpoint
f.vectorPaths.line[0].d='M0 40L398 40 M370 35L380 40L370 45';
assert.equal(vectorPair(f,'line','target',nodes).reason,'stroke_crosses_object');
f=frame('M0 0L100 100');
f.vectorPaths.second=[{d:'M0 20L80 100',matrix:identity,radius:1,supported:true}];
nodes.push({id:'second',type:'arrow'});
assert.equal(vectorPair(f,'line','second',nodes).overlap,false);
f.vectorPaths.second[0].d='M0 100L100 0';
assert.equal(vectorPair(f,'line','second',nodes).reason,'stroke_crosses_stroke');
console.log('Linear SVG overlap: transformed segments, text crossings, endpoint provenance and fallback passed');
