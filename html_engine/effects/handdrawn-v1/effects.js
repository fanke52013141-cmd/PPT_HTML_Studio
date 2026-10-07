(function (global) {
  'use strict';
  const ns='http://www.w3.org/2000/svg';
  const palette={paper:'#fffaf0',ink:'#343c49',yellow:'#ffdf87',blue:'#8bc7d0',coral:'#d86856',font:'Microsoft YaHei'};
  const specs={paper:[180,70],arrow:[180,100],mark:[280,90],sun:[100,100],flow:[180,140],text:[180,70],panel:[180,100]};
  const clamp=x=>Math.max(0,Math.min(1,x));
  const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
  const out=x=>x===1?1:1-Math.pow(2,-8*x)*Math.cos(10*x);
  function svgNode(tag,attrs,parent){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(parent)parent.append(e);return e;}
  function mount(parent,type,p={},theme={}) {
    if(!specs[type])throw new Error('Unknown effect '+type);
    const t={...palette,...theme}, w=p.width??400,h=p.height??170;
    if(!Number.isFinite(w)||!Number.isFinite(h)||w<specs[type][0]||h<specs[type][1]||w>1600||h>1000)throw new Error('Effect size outside supported range');
    const text=String(p.text??''),limit={paper:12,mark:16,text:80}[type];
    if(limit&&[...text].length>limit)throw new Error('Text exceeds effect capacity');
    const font=p.fontSize??32;
    if(!Number.isFinite(font)||font<20||font>64)throw new Error('Font outside20—64');
    const tilt=p.tilt??-2,stroke=p.stroke??4,count=p.count??6,seed=p.seed??17;
    if(!Number.isFinite(tilt)||Math.abs(tilt)>6||!Number.isFinite(stroke)||stroke<2||stroke>8)throw new Error('Invalid tilt/stroke');
    if(!Number.isInteger(count)||count<1||count>24||!Number.isInteger(seed))throw new Error('Invalid particle count/seed');
    const radius=p.radius??16;if(!Number.isFinite(radius)||radius<0||radius>32)throw new Error('Invalid radius');
    if(type==='paper'||type==='mark'){const measure=document.createElement('canvas').getContext('2d');measure.font=`${type==='paper'?'700 ':''}${font}px "${t.font}"`;if(measure.measureText(text).width>w*(type==='mark'?.72:1)-20)throw new Error('Text does not fit the selected effect width');}
    const e=document.createElement('div');e.className='flat-effect flat-'+type;e.dataset.effect=p.id??type;
    Object.assign(e.style,{position:'relative',width:w+'px',height:h+'px',fontFamily:t.font+', sans-serif',color:t.ink});parent.append(e);
    let paint=()=>{},positions=[];
    if(type==='paper') {
      Object.assign(e.style,{background:t.yellow,border:`3px solid ${t.ink}`,borderRadius:'8px',boxShadow:`6px 6px 0 ${t.ink}`,display:'flex',alignItems:'center',justifyContent:'center',fontSize:font+'px',fontWeight:'700',whiteSpace:'nowrap'});e.textContent=text;
      paint=q=>{e.style.opacity=smooth(q*3);e.style.transform=`translateY(${(1-out(q))*30}px) rotate(${tilt}deg) scale(${.93+.07*out(q)})`;};
    } else if(type==='panel') {
      Object.assign(e.style,{background:t.paper,border:`2px solid ${t.ink}`,borderRadius:radius+'px'});paint=q=>{e.style.opacity=smooth(q);e.style.clipPath=`inset(0 ${(1-smooth(q))*100}% 0 0)`;};
    } else if(type==='text') {
      Object.assign(e.style,{fontSize:font+'px',fontWeight:p.bold?'700':'400',lineHeight:'1.4',whiteSpace:'normal'});
      const accent=String(p.accent??''),at=accent?text.indexOf(accent):-1;
      if(at>=0){e.append(document.createTextNode(text.slice(0,at)));const span=document.createElement('span');span.textContent=accent;span.style.color=t.coral;e.append(span,document.createTextNode(text.slice(at+accent.length)));}else e.textContent=text;
      paint=q=>{e.style.opacity=smooth(q);e.style.transform=`translateY(${12*(1-smooth(q))}px)`;};
    } else if(type==='flow') {
      const c=document.createElement('canvas'),dpr=Math.min(2,global.devicePixelRatio||1);c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);Object.assign(c.style,{width:w+'px',height:h+'px'});c.setAttribute('aria-label','上升粒子，数量为过程示意');e.append(c);const x=c.getContext('2d');
      paint=q=>{x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,w,h);x.strokeStyle=t.blue;x.fillStyle=t.blue;x.lineWidth=3;positions=[];
        for(let i=0;i<count;i++){const variation=((seed+i*37)%101)/101,phase=clamp(q*1.25-i*.035),px=w*(.14+.72*(i+.5)/count)+Math.sin(phase*Math.PI)*(variation-.5)*35,py=h*(.9-(.78-.24*variation)*smooth(phase));positions.push({id:(p.id??'flow')+'.particle.'+i,x:px,y:py});if(q<=0)continue;x.setLineDash([4,8]);x.beginPath();x.moveTo(px,h*.91);x.quadraticCurveTo(px-15,h*.55,px,py+10);x.stroke();x.setLineDash([]);x.beginPath();x.arc(px,py,6,0,Math.PI*2);x.fill();}
      };
    } else {
      const s=svgNode('svg',{viewBox:`0 0 ${w} ${h}`,width:w,height:h},e);let line,head;
      if(type==='arrow'){line=svgNode('path',{d:`M ${w*.08} ${h*.8} Q ${w*.5} ${h*.12} ${w*.9} ${h*.46}`,fill:'none',stroke:t.ink,'stroke-width':stroke,'stroke-linecap':'round'},s);head=svgNode('path',{d:`M ${w*.9-24} ${h*.46-17} L ${w*.9} ${h*.46} L ${w*.9-29} ${h*.46+8}`,fill:'none',stroke:t.ink,'stroke-width':stroke,'stroke-linecap':'round','stroke-linejoin':'round'},s);}
      if(type==='mark'){const tx=svgNode('text',{x:w/2,y:h*.6,'text-anchor':'middle',fill:t.ink,'font-size':font,'font-family':t.font},s);tx.textContent=text;line=svgNode('path',{d:`M ${w*.13} ${h*.2} C ${w*.8} ${-h*.03} ${w*.98} ${h*.3} ${w*.89} ${h*.75} C ${w*.65} ${h*1.04} ${w*.07} ${h*.92} ${w*.08} ${h*.45} Q ${w*.08} ${h*.24} ${w*.16} ${h*.21}`,fill:'none',stroke:t.coral,'stroke-width':stroke,'stroke-linecap':'round'},s);head=tx;}
      if(type==='sun'){const cx=w/2,cy=h/2,r=Math.min(w,h)*.23;svgNode('circle',{cx,cy,r,fill:t.yellow,stroke:t.ink,'stroke-width':stroke},s);for(let i=0;i<8;i++){const a=i*Math.PI/4;svgNode('line',{x1:cx+Math.cos(a)*r*1.5,y1:cy+Math.sin(a)*r*1.5,x2:cx+Math.cos(a)*r*1.95,y2:cy+Math.sin(a)*r*1.95,stroke:t.ink,'stroke-width':stroke,'stroke-linecap':'round'},s);}paint=q=>{e.style.opacity=smooth(q*3);e.style.transform=`rotate(${Math.sin(q*Math.PI)*8}deg) scale(${.88+.12*out(q)})`;};}
      if(line){const length=line.getTotalLength();line.style.strokeDasharray=length;paint=q=>{line.style.strokeDashoffset=length*(1-smooth(q));if(head)head.style.opacity=type==='mark'?smooth(q*3):smooth((q-.8)*5);};}
    }
    function at(q){if(!Number.isFinite(q)||q<0||q>1)throw new Error('Progress outside0—1');paint(q);}
    at(0);
    return {element:e,at,geometry:()=>{const r=e.getBoundingClientRect();return {id:p.id??type,x:r.x,y:r.y,width:r.width,height:r.height,particles:positions.map(o=>({...o}))};},destroy:()=>e.remove()};
  }
  global.FlatEffects={version:'0.1.0',mount,palette,types:Object.keys(specs)};
})(window);
