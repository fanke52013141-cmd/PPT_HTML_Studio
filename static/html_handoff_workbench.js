// Human parameter amendments over server-persisted B/A/W; no renderer or source authority.
(function () {
  'use strict';
  if (window.HtmlHandoffWorkbench) return;
  const el = (tag, text = '', attrs = {}) => Object.assign(document.createElement(tag), {textContent:text,...attrs});
  function mount(host, options) {
    const panel=el('section'), heading=el('h4','人工微调工作草稿'), info=el('p'), fields=el('div'), shots=el('div'), checks=el('pre'), assistance=el('section'), groupPanel=el('section');
    const technical=el('details');technical.append(el('summary','高级：操作与诊断详情'),checks);
    panel.dataset.handoffWorkbench=''; panel.hidden=true;
    panel.append(heading,el('p','正式页保持原样；这里修改工作草稿。诊断图不代表通过，改动后需重新检查。'),info,groupPanel,assistance,fields,shots,technical);
    host.append(panel);
    let state=null, ref=null, disposed=false, renderGeneration=0, selected=[], view='work';
    const viewSelect=el('select'), canvasStatus=el('p');
    for(const [value,text] of [['work','人工工作草稿 · 可编辑'],['agent','Agent候选 · 只读'],['baseline','原页面 · 只读']])viewSelect.append(el('option',text,{value}));
    viewSelect.setAttribute('aria-label','候选画布视图');canvasStatus.dataset.canvasError='';panel.insertBefore(viewSelect,fields);panel.insertBefore(canvasStatus,fields);
    const names={offsetX:'水平偏移（向右为正）',offsetY:'垂直偏移（向下为正）',width:'宽度',height:'高度',fontSizePx:'字号（像素）',lineHeight:'行高',fontWeight:'字重',align:'对齐',variant:'呈现样式',text:'正文',heading:'标题',from:'左侧标签',to:'右侧标签',tag:'标签',note:'说明'};
    const label=k=>names[k]||k;
    function mergeOperations(operations) {
      const next=structuredClone(state.work.operations);
      for(const op of operations){const old=next.find(o=>o.targetId===op.targetId&&o.kind===op.kind&&o.part===op.part);if(old)Object.assign(old.values,op.values);else next.push(op);}
      return next;
    }
    const workCanvas=HtmlEditorCanvasBridge.createWorkView({host:panel,before:fields,
      onSelect:ids=>{selected=ids;const target=fields.querySelector('select');if(ids.length===1&&target){target.value=ids[0];target.onchange();}},
      onCommit:ops=>options.run(async()=>{try{await update(mergeOperations(ops));}finally{if(!disposed)await renderCanvas();}})});
    async function renderCanvas(){
      const token=++renderGeneration;
      const message=await workCanvas.render(state,view,selected);
      if(!disposed&&token===renderGeneration)canvasStatus.textContent=message;
    }
    viewSelect.onchange=()=>{view=viewSelect.value;renderCanvas().catch(e=>canvasStatus.textContent=e.message);};
    function requestBody(extra={}) { return {...ref,work_revision:state.work.work_revision,operations:state.work.operations,selected_group_ids:state.work.selected_group_ids??null,...extra}; }
    async function update(operations) {
      const response=await options.request('update',requestBody({operations}));
      state=response; draw();
    }
    function button(label, fn, disabled=false) {
      const b=el('button',label,{type:'button',disabled});
      b.onclick=()=>options.run(fn); return b;
    }
    function draw() {
      if(disposed)return; panel.hidden=false; fields.replaceChildren();shots.replaceChildren();
      const work=state.work, checked=work.check;
      groupPanel.replaceChildren();assistance.replaceChildren();
      if(state.editable){
        groupPanel.append(el('h4','按关联组采用 Agent 改进'),el('p','同组修改一起采用。未选组保留原页值；已有人工操作保留。组选项改变后需重新检查整页，原任务的全部验收条件仍保留。'));
        const groupInputs=[];
        for(const group of state.groups||[]){
          const row=el('label'),input=el('input','',{type:'checkbox',checked:work.selected_group_ids==null||work.selected_group_ids.includes(group.id)});
          input.dataset.workGroup=group.id;
          const titles=group.targets.map(id=>{const node=state.scene.nodes.find(n=>n.id===id);return node?.title||node?.runs?.map(r=>r.text).join('')||id;});
          row.append(input,document.createTextNode(`${titles.join('、')} · ${group.operations.length}项修改 · ${group.reasons.join('；')}`));
          const detail=el('details');detail.append(el('summary','查看这组修改'));
          for(const op of group.operations){
            const original=state.views?.baseline?.scene?.nodes.find(n=>n.id===op.targetId);
            const values=op.kind==='set_text_style'?original?.presentation?.typography?.[op.part]:original?.presentation;
            detail.append(el('p',`${op.targetId}${op.part?' · '+label(op.part):''}：${Object.entries(op.values).map(([key,value])=>`${label(key)} ${values?.[key]??'继承默认'} → ${value}`).join('，')}`));
          }
          groupPanel.append(row,detail);groupInputs.push(input);
        }
        groupPanel.append(button('采用所选组到工作草稿',async()=>{state=await options.request('update',requestBody({selected_group_ids:groupInputs.filter(i=>i.checked).map(i=>i.dataset.workGroup)}));view='work';viewSelect.value=view;draw();}));
        assistance.append(el('h4','中文问题提示与联动方案'));
        const advice=state.advice;
        if(!advice)assistance.append(el('p','先检查工作草稿，读取当前测量与边界，再给出可预览方案。'));
        else{
          for(const item of advice.messages||[])assistance.append(el('p',item.message));
          for(const text of advice.blocked||[])assistance.append(el('p',text));
          if(!advice.proposals.length)assistance.append(el('p','当前没有可自动联动的方案；可继续人工编辑并检查。'));
          for(const proposal of advice.proposals||[])assistance.append(button('预览联动修复方案',async()=>{
            state=await options.request('propose',requestBody({proposal_id:proposal.id}));view='proposal';
            if(![...viewSelect.options].some(o=>o.value==='proposal'))viewSelect.append(el('option','联动方案预览 · 尚未应用',{value:'proposal'}));
            viewSelect.value=view;draw();
          }));
        }
        const proposed=state.proposal_preview;
        if(proposed){
          assistance.append(el('p',proposed.passed?'联动方案检查通过；工作草稿尚未改变，请核对预览后确认。':'联动预览未通过，不能确认应用；原草稿保持。'));
          for(const op of proposed.changes||[])assistance.append(el('p',`${op.targetId}：${Object.entries(op.values).map(([key,value])=>`${label(key)} → ${value}`).join('，')}`));
          if(!proposed.passed)assistance.append(el('pre',JSON.stringify(proposed.check.review?.validation||proposed.check.review?.issues||proposed.check.acceptance,null,2)));
          assistance.append(button('确认应用此联动方案',async()=>{state=await options.request('update',requestBody({proposal_id:proposed.id}));view='work';viewSelect.value=view;draw();},!proposed.passed));
        }
      }
      if(!state.views?.[view]&&view==='proposal'){view='work';viewSelect.value=view;}

      renderCanvas().catch(e=>{if(!disposed)canvasStatus.textContent=e.message;});
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
      for(const id of state.scope){const n=state.scene.nodes.find(n=>n.id===id);const title=n?.title||n?.heading||n?.text||n?.label||n?.runs?.map(r=>r.text).join('')||({headline:'页面标题',relationship:'关系图',text:'正文',figure:'插图',annotation:'标注'}[n?.type])||id;target.append(el('option',typeof title==='string'?title.slice(0,45):id,{value:id}));}if(selected.length===1&&state.scope.includes(selected[0]))target.value=selected[0];
      fields.append(target,kind,inputs);
      const variants=state.operation_schema.oneOf||[];
      function choices() {
        kind.replaceChildren();
        variants.forEach((s,index)=>{
          const p=s.properties;
          if(p.targetId.const!==target.value||!['set_presentation','set_text_style','set_variant'].includes(p.kind.const))return;
          const operationLabel=p.kind.const==='set_presentation'?'位置与尺寸':p.kind.const==='set_text_style'?`文字 · ${label(p.part.const)}`:`呈现 · ${p.values.properties.variant.const}`;
          kind.append(el('option',operationLabel,{value:String(index)}));
        }); controls();
      }
      function controls() {
        inputs.replaceChildren(); const spec=variants[Number(kind.value)];if(!spec)return;
        const node=state.scene.nodes.find(n=>n.id===target.value),p=spec.properties;
        for(const [key,s] of Object.entries(p.values.properties)) {
          const fieldLabel=el('label',label(key)), input=s.enum||s.const!==undefined?el('select'):el('input','',{type:'number',step:'any'});
          input.dataset.workField=key;
          if(s.enum) {input.append(el('option','保持当前',{value:''}));for(const v of s.enum)input.append(el('option',String(v),{value:String(v)}));}
          else if(s.const!==undefined)input.append(el('option',s.const,{value:s.const}));
          else {if(s.minimum!==undefined)input.min=s.minimum;if(s.maximum!==undefined)input.max=s.maximum;}
          const current=p.kind.const==='set_text_style'?node.presentation?.typography?.[p.part.const]?.[key]:node.presentation?.[key];
          if(input.tagName==='INPUT')input.placeholder=`当前：${current??'继承默认'}；留空保持`;
          fieldLabel.append(input);inputs.append(fieldLabel);
        }
      }
      target.onchange=choices;kind.onchange=controls;choices();
      fields.append(button('定位此对象',()=>{selected=[target.value];workCanvas.select(selected);options.select?.(target.value);}),button('应用到工作草稿',async()=>{
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
      fields.append(button('撤销人工修改',async()=>{state=await options.request('update',requestBody({history_action:'undo'}));draw();},!work.undo?.length),
        button('重做人工修改',async()=>{state=await options.request('update',requestBody({history_action:'redo'}));draw();},!work.redo?.length),
        button('恢复Agent候选',async()=>{state=await options.request('update',requestBody({operations:[],selected_group_ids:null}));view='work';viewSelect.value=view;draw();},!work.operations.length&&work.selected_group_ids==null),
        button('检查工作草稿',async()=>{state=await options.request('check',requestBody());draw();}),
        button('保存工作草稿到页面',async()=>{
          const response=await options.request('save',requestBody());state={...state,work:response.work,saved:true,editable:false};draw();
          await options.onSaved();
        },!checked?.passed));
    }
    return {async open(reference,restore=false){ref=reference;state=await options.request(restore?'read':'open',ref);if(!disposed)draw();},
      destroy(){disposed=true;renderGeneration++;workCanvas.destroy();panel.remove();state=null;}};
  }
  window.HtmlHandoffWorkbench={mount};
})();
