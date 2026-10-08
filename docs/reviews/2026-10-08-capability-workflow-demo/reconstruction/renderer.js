/* Isolated, data-driven static review components. This is not a production registry. */
(() => {
  'use strict';
  const { scene, theme, assets, reference } = window.RECONSTRUCTION;
  const ns = 'http://www.w3.org/2000/svg';
  const stage = document.querySelector('#stage');
  const css = document.documentElement.style;
  Object.entries(theme.colors).forEach(([key, value]) => css.setProperty('--' + key, value));
  css.setProperty('--font', '"' + theme.font.family + '"');
  stage.style.width = scene.canvas.width + 'px';
  stage.style.height = scene.canvas.height + 'px';
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const vector = (tag, attrs, text) => {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function rich(parent, runs) {
    for (const run of runs) {
      const node = el('span', '', run.text);
      if (run.accent) node.classList.add('accent');
      if (run.underline) node.classList.add('underline');
      if (run.bold) node.style.fontWeight = '700';
      parent.append(node);
    }
  }
  function svg(w, h) {
    return vector('svg', { viewBox: `0 0 ${w} ${h}`, width: w, height: h, 'aria-hidden': true });
  }
  function line(parent, points, color, width = theme.strokeWidth) {
    parent.append(vector('path', { d: points, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
  }
  function arrow(parent, x1, y1, x2, y2, color, width = theme.strokeWidth, size = 10) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    line(parent, `M${x1} ${y1} L${x2} ${y2}`, color, width);
    line(parent, `M${x2-size*Math.cos(angle-.5)} ${y2-size*Math.sin(angle-.5)} L${x2} ${y2} L${x2-size*Math.cos(angle+.5)} ${y2-size*Math.sin(angle+.5)}`, color, width);
  }
  function st(parent, x, y, text, opts = {}) {
    const node = vector('text', { x, y, fill: opts.accent ? theme.colors.pink : theme.colors.body, 'font-size': opts.size || 23, 'font-weight': opts.bold ? 700 : 400, 'text-anchor': opts.anchor || 'start' }, text);
    parent.append(node);
    return node;
  }
  const components = {
    text(root, data) {
      const text = el('div', data.role + (data.gradient ? ' gradient-text' : ''), data.text);
      text.style.fontSize = theme.text[data.role] + 'px';
      root.append(text);
    },
    'rich-text'(root, data) {
      const text = el('div', data.role);
      text.style.fontSize = theme.text[data.role] + 'px';
      rich(text, data.runs);
      root.append(text);
    },
    'knowledge-card'(root, data) {
      const style = theme.card[data.variant];
      root.classList.add('knowledge-card');
      Object.assign(root.style, { background: style.fill, border: `${theme.card.borderWidth}px solid ${style.border}`, borderRadius: theme.card.radius + 'px' });
      const number = el('div', 'number', data.number);
      Object.assign(number.style, { width: theme.card.badgeDiameter + 'px', height: theme.card.badgeDiameter + 'px', background: style.badge });
      const title = el('div', 'card-title', data.title);
      title.style.fontSize = theme.text.cardTitle + 'px';
      const body = el('div', 'card-body');
      body.style.fontSize = theme.text[data.textRole || 'body'] + 'px';
      if (data.bodyOffset) body.style.left = data.bodyOffset + 'px';
      data.lines.forEach(runs => { const row = el('div', 'line'); rich(row, runs); body.append(row); });
      root.append(number, title, body);
    },
    'relation-arrow'(root, data) {
      const v = svg(data.box[2], data.box[3]);
      st(v, data.box[2]/2, 23, data.text, { anchor: 'middle', bold: true, size: 24 });
      arrow(v, 0, 48, data.box[2]-4, 48, theme.colors.blue, 4, 18);
      root.append(v);
    },
    image(root, data) {
      const asset = assets[data.asset];
      if (!asset) throw new Error('Missing illustration asset: ' + data.asset);
      root.classList.add('illustration');
      root.style.overflow = 'hidden';
      const image = el('img');
      image.src = asset.url;
      image.alt = data.alt;
      image.draggable = false;
      const [left, top, right, bottom] = asset.visibleBounds;
      const scale = Math.min(data.box[2]/(right-left), data.box[3]/(bottom-top));
      Object.assign(image.style, { position: 'absolute', width: asset.width*scale+'px', height: asset.height*scale+'px', left: ((data.box[2]-(right-left)*scale)/2-left*scale)+'px', top: ((data.box[3]-(bottom-top)*scale)/2-top*scale)+'px' });
      root.dataset.visibleMapping = JSON.stringify({ natural: [asset.width, asset.height], visibleBounds: asset.visibleBounds, scale });
      root.append(image);
      if (data.shadowBox) {
        const shadow = el('div', 'illustration-shadow');
        const [x,y,w,h] = data.shadowBox;
        Object.assign(shadow.style, { left: x+'px', top:y+'px', width:w+'px', height:h+'px', background:theme.illustrationShadow.fill, opacity:theme.illustrationShadow.opacity });
        stage.insertBefore(shadow, root);
      }
    },
    'temperature-scale'(root, data) {
      const v = svg(data.box[2], data.box[3]);
      const defs = vector('defs');
      const grad = vector('linearGradient', { id:'temperature-column', x1:0, y1:0, x2:1, y2:0 });
      grad.append(vector('stop', {offset:0,'stop-color':'#ADDAF8'}), vector('stop', {offset:1,'stop-color':'#70B4E5'}));
      defs.append(grad);v.append(defs);
      v.append(vector('rect', {x:76,y:0,width:70,height:359,rx:18,fill:'#F2F8FD',stroke:'#B2CCEB','stroke-width':1}));
      v.append(vector('rect', {x:105,y:20,width:14,height:302,rx:7,fill:'#FFFFFF',stroke:'#BDD5EE','stroke-width':1.5}));
      v.append(vector('rect', {x:105,y:data.columnTop,width:14,height:302-data.columnTop,fill:'url(#temperature-column)',opacity:.82}));
      v.append(vector('rect', {x:105,y:282,width:14,height:41,fill:'#F68EAD'}));
      for(let i=0;i<11;i++) {
        const y = 61+i*22;
        line(v, `M${i%2 ? 94 : 90} ${y} L132 ${y}`, '#C5D7EB', 2.5);
      }
      for(const marker of data.markers) {
        st(v, 54, marker.y+8, marker.text, {anchor:'end',accent:marker.accent,bold:marker.accent,size:23});
        line(v, `M69 ${marker.y} L118 ${marker.y}`, marker.accent ? theme.colors.pink : '#91AFCF', 3);
      }
      v.append(vector('circle', {cx:112,cy:data.bulbY,r:18,fill:'#F57FA5',stroke:'#8AB6DD','stroke-width':1.5}));
      root.append(v);
    },
    'temperature-plot'(root, data) {
      const v = svg(data.box[2], data.box[3]);
      st(v, 86, 24, data.title, {bold:true,size:theme.text.plotTitle});
      const originX=data.points[0][0];
      arrow(v, originX, 305, originX, 61, theme.colors.body, 2.5, 10);
      arrow(v, originX, 305, 479, 305, theme.colors.body, 2.5, 10);
      data.axisTitle.forEach((word,i) => st(v, 0, 92+i*24, word, {anchor:'middle',size:20}));
      for(const tick of data.ticks) {
        st(v, originX-22, tick.y+7, tick.text, {anchor:'end',size:23});
        line(v, `M${originX-10} ${tick.y} L${originX} ${tick.y}`, '#92AACA', 2.5);
        if(tick.text!=='20') line(v, `M${originX} ${tick.y} L470 ${tick.y}`, '#D6E0EA', 2.5);
      }
      const [a,b,c]=data.points;
      line(v, `M${a[0]} ${a[1]} L${b[0]} ${b[1]}`, theme.colors.blue, 4);
      line(v, `M${b[0]} ${b[1]} L${c[0]} ${c[1]}`, theme.colors.pink, 3.5);
      v.append(vector('rect', {x:288,y:101,width:147,height:82,rx:17,fill:'#FBE3ED'}));
      data.phase.forEach((word,i)=>st(v, 362, 135+i*28, word, {anchor:'middle',accent:i===0,size:22}));
      arrow(v, 361, 186, 361, 208, theme.colors.pink, 3.5, 11);
      st(v, 483, 339, data.xTitle, {anchor:'end',size:21});
      root.append(v);
    },
    'heat-arrows'(root, data) {
      const v = svg(data.box[2], data.box[3]);
      arrow(v, 93,35,40,4,theme.colors.pink,3.5,13);
      arrow(v, 91,81,25,91,theme.colors.pink,3.5,13);
      arrow(v, 97,124,41,153,theme.colors.pink,3.5,13);
      st(v, 0, 75, data.text, {size:23});
      root.append(v);
    },
    label(root, data) {
      root.classList.add('summary-label');
      Object.assign(root.style, {background:theme.label.fill,border:'1px solid '+theme.label.border,borderRadius:theme.label.radius+'px',fontSize:theme.text.label+'px'});
      rich(root, data.runs);
    }
  };
  for (const object of scene.objects) {
    if(!components[object.kind]) throw new Error('Unknown experimental component: '+object.kind);
    const node = el('div', 'visual-object');
    node.dataset.objectId = object.id;
    node.dataset.kind = object.kind;
    const [x,y,w,h] = object.box;
    Object.assign(node.style, {left:x+'px',top:y+'px',width:w+'px',height:h+'px'});
    stage.append(node);
    components[object.kind](node, object);
  }
  const ref = document.querySelector('#reference');
  ref.src = reference;
  const viewport = document.querySelector('.viewport');
  const canvas = document.querySelector('.canvas');
  const splitControl = document.querySelector('#split-control');
  let mode = 'html';
  function resize() {
    const scale = Math.min((window.innerWidth - 48)/scene.canvas.width, (window.innerHeight-145)/scene.canvas.height);
    canvas.style.transform = 'scale('+Math.max(.15,scale)+')';
    viewport.style.width = (scene.canvas.width*Math.max(.15,scale))+'px';
    viewport.style.height = (scene.canvas.height*Math.max(.15,scale))+'px';
  }
  window.addEventListener('resize', resize);resize();
  function selectMode(value) {
    mode=value;
    canvas.dataset.mode = mode;
    document.querySelectorAll('[data-mode-button]').forEach(button => button.setAttribute('aria-pressed', button.dataset.modeButton===mode));
    splitControl.hidden = mode!=='compare';
    document.querySelector('#reference-caption').hidden = mode==='html';
    document.querySelector('#html-caption').hidden = mode==='reference';
    document.querySelector('#reference-caption').textContent = mode==='compare' ? '左侧 · 生成参考' : '生成参考图';
    document.querySelector('#html-caption').textContent = mode==='compare' ? '右侧 · 实际 HTML' : '实际 HTML / CSS / SVG';
  }
  document.querySelectorAll('[data-mode-button]').forEach(button=>button.addEventListener('click',()=>selectMode(button.dataset.modeButton)));
  const slider = document.querySelector('#split');
  slider.addEventListener('input',()=>canvas.style.setProperty('--split',slider.value+'%'));
  document.querySelector('#hide-illustrations').addEventListener('change',event=>stage.classList.toggle('hide-illustrations',event.target.checked));
  selectMode('html');
  const raw = new URLSearchParams(location.search).get('view')==='raw';
  if(raw) {
    document.body.classList.add('raw');
    canvas.style.transform='none';
    viewport.style.width=scene.canvas.width+'px';viewport.style.height=scene.canvas.height+'px';
    window.removeEventListener('resize',resize);
  }
  Promise.all([document.fonts.ready,...Array.from(document.images).map(img=>img.decode())]).then(()=>{
    if(!document.fonts.check('24px "'+theme.font.family+'"')) throw new Error('Pinned host font unavailable');
    window.reconstructionReady=true;
  }).catch(error=>{document.querySelector('#status').textContent='资源加载失败：'+error.message;window.reconstructionError=error.message;});
})();
