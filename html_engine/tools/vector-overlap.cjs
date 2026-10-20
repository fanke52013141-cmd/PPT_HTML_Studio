"use strict";
// Exact linear SVG centreline tests with conservative stroke envelopes.
// Unsupported shapes fail closed through the caller's original box check.
const VERSION = 'svg-linear-stroke/0.1.0';
function linearSegments(d, matrix) {
  if(typeof d!=='string' || !Array.isArray(matrix) || matrix.length!==6 || !matrix.every(Number.isFinite)) return null;
  const tokens=d.match(/[MLHVZmlhvz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?/ig) || [];
  if(d.replace(/[MLHVZmlhvz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?|[\s,]/ig,'') || tokens.length>8192) return null;
  const transform=p=>({x:matrix[0]*p.x+matrix[2]*p.y+matrix[4],y:matrix[1]*p.x+matrix[3]*p.y+matrix[5]});
  let i=0,command=null,current={x:0,y:0},origin=null;
  const segments=[];
  while(i<tokens.length) {
    if(/^[a-z]$/i.test(tokens[i])) command=tokens[i++];
    if(!command) return null;
    const upper=command.toUpperCase(),relative=command!==upper;
    if(upper==='Z') {
      if(!origin) return null;
      segments.push({a:transform(current),b:transform(origin)});current={...origin};command=null;continue;
    }
    const count=['M','L'].includes(upper)?2:1;
    if(i+count>tokens.length || tokens.slice(i,i+count).some(v=>/^[a-z]$/i.test(v))) return null;
    const values=tokens.slice(i,i+count).map(Number);i+=count;
    if(!values.every(Number.isFinite)) return null;
    let next={...current};
    if(upper==='H') next.x=values[0]+(relative?current.x:0);
    else if(upper==='V') next.y=values[0]+(relative?current.y:0);
    else next={x:values[0]+(relative?current.x:0),y:values[1]+(relative?current.y:0)};
    if(upper==='M') {origin={...next};command=relative?'l':'L';}
    else {
      if(!origin) return null;
      segments.push({a:transform(current),b:transform(next)});
    }
    current=next;
  }
  return segments.length && segments.every(s=>[s.a.x,s.a.y,s.b.x,s.b.y].every(Number.isFinite))?segments:null;
}
function interval(segment,rect,padding=0) {
  if(!rect || ![rect.x,rect.y,rect.width,rect.height,padding].every(Number.isFinite)) return null;
  let lo=0,hi=1;
  for(const [start,delta,min,max] of [
    [segment.a.x,segment.b.x-segment.a.x,rect.x-padding,rect.x+rect.width+padding],
    [segment.a.y,segment.b.y-segment.a.y,rect.y-padding,rect.y+rect.height+padding]]) {
    if(Math.abs(delta)<1e-9) {if(start<min || start>max) return null;}
    else {const x=(min-start)/delta,y=(max-start)/delta;lo=Math.max(lo,Math.min(x,y));hi=Math.min(hi,Math.max(x,y));if(lo>hi) return null;}
  }
  return [lo,hi];
}
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
function relationProgress(main,geometry) {
  if(!main || distance(main.a,geometry.from)>=1) return null;
  const dx=geometry.to.x-geometry.from.x,dy=geometry.to.y-geometry.from.y,len2=dx*dx+dy*dy;
  if(len2<1e-9) return null;
  const projection=((main.b.x-geometry.from.x)*dx+(main.b.y-geometry.from.y)*dy)/len2;
  const cross=Math.abs((main.b.x-geometry.from.x)*dy-(main.b.y-geometry.from.y)*dx)/Math.sqrt(len2);
  return projection>=-1e-6 && projection<=1+1e-6 && cross<1?projection:null;
}
function endpointSegment(segment,index,node,target,geometry,box) {
  if(!node.from || !node.to || !geometry?.from || !geometry?.to) return false;
  const progress=relationProgress(segment.main,geometry);
  if(progress===null) return false;
  const identities=[['from',node.from.objectId],['to',node.to.objectId]].filter(([,id])=>id===target);
  for(const [side] of identities) {
    const endpoint=geometry[side];
    if(!interval({a:endpoint,b:endpoint},box,1)) continue;
    if(index===0) return true;
    // A short canonical head may return across its declared source boundary.
    // Limit that contact by the actual head length; never exempt other objects.
    const headLength=distance(segment.a,segment.b);
    const tip=segment.main.b;
    const edgeDistance=Math.hypot(Math.max(box.x-tip.x,0,tip.x-box.x-box.width),
                                 Math.max(box.y-tip.y,0,tip.y-box.y-box.height));
    if(index>0 && progress>0.99 && headLength<=14 && edgeDistance<=headLength &&
       (distance(segment.a,tip)<1 || distance(segment.b,tip)<1)) return true;
  }
  return false;
}
function pathsFor(frame,id) {
  const paths=frame.vectorPaths?.[id];
  if(!paths?.length) return null;
  const result=[];
  for(const path of paths) {
    if(!path.supported || !Number.isFinite(path.radius) || path.radius<0) return null;
    const segments=linearSegments(path.d,path.matrix);
    if(!segments) return null;
    result.push(...segments.map((segment,index)=>({...segment,index,main:segments[0],radius:path.radius})));
  }
  return result;
}
function vectorObject(frame,node,target) {
  const segments=pathsFor(frame,node.id),box=frame.boxes[target];
  if(!segments || !box || !frame.textRects?.[target]) return null;
  const hits=segments.filter(s=>interval(s,box,s.radius));
  if(!hits.length) return {overlap:false,method:VERSION};
  for(const s of hits) {
    const text=frame.textRects[target].find(rect=>interval(s,rect,s.radius));
    if(text) return {overlap:true,method:VERSION,reason:'stroke_crosses_text',textRect:text};
  }
  if(hits.every(s=>endpointSegment(s,s.index,node,target,frame.geometry?.[node.id],box)))
    return {overlap:false,contact:true,method:VERSION,reason:'declared_endpoint_nontext_contact'};
  return {overlap:true,method:VERSION,reason:'stroke_crosses_object'};
}
function vectorPair(frame,a,b,nodes) {
  const first=nodes.find(n=>n.id===a),second=nodes.find(n=>n.id===b);
  if(first?.type==='arrow' && second?.type!=='arrow') return vectorObject(frame,first,b);
  if(second?.type==='arrow' && first?.type!=='arrow') return vectorObject(frame,second,a);
  if(first?.type==='arrow' && second?.type==='arrow') {
    const x=pathsFor(frame,a),y=pathsFor(frame,b);
    if(!x || !y) return null;
    for(const one of x) for(const two of y) if(segmentDistance(one,two)<=one.radius+two.radius)
      return {overlap:true,method:VERSION,reason:'stroke_crosses_stroke'};
    return {overlap:false,method:VERSION};
  }
  // Unsupported SVG retains the conservative original box check.
  return null;
}
function segmentDistance(one,two) {
  const cross=(a,b)=>a.x*b.y-a.y*b.x,subtract=(a,b)=>({x:a.x-b.x,y:a.y-b.y});
  const r=subtract(one.b,one.a),s=subtract(two.b,two.a),q=subtract(two.a,one.a),den=cross(r,s);
  if(Math.abs(den)>1e-9) {
    const t=cross(q,s)/den,u=cross(q,r)/den;
    if(t>=0 && t<=1 && u>=0 && u<=1) return 0;
  }
  function pointDistance(p,segment) {
    const dx=segment.b.x-segment.a.x,dy=segment.b.y-segment.a.y,length=dx*dx+dy*dy;
    const t=length?Math.max(0,Math.min(1,((p.x-segment.a.x)*dx+(p.y-segment.a.y)*dy)/length)):0;
    return distance(p,{x:segment.a.x+t*dx,y:segment.a.y+t*dy});
  }
  return Math.min(pointDistance(one.a,two),pointDistance(one.b,two),pointDistance(two.a,one),pointDistance(two.b,one));
}
module.exports={VERSION,linearSegments,interval,vectorPair};
