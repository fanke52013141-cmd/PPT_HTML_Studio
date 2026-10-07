(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const colors = {ink:'#344660',pink:'#f28ca1',yellow:'#f3ca69',blue:'#9fc8e9',green:'#a8cfad',purple:'#c8b8e8'};
  const make = (tag,attrs,parent) => {
    const node = document.createElementNS(NS,tag);
    for(const [key,value] of Object.entries(attrs)) node.setAttribute(key,String(value));
    parent?.append(node); return node;
  };
  const line = (svg,d,color,width=4) => make('path',{d,fill:'none',stroke:color,'stroke-width':width,'stroke-linecap':'round','stroke-linejoin':'round'},svg);
  const clamp = value => Math.max(0,Math.min(1,value));
  const smooth = value => {const x=clamp(value);return x*x*(3-2*x);};
  let nextId=0;
  function mount(parent,type,options={}) {
    if(!['label','underline','arrow','icon'].includes(type)) throw new Error('Unknown watercolor effect');
    const w=Number(options.width||300),h=Number(options.height||100);
    if(!Number.isFinite(w)||!Number.isFinite(h)||w<70||h<28||w>1600||h>900) throw new RangeError('Invalid effect dimensions');
    const color=colors[options.color||'pink'];
    if(!color) throw new Error('Unknown palette color');
    const root=document.createElement('div');root.className='wc-effect wc-'+type;root.dataset.effectId=options.id||type;
    root.style.width=w+'px';root.style.height=h+'px';parent.append(root);
    const svg=make('svg',{viewBox:`0 0 ${w} ${h}`,width:w,height:h,'aria-hidden':'true'},root);
    let stroke=null,fill=null,word=null;
    if(type==='label') {
      const text=String(options.text||'');if(!text||[...text].length>14) throw new Error('Label text outside capacity');
      const font=Number(options.fontSize||36);if(font<20||font>58) throw new RangeError('Invalid label font');
      const measure=document.createElement('canvas').getContext('2d');measure.font=`700 ${font}px STKaiti`;
      if(measure.measureText(text).width>w-38) throw new Error('Label text does not fit');
      const shape=`M 12 ${h*.27} Q ${w*.24} ${h*.12} ${w*.52} ${h*.19} Q ${w*.78} ${h*.1} ${w-13} ${h*.23} L ${w-8} ${h*.75} Q ${w*.72} ${h*.89} ${w*.48} ${h*.82} Q ${w*.2} ${h*.93} 11 ${h*.73} Z`;
      const serial=++nextId,clipId='wc-label-clip-'+serial,gradientId='wc-label-wash-'+serial;
      const defs=make('defs',{},svg),gradient=make('linearGradient',{id:gradientId,x1:'0%',x2:'95%',y1:'0%',y2:'100%'},defs);
      make('stop',{offset:'0%','stop-color':'#fff8f3'},gradient);make('stop',{offset:'22%','stop-color':color},gradient);make('stop',{offset:'72%','stop-color':color},gradient);make('stop',{offset:'100%','stop-color':'#fffaf5'},gradient);
      const clip=make('clipPath',{id:clipId},defs);make('path',{d:shape},clip);
      fill=make('path',{d:shape,fill:`url(#${gradientId})`,opacity:'.78'},svg);
      const texture=make('g',{'clip-path':`url(#${clipId})`,opacity:'.22'},svg);
      for(let i=0;i<13;i++) {const y=h*.15+i*h*.055;line(texture,`M 12 ${y} L ${33+i%4*4} ${y-4} M ${w-36-i%3*3} ${y+2} L ${w-10} ${y-3}`,i%3===0?'#fffaf4':colors.ink,i%3===0?1.6:.65);}
      make('path',{d:`M 17 ${h*.36} Q ${w*.48} ${h*.2} ${w-18} ${h*.34} M 15 ${h*.72} Q ${w*.5} ${h*.87} ${w-20} ${h*.68}`,fill:'none',stroke:'#fff8f1','stroke-width':Math.max(4,h*.11),opacity:'.33','stroke-linecap':'round','clip-path':`url(#${clipId})`},svg);
      stroke=line(svg,`M 13 ${h*.26} Q ${w*.27} ${h*.15} ${w*.52} ${h*.18} Q ${w*.8} ${h*.1} ${w-12} ${h*.24} L ${w-8} ${h*.74} Q ${w*.73} ${h*.88} ${w*.49} ${h*.82} Q ${w*.19} ${h*.94} 10 ${h*.73} Z`,colors.ink,1.8);
      word=document.createElement('span');word.className='wc-label-text';word.textContent=text;word.style.fontSize=font+'px';root.append(word);
    } else if(type==='underline') {
      stroke=line(svg,`M 6 ${h*.48} Q ${w*.24} ${h*.8} ${w*.5} ${h*.47} Q ${w*.73} ${h*.21} ${w-7} ${h*.53} M ${w*.1} ${h*.8} Q ${w*.51} ${h*.65} ${w*.9} ${h*.7}`,color,Math.max(4,h*.17));
    } else if(type==='arrow') {
      stroke=line(svg,`M 8 ${h*.77} Q ${w*.38} ${h*.06} ${w*.83} ${h*.4} M ${w*.68} ${h*.2} L ${w*.84} ${h*.4} L ${w*.65} ${h*.5}`,colors.ink,3.2);
    } else {
      const icon=String(options.icon||'spark');
      if(icon==='spark') stroke=line(svg,`M ${w*.5} 7 L ${w*.56} ${h*.4} L ${w-7} ${h*.51} L ${w*.57} ${h*.59} L ${w*.49} ${h-7} L ${w*.42} ${h*.6} L 8 ${h*.5} L ${w*.42} ${h*.41} Z`,color,3);
      else if(icon==='leaf') stroke=line(svg,`M ${w*.13} ${h*.83} Q ${w*.26} ${h*.28} ${w*.86} ${h*.14} Q ${w*.89} ${h*.74} ${w*.13} ${h*.83} M ${w*.19} ${h*.79} Q ${w*.42} ${h*.53} ${w*.78} ${h*.25}`,color,3);
      else throw new Error('Unknown icon');
    }
    if(stroke) {const length=stroke.getTotalLength();stroke.style.strokeDasharray=length;stroke.dataset.length=String(length);}
    const api={element:root,at(progress){if(!Number.isFinite(progress)||progress<0||progress>1) throw new RangeError('Invalid progress');const q=smooth(progress);root.style.opacity=String(smooth(progress*2));if(fill) fill.style.opacity=String(.63*q);if(stroke) stroke.style.strokeDashoffset=String(Number(stroke.dataset.length)*(1-q));if(word) word.style.opacity=String(smooth((progress-.22)*2));},geometry(){const b=root.getBoundingClientRect();return {id:root.dataset.effectId,x:b.x,y:b.y,width:b.width,height:b.height};},destroy(){root.remove();}};
    api.at(0);return api;
  }
  window.WatercolorEffects={version:'0.1.0',colors,mount};
})();
