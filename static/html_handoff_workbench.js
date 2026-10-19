// Human parameter amendments over server-persisted B/A/W; no renderer or source authority.
(function () {
  'use strict';
  if (window.HtmlHandoffWorkbench) return;
  const el = (tag, text = '', attrs = {}) => Object.assign(document.createElement(tag), {textContent:text,...attrs});
  function mount(host, options) {
    const panel=el('section'), heading=el('h4','人工微调工作草稿'), info=el('p'), fields=el('div'), shots=el('div'), checks=el('pre');
    panel.dataset.handoffWorkbench=''; panel.hidden=true;
    panel.append(heading,el('p','正式页保持原样；这里修改工作草稿。诊断图不代表通过，改动后需重新检查。'),info,fields,shots,checks);
    host.append(panel);
    let state=null, ref=null, undo=[], redo=[];
    function requestBody(extra={}) { return {...ref,work_revision:state.work.work_revision,operations:state.work.operations,...extra}; }
    async function update(operations, history=true) {
      const previous=structuredClone(state.work.operations);
      const response=await options.request('update',requestBody({operations}));
      if(history){undo.push(previous);redo=[];}
      state=response; draw();
    }
    function button(label, fn, disabled=false) {
      const b=el('button',label,{type:'button',disabled});
      b.onclick=()=>options.run(fn); return b;
    }
    function draw() {
      panel.hidden=false; fields.replaceChildren();shots.replaceChildren();
      const work=state.work, checked=work.check;
      info.textContent=state.saved?'此工作草稿已保存；重新打开当前页面继续编辑。':state.stale?`历史草稿不可保存：${state.message}`:
        `工作版本 ${work.work_revision} · ${work.operations.length} 项人工操作 · ${checked?.passed?'原系统检查通过，尚未保存':'尚未通过当前完整检查'}`;
      checks.textContent=JSON.stringify({operations:work.operations,acceptance:checked?.acceptance,
        issues:checked?.review?.issues,validation:checked?.review?.validation,diagnostic:checked?.diagnostic},null,2);
      for(const shot of state.pictures||[]) {
        if(!shot.image?.startsWith('data:image/png;base64,'))continue;
        const figure=el('figure'),img=el('img','',{src:shot.image,alt:checked?.passed?'工作草稿实际画面':'未通过的诊断画面'});
        figure.append(el('figcaption',`${checked?.passed?'实际画面':'诊断图 · 未通过'} · ${shot.timeMs}ms`),img);shots.append(figure);
      }
      if(!state.editable)return;
      const target=el('select'),kind=el('select'),inputs=el('div');
      target.setAttribute('aria-label','人工修改对象');kind.setAttribute('aria-label','人工修改操作');
      for(const id of state.scope)target.append(el('option',id,{value:id}));
      fields.append(target,kind,inputs);
      const variants=state.operation_schema.oneOf||[];
      function choices() {
        kind.replaceChildren();
        variants.forEach((s,index)=>{
          const p=s.properties;
          if(p.targetId.const!==target.value||!['set_presentation','set_text_style','set_variant'].includes(p.kind.const))return;
          const label=p.kind.const==='set_presentation'?'位置与尺寸':p.kind.const==='set_text_style'?`文字 · ${p.part.const}`:`呈现 · ${p.values.properties.variant.const}`;
          kind.append(el('option',label,{value:String(index)}));
        }); controls();
      }
      function controls() {
        inputs.replaceChildren(); const spec=variants[Number(kind.value)];if(!spec)return;
        const node=state.scene.nodes.find(n=>n.id===target.value),p=spec.properties;
        for(const [key,s] of Object.entries(p.values.properties)) {
          const label=el('label',key), input=s.enum||s.const!==undefined?el('select'):el('input','',{type:'number',step:'any'});
          input.dataset.workField=key;
          if(s.enum) {input.append(el('option','保持当前',{value:''}));for(const v of s.enum)input.append(el('option',String(v),{value:String(v)}));}
          else if(s.const!==undefined)input.append(el('option',s.const,{value:s.const}));
          else {if(s.minimum!==undefined)input.min=s.minimum;if(s.maximum!==undefined)input.max=s.maximum;}
          const current=p.kind.const==='set_text_style'?node.presentation?.typography?.[p.part.const]?.[key]:node.presentation?.[key];
          if(input.tagName==='INPUT')input.placeholder=`当前：${current??'继承默认'}；留空保持`;
          label.append(input);inputs.append(label);
        }
      }
      target.onchange=choices;kind.onchange=controls;choices();
      fields.append(button('定位此对象',()=>options.select?.(target.value)),button('应用到工作草稿',async()=>{
        const spec=variants[Number(kind.value)],p=spec.properties,values={};
        for(const input of inputs.querySelectorAll('[data-work-field]')) {
          if(input.value==='')continue;
          const schema=p.values.properties[input.dataset.workField];
          values[input.dataset.workField]=schema.type==='number'||schema.type==='integer'?Number(input.value):input.value;
        }
        if(!Object.keys(values).length)throw Error('请填写至少一个需要修改的值。');
        const op={targetId:target.value,kind:p.kind.const,values};if(p.part)op.part=p.part.const;
        const same=o=>o.targetId===op.targetId&&o.kind===op.kind&&o.part===op.part;
        const existing=work.operations.find(same),ops=work.operations.filter(o=>!same(o));
        ops.push({...op,values:{...existing?.values,...values}});await update(ops);
      }));
      fields.append(button('撤销人工修改',async()=>{const next=undo.at(-1),old=structuredClone(work.operations);await update(next,false);undo.pop();redo.push(old);draw();},!undo.length),
        button('重做人工修改',async()=>{const next=redo.at(-1),old=structuredClone(work.operations);await update(next,false);redo.pop();undo.push(old);draw();},!redo.length),
        button('恢复Agent候选',()=>update([]),!work.operations.length),
        button('检查工作草稿',async()=>{state=await options.request('check',requestBody());draw();}),
        button('保存工作草稿到页面',async()=>{
          const response=await options.request('save',requestBody());state={...state,work:response.work,saved:true,editable:false};draw();
          await options.onSaved();
        },!checked?.passed));
    }
    return {async open(reference,restore=false){ref=reference;state=await options.request(restore?'read':'open',ref);undo=[];redo=[];draw();},
      destroy(){panel.remove();state=null;}};
  }
  window.HtmlHandoffWorkbench={mount};
})();
