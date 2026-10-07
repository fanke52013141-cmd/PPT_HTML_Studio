"use strict";
// Experimental pure time evaluator: milliseconds -> complete visual state.
(() => {
  const durationMs=12000;
  const paths=[
    {id:"drop-a",start:2200,end:5100,points:[[1060,425],[1015,460],[1130,575],[1230,570]],scale:0.88},
    {id:"drop-b",start:2500,end:5400,points:[[1390,400],[1460,480],[1300,490],[1250,560]],scale:1},
    {id:"drop-c",start:2700,end:5400,points:[[1440,690],[1400,720],[1290,650],[1240,585]],scale:0.72}
  ];
  const progress=(t,a,b)=>Math.max(0,Math.min(1,(t-a)/(b-a)));
  const smooth=p=>p*p*(3-2*p);
  const lerp=(a,b,p)=>a+(b-a)*p;
  function bezier(points,p){const q=1-p;return [0,1].map(axis=>q*q*q*points[0][axis]+3*q*q*p*points[1][axis]+3*q*p*p*points[2][axis]+p*p*p*points[3][axis]);}
  function evaluate(tMs){
    if(!Number.isFinite(tMs)||tMs<0||tMs>durationMs)throw new RangeError("tMs must be finite and within [0,12000]");
    const merge=smooth(progress(tMs,5400,6700)),zoom=smooth(progress(tMs,7800,9800));
    const camera={x:lerp(960,1060,zoom),y:lerp(540,555,zoom),z:lerp(1,1.15,zoom)};
    const drops=paths.map(path=>{const [x,y]=bezier(path.points,smooth(progress(tMs,path.start,path.end)));return {id:path.id,x,y,scale:path.scale,opacity:1-merge};});
    const phase=tMs<2200?0:tMs<5400?1:tMs<7800?2:3;
    return {tMs,camera,drops,merged:{x:1245,y:570,scale:lerp(.7,1,merge),opacity:merge},phase,
      caption:["放大观察：杯壁上的小水滴","小水滴逐渐靠近","接触后，汇集为更大的水滴","聚焦观察：变化发生在同一个场景中"][phase]};
  }
  window.objectMotion={durationMs,evaluate};
})();
