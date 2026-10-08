// N02 edits author data; the iframe runs the unchanged production shared player.
(function () {
  'use strict';
  if (window.HtmlSceneEditor) return;
  const clone = value => structuredClone(value);
  const drafts = new Map();
  let active = null, generation = 0;
  const el = (tag, text, attrs = {}) => Object.assign(document.createElement(tag), {textContent: text, ...attrs});
  function notify(s, text) { s.status.textContent = text; }
  function snapshot(s) { return clone({scene: s.doc.scene, binding: s.doc.binding, anchor_overrides: s.doc.anchor_overrides}); }
  function remember(s) { drafts.set(s.key, {doc: clone(s.doc), dirty: s.dirty, selected: s.selected}); }
  function change(s, fn) {
    s.undo.push(snapshot(s)); if (s.undo.length > 50) s.undo.shift(); s.redo = [];
    fn(); s.dirty = true; remember(s); notify(s, '有未保存修改；预览校验后保存。');
  }
  function setPath(object, parts, value) {
    let cursor = object; for (const key of parts.slice(0, -1)) cursor = cursor[key];
    cursor[parts.at(-1)] = value;
  }
  function schema(s, spec) {
    return spec.$ref ? schema(s, s.doc.capabilities.schema.$defs[spec.$ref.split('/').at(-1)]) : spec;
  }
  function control(s, parent, spec, value, path, update) {
    spec = schema(s, spec);
    if (spec.type === 'object' || spec.properties) {
      const box = el('fieldset', ''), title = el('legend', path.at(-1)); box.append(title); parent.append(box);
      for (const [key, child] of Object.entries(spec.properties || {})) {
        if (child.const !== undefined || ['id','slot','type'].includes(key) && path.length === 0) continue;
        if (value[key] !== undefined) control(s, box, child, value[key], [...path, key], update);
        else {
          const add = el('button', `添加 ${key}`, {type:'button'}); box.append(add);
          add.onclick = () => { change(s, () => update([...path,key], defaults(s,child))); properties(s); };
        }
      }
      return;
    }
    if (spec.type === 'array') {
      const box = el('fieldset', ''); box.append(el('legend',path.at(-1))); parent.append(box);
      value.forEach((item, index) => {
        control(s, box, spec.items, item, [...path,index], update);
        if (value.length > (spec.minItems || 0)) {
          const remove = el('button',`删除第 ${index+1} 段`,{type:'button'}); box.append(remove);
          remove.onclick = () => { change(s,()=>update(path,value.filter((_,i)=>i!==index))); properties(s); };
        }
      });
      if (value.length < (spec.maxItems || 16)) {
        const add = el('button','添加文本段',{type:'button'}); box.append(add);
        add.onclick=()=>{change(s,()=>update(path,[...value,defaults(s,spec.items)]));properties(s);};
      }
      return;
    }
    const label = el('label', path.join('.'));
    let input;
    if (spec.enum) {
      input = el('select',''); for (const option of spec.enum) input.append(el('option',option,{value:option}));
      input.value = value;
    } else if (spec.type === 'boolean') {
      input=el('input','',{type:'checkbox',checked:!!value});
    } else {
      input=el(spec.type==='string' && (spec.maxLength || 0)>60 ? 'textarea':'input','');
      if (input.tagName==='INPUT') input.type=spec.type==='number' || spec.type==='integer' ? 'number':'text';
      input.value=value;
      if (spec.minimum!==undefined) input.min=spec.minimum;
      if (spec.maximum!==undefined) input.max=spec.maximum;
      if (spec.maxLength) input.maxLength=spec.maxLength;
      if (input.type==='number') input.step='any';
    }
    input.dataset.field=path.join('.'); label.append(input); parent.append(label);
    input.onchange=()=>change(s,()=>update(path,input.type==='checkbox' ? input.checked : input.type==='number' ? Number(input.value):input.value));
  }
  function defaults(s, spec) {
    spec=schema(s,spec);
    if (spec.const!==undefined) return spec.const;
    if (spec.enum) return spec.enum[0];
    if (spec.type==='object') return Object.fromEntries((spec.required||[]).map(k=>[k,defaults(s,spec.properties[k])]));
    if (spec.type==='array') return Array.from({length:spec.minItems||1},()=>defaults(s,spec.items));
    if (spec.type==='boolean') return false;
    if (spec.type==='number'||spec.type==='integer') return spec.minimum || 0;
    return '新内容';
  }
  function allAssets(s) {
    const base=s.frame.contentWindow.VisualData?.catalog.assets || [];
    return [...base.filter(a=>!s.doc.resources.assets.some(b=>b.id===a.id)),...s.doc.resources.assets];
  }
  function selection(s,id) { s.selected=id; properties(s); mark(s); remember(s); }
  function mark(s) {
    const doc=s.frame.contentDocument;
    doc?.querySelectorAll('[data-object-id]').forEach(node=>{
      node.style.outline=node.dataset.objectId===s.selected ? '2px solid #ee5d36':'';
    });
    s.list.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.object===s.selected)));
  }
  function nodeList(s) {
    s.list.replaceChildren(...s.doc.scene.nodes.map(n=>{
      const b=el('button',`${n.id} · ${n.type}`,{type:'button'}); b.dataset.object=n.id;
      b.onclick=()=>selection(s,n.id);return b;
    }));
  }
  function properties(s) {
    const node=s.doc.scene.nodes.find(n=>n.id===s.selected); s.props.replaceChildren(); if (!node) return;
    s.props.append(el('h4',`${node.id} · ${node.type}`));
    const spec=s.doc.capabilities.schema.$defs.node.oneOf.find(x=>x.properties.type.const===node.type);
    const propertiesSpec=clone(spec); delete propertiesSpec.properties.assetRef;
    control(s,s.props,propertiesSpec,node,[],(path,v)=>setPath(node,path,v));
    if (node.type==='image') imageFields(s,node);
    actions(s,node);
    const info=el('button','测量当前目标',{type:'button'});s.props.append(info);
    info.onclick=()=>{
      const report=s.frame.contentWindow.visualPlayer.seek(s.frame.contentWindow.visualPlayer.timeMs);
      notify(s,JSON.stringify(report.geometry[node.id] || {code:'TARGET_NODE_GONE'}));
    };
    const range=el('button','读取画面文字选区',{type:'button'});s.props.append(range);
    range.onclick=()=>{
      try { notify(s,JSON.stringify(measureTextSelection(s.frame.contentWindow))); }
      catch(e) {notify(s,e.message);}
    };
  }
  function imageFields(s,node) {
    const label=el('label','替换独立资源'), select=el('select','');select.dataset.field='assetRef';
    for(const a of allAssets(s)) select.append(el('option',`${a.id}@${a.version}`,{value:a.id}));
    select.value=node.assetRef.id;label.append(select);s.props.append(label);
    select.onchange=()=>{
      change(s,()=>{
        const asset=allAssets(s).find(a=>a.id===select.value);
        node.assetRef={id:asset.id,version:asset.version};node.anchorId=asset.anchors[0]?.id || '';
        delete s.doc.anchor_overrides[node.id];
        for(const n of s.doc.scene.nodes.filter(n=>n.type==='annotation'&&n.targetId===node.id)) n.anchorId=node.anchorId;
      }); properties(s);notify(s,'已替换资源并重置为新资源登记锚点；请检查所有关联圈注。');
    };
    const asset=allAssets(s).find(a=>a.id===node.assetRef.id); if(!asset)return;
    const points=s.doc.anchor_overrides[node.id] || asset.anchors;
    const box=el('fieldset','');box.append(el('legend','原图语义锚点（归一化坐标）'));s.props.append(box);
    points.forEach((a,index)=>{
      const row=el('div','');row.className='hse-anchor';box.append(row);
      for(const key of ['id','x','y']) {
        const label=el('label',key),input=el('input','',{type:key==='id'?'text':'number',value:a[key]});
        input.dataset.anchor=`${index}.${key}`;if(key!=='id'){input.min=0;input.max=0.999999;input.step=0.001;}
        label.append(input);row.append(label);
        input.onchange=()=>change(s,()=>{
          const updated=clone(points),old=updated[index].id;updated[index][key]=key==='id'?input.value:Number(input.value);
          s.doc.anchor_overrides[node.id]=updated;
          if(key==='id'){
            if(node.anchorId===old)node.anchorId=input.value;
            s.doc.scene.nodes.filter(n=>n.type==='annotation'&&n.targetId===node.id&&n.anchorId===old).forEach(n=>n.anchorId=input.value);
          }
          properties(s);
        });
      }
      const pick=el('button','在图中定位',{type:'button'});row.append(pick);
      pick.onclick=()=>{s.pick={nodeId:node.id,index};notify(s,'请点击预览主体内部，按实际 contain 映射记录锚点。');};
    });
    const add=el('button','新增语义锚点',{type:'button'});box.append(add);
    add.onclick=()=>{change(s,()=>{let i=1;while(points.some(a=>a.id===`anchor-${i}`))i++;s.doc.anchor_overrides[node.id]=[...clone(points),{id:`anchor-${i}`,x:0.5,y:0.5}];});properties(s);};
    box.append(el('p','锚点改动保存为本页独立资源版本，原资源继续保留。'));
  }
  function actions(s,node) {
    const box=el('fieldset','');box.append(el('legend','动作与讲稿语块'));s.props.append(box);
    const list=s.doc.scene.motion.filter(a=>a.targetId===node.id);
    list.forEach(a=>{
      const section=el('fieldset','');section.append(el('legend',a.type));box.append(section);
      const spec=s.doc.capabilities.schema.$defs.motion.oneOf.find(x=>x.properties.type.const===a.type);
      const props=clone(spec);delete props.properties.targetId;
      control(s,section,props,a,[a.type],(path,v)=>setPath(a,path.slice(1),v));
      const key=`${node.id}:${a.type}`,link=s.doc.binding?.actions[key];
      const label=el('label','绑定句子'),select=el('select','');select.dataset.beat=a.type;
      select.append(el('option','作者时间（未绑定）',{value:''}));
      const beats=s.doc.beats || [];
      for(const b of beats) {const id=b.beat_id||b.id;select.append(el('option',`${id} · ${b.text||b.narration||''}`,{value:id}));}
      if(link && !beats.some(b=>(b.beat_id||b.id)===link.beatId))select.append(el('option',`已删除：${link.beatId}`,{value:link.beatId}));
      select.value=link?.beatId||'';label.append(select);section.append(label);
      select.onchange=()=>{change(s,()=>{
        s.doc.binding ||= {format:'hps.html.motion_binding',version:'0.1.0',mode:'beat_ids',actions:{}};
        if(select.value)s.doc.binding.actions[key]={beatId:select.value,edge:'start',offsetMs:0};
        else delete s.doc.binding.actions[key];
      });properties(s);};
      if(link)control(s,section,{type:'object',properties:{edge:{enum:['start','end']},offsetMs:{type:'integer',minimum:-120000,maximum:120000}}},link,['binding',a.type],(path,v)=>setPath(link,path.slice(2),v));
      if(a.type!=='enter'){
        const remove=el('button','删除此动作',{type:'button'});section.append(remove);
        remove.onclick=()=>{change(s,()=>{s.doc.scene.motion=s.doc.scene.motion.filter(v=>v!==a);if(s.doc.binding)delete s.doc.binding.actions[key];});properties(s);};
      }
    });
    for(const type of s.doc.capabilities.actions.filter(type=>!list.some(a=>a.type===type))){
      const add=el('button',`添加 ${type}`,{type:'button'});box.append(add);
      add.onclick=()=>{change(s,()=>s.doc.scene.motion.push({targetId:node.id,type,startMs:Math.max(...list.map(a=>a.startMs+a.durationMs)),durationMs:500}));properties(s);};
    }
  }
  function measureTextSelection(win) {
    const selection=win.getSelection();if(!selection?.rangeCount||selection.isCollapsed)throw Error('请先在画面选中文字。');
    const range=selection.getRangeAt(0),start=range.startContainer.parentElement.closest('[data-object-id]'),end=range.endContainer.parentElement.closest('[data-object-id]');
    if(!start||start!==end)throw Error('选区必须位于同一对象。');
    const prefix=range.cloneRange();prefix.selectNodeContents(start);prefix.setEnd(range.startContainer,range.startOffset);
    const scale=win.document.getElementById('viewport').clientWidth/1600;
    const origin=win.document.getElementById('viewport').getBoundingClientRect();
    return {kind:'text_range',nodeId:start.dataset.objectId,start:[...prefix.toString()].length,end:[...prefix.toString()].length+[...range.toString()].length,text:range.toString(),rects:[...range.getClientRects()].map(r=>({x:(r.x-origin.x)/scale,y:(r.y-origin.y)/scale,width:r.width/scale,height:r.height/scale})),output_supported:false};
  }
  async function preview(s) {
    const token=++s.previewGeneration;
    const resolved=await API.post(`${s.url}/preview`,{...snapshot(s),expected_revision:s.doc.revision});
    if(active!==s||token!==s.previewGeneration)return false;
    const ok=await s.frame.contentWindow.visualPlayer.apply(resolved.scene,resolved.resources);
    if(active!==s||token!==s.previewGeneration)return false;
    if(!ok)throw Error(s.frame.contentDocument.getElementById('status').textContent);
    s.seek.max=resolved.scene.durationMs;s.seek.value=Math.min(Number(s.seek.value),resolved.scene.durationMs);
    s.frame.contentWindow.visualPlayer.seek(Number(s.seek.value));mark(s);
    s.previewSnapshot=JSON.stringify(snapshot(s));notify(s,`修订 ${s.doc.revision}${s.dirty?' · 本地草稿':''} · ${resolved.audio_status}`);return true;
  }
  async function save(s) {
    s.root.inert=true;
    s.save.disabled=true;
    try {
      if(!await preview(s))return;
      const payload={...snapshot(s),expected_revision:s.doc.revision};
      const result=await API.put(s.url,payload);
      if(active!==s)return;
      s.doc=await API.get(s.url);s.dirty=false;s.undo=[];s.redo=[];remember(s);nodeList(s);properties(s);await preview(s);
      notify(s,result.changed?'已保存；本页需要重新审阅，音频保留。':'内容未变化；批准与音频保留。');
    }catch(e){
      remember(s);
      if(e.status===409){s.conflict.hidden=false;notify(s,'修订冲突：本地草稿已保留。先比较服务器版本，再决定是否重载。');}
      else notify(s,e.message);
    }finally{s.save.disabled=false;s.root.inert=false;}
  }
  async function open(host,projectId,slideId) {
    if(active)remember(active);
    const token=++generation,key=`${projectId}:${slideId}`,url=`/api/projects/${encodeURIComponent(projectId)}/html-visual/${encodeURIComponent(slideId)}/editor`;
    const existing=drafts.get(key);
    const doc=existing?.dirty ? clone(existing.doc) : await API.get(url);
    if(token!==generation)return;
    const root=el('section','');root.className='html-scene-editor';host.replaceChildren(root);
    const bar=el('div','');bar.className='hse-toolbar';root.append(bar);
    const status=el('p','',{role:'status'});status.dataset.editorStatus='';root.append(status);
    const grid=el('div','');grid.className='hse-grid';root.append(grid);
    const list=el('nav','',{'aria-label':'场景对象'}),middle=el('div',''),props=el('aside','');grid.append(list,middle,props);
    const frame=el('iframe','',{title:'HTML 共享播放器预览'});frame.className='hse-preview';middle.append(frame);
    const seek=el('input','',{type:'range',min:0,max:doc.scene.durationMs,value:doc.scene.durationMs});seek.setAttribute('aria-label','预览毫秒');middle.append(seek);
    const time=el('input','',{type:'number',min:0,value:doc.scene.durationMs});time.setAttribute('aria-label','跳转毫秒');middle.append(time);
    const conflict=el('div','');conflict.hidden=true;root.append(conflict);
    const s={root,status,list,props,frame,seek,time,conflict,key,url,doc,dirty:existing?.dirty||false,selected:existing?.selected||doc.scene.nodes[0].id,undo:[],redo:[],previewGeneration:0};active=s;
    const button=(text,action)=>{const b=el('button',text,{type:'button'});bar.append(b);b.onclick=async()=>{try{await action();}catch(e){notify(s,e.message);}};return b;};
    button('校验预览',()=>preview(s));s.save=button('保存修改',()=>save(s));
    button('撤销',()=>history(s,'undo','redo'));button('重做',()=>history(s,'redo','undo'));
    button('播放 / 暂停',()=>{const p=frame.contentWindow.visualPlayer;p.playing?p.pause():p.play();});
    button('重播',()=>{const p=frame.contentWindow.visualPlayer;p.pause();p.seek(0);p.play();});
    button('上一帧',()=>seekTo(s,(frame.contentWindow.visualPlayer.timeMs||0)-1000/30));
    button('下一帧',()=>seekTo(s,(frame.contentWindow.visualPlayer.timeMs||0)+1000/30));
    const compare=el('button','比较服务器版本',{type:'button'}),reload=el('button','舍弃本地草稿并重载',{type:'button'}),comparison=el('pre','');conflict.append(compare,reload,comparison);
    compare.onclick=async()=>{try{const latest=await API.get(url);comparison.textContent=JSON.stringify({server_revision:latest.revision,server_scene:latest.scene,server_binding:latest.binding,local:snapshot(s)},null,2);}catch(e){notify(s,e.message);}};
    reload.onclick=()=>{drafts.delete(key);s.dirty=false;open(host,projectId,slideId).catch(e=>notify(s,e.message));};
    seek.oninput=()=>seekTo(s,Number(seek.value));time.onchange=()=>seekTo(s,Number(time.value));
    frame.srcdoc=`<!doctype html><meta charset="utf-8"><style>body{margin:0}#viewport{width:100%}.runtime-controls{display:none}</style><div id="viewport"></div><div class="runtime-controls"><select id="scene"></select><select id="theme"></select><textarea id="definition"></textarea><button id="apply"></button><button id="play"></button><button id="end"></button><input id="seek"><span id="time"></span><input id="font" value="32"><span id="font-value"></span><input type="checkbox" id="reduced"><p id="status"></p></div><script src="/api/html-scene-editor/runtime/data.js"></script><script src="/api/html-scene-editor/runtime/player.js"></script>`;
    await new Promise((resolve,reject)=>{frame.onload=resolve;frame.onerror=()=>reject(Error('播放器加载失败'));});
    if(active!==s)return;
    if(!frame.contentWindow.visualPlayer)throw Error('共享播放器未加载');
    frame.contentDocument.addEventListener('pointerup',event=>{
      if(s.pick){
        const node=s.doc.scene.nodes.find(n=>n.id===s.pick.nodeId),asset=allAssets(s).find(a=>a.id===node.assetRef.id);
        const img=[...frame.contentDocument.querySelectorAll('[data-object-id]')].find(n=>n.dataset.objectId===node.id)?.querySelector('img');
        const rect=img?.getBoundingClientRect();if(!rect)return;
        const x=(event.clientX-rect.x)/rect.width,y=(event.clientY-rect.y)/rect.height;
        if(x<0||y<0||x>=1||y>=1){notify(s,'锚点必须位于主体原图内部。');return;}
        change(s,()=>{const points=clone(s.doc.anchor_overrides[node.id]||asset.anchors);points[s.pick.index]={...points[s.pick.index],x,y};s.doc.anchor_overrides[node.id]=points;});s.pick=null;properties(s);return;
      }
      const target=event.target.closest('[data-object-id]');if(target)selection(s,target.dataset.objectId);
    });
    nodeList(s);properties(s);await preview(s);
  }
  function seekTo(s,ms){const p=s.frame.contentWindow.visualPlayer;p.pause();const t=Math.max(0,Math.min(p.scene.durationMs,ms));p.seek(t);s.seek.value=t;s.time.value=Math.round(t);mark(s);}
  function history(s,source,target){if(!s[source].length)return;s[target].push(snapshot(s));Object.assign(s.doc,s[source].pop());s.dirty=true;remember(s);nodeList(s);properties(s);notify(s,'会话编辑已恢复，请校验预览后保存。');}
  function close(){if(active){remember(active);active.frame.contentWindow.visualPlayer?.pause();}active=null;generation++;}
  window.addEventListener('beforeunload',e=>{if(active?.dirty){e.preventDefault();e.returnValue='';}});
  window.HtmlSceneEditor={open,close,measureTextSelection};
})();
