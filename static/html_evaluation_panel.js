// Dataset labels and experiment control only. Original services own all writes.
(function(){
  'use strict';
  if(window.HtmlEvaluationPanel)return;
  const states=new WeakMap();
  const el=(tag,text='')=>Object.assign(document.createElement(tag),{textContent:text});
  function field(label,control){const root=el('label',label+' ');root.append(control);return root;}
  function select(values,label){const s=el('select');s.setAttribute('aria-label',label);for(const [value,text]of values){const o=el('option',text);o.value=value;s.append(o);}return s;}
  function clear(section){const s=states.get(section);if(!s)return;s.serial++;s.nonce=null;s.frame.removeAttribute('src');clearTimeout(s.timer);window.removeEventListener('message',s.message);s.box.remove();states.delete(section);}
  function mount(section,context){
    const key=context.project.id+':'+context.slideId;if(states.get(section)?.key===key)return;
    clear(section);
    const box=el('details'),summary=el('summary','评测标注与配对实验');box.dataset.designOnly='';box.append(summary);
    const reload=el('button','读取评测数据集'),datasets=select([],'评测数据集'),cases=select([],'标注样本'),open=el('button','打开原图标注');
    const status=el('p','读取本项目数据集后选择样本。标注和复核不会批准生产页面。');status.setAttribute('role','status');
    const annotator=el('input');annotator.maxLength=100;annotator.setAttribute('aria-label','标注者');
    const reviewer=el('input');reviewer.maxLength=100;reviewer.setAttribute('aria-label','独立复核者');
    const note=el('input');note.maxLength=1000;note.setAttribute('aria-label','复核依据');
    const save=el('button','保存标注草稿'),accept=el('button','复核通过并封存'),reject=el('button','要求修改标注');
    save.disabled=true;accept.disabled=true;reject.disabled=true;
    const history=el('ul'),frame=el('iframe');frame.title='原图标注工作台';frame.setAttribute('sandbox','allow-scripts allow-downloads');frame.hidden=true;frame.style.cssText='width:100%;height:850px;border:1px solid #ddd';
    const create=el('details');create.append(el('summary','从本项目已保存页面创建数据集'));
    const id=el('input');id.placeholder='dataset-name';id.setAttribute('aria-label','新数据集名称');const pages=el('div'),createButton=el('button','创建标注数据集');create.append(field('数据集名称',id),pages,createButton);
    const experiments=el('details');experiments.append(el('summary','运行固定样本配对实验'));
    const before=select([['0.5.0','定位协议 0.5.0'],['0.5.1','定位协议 0.5.1']],'优化前协议');
    const after=select([['0.5.1','定位协议 0.5.1'],['0.5.0','定位协议 0.5.0']],'优化后协议');
    const beforeRole=select([['text','项目视觉文字模型'],['planning','项目规划模型（需支持图像）']],'优化前模型');
    const afterRole=select([['text','项目视觉文字模型'],['planning','项目规划模型（需支持图像）']],'优化后模型');
    const repetitions=el('input');repetitions.type='number';repetitions.min=1;repetitions.max=5;repetitions.value='1';
    const start=el('button','开始配对实验（调用项目模型）'),cancel=el('button','停止配对实验');cancel.disabled=true;
    const results=el('pre');results.style.whiteSpace='pre-wrap';
    experiments.append(field('优化前',before),beforeRole,field('优化后',after),afterRole,field('重复次数',repetitions),
      el('p','仅对所有样本已独立复核的数据集执行。冻结两组配置并交替顺序；未知结果不自动重发，费用未知保持空值。'),start,cancel,results);
    box.append(status,reload,field('数据集',datasets),field('样本',cases),open,field('标注者',annotator),save,
      field('独立复核者',reviewer),field('复核依据（至少8字）',note),accept,reject,history,frame,create,experiments);
    for(const b of box.querySelectorAll('button'))b.type='button';
    section.append(box);
    const s={key,box,frame,serial:0,nonce:null,base:`/api/projects/${encodeURIComponent(context.project.id)}/html-evaluation`,project:context.project.id};states.set(section,s);
    const valid=()=>states.get(section)===s&&!section.hidden;
    async function command(body){return (await API.post(s.base+'/action',{command:body})).evaluation;}
    function invalidate(){s.serial++;s.nonce=null;s.annotation=null;s.mapping=null;save.disabled=true;accept.disabled=true;reject.disabled=true;frame.hidden=true;frame.removeAttribute('src');}
    function renderTask(task){
      s.task=task;cancel.disabled=!['queued','running'].includes(task.status);
      const comparison=task.result?.comparison||task.progress?.comparison;
      results.textContent=JSON.stringify({任务:task.id,状态:task.status,进度:task.progress?.experiment,错误:task.error,报告:comparison?.summary},null,2);
      clearTimeout(s.timer);
      if(!cancel.disabled)s.timer=setTimeout(async()=>{if(!valid())return;try{const data=await API.get(`/api/projects/${encodeURIComponent(s.project)}/html-review/tasks/${encodeURIComponent(task.id)}`);if(valid())renderTask(data.task);}catch(error){if(valid())status.textContent=error.message;}},1000);
    }
    async function refresh(){
      invalidate();const serial=s.serial;
      const data=(await API.get(s.base)).evaluation;if(!valid()||serial!==s.serial)return;
      s.data=data;datasets.replaceChildren();for(const d of data.datasets){const o=el('option',d.id);o.value=d.id;datasets.append(o);}fillCases();
      pages.replaceChildren();s.samples=[];
      for(const p of data.pages){const row=el('div'),check=el('input'),course=el('input'),split=select([['development','开发集'],['holdout','留出集']],'样本划分');check.type='checkbox';course.value='course-1';course.setAttribute('aria-label','课程 '+p.slide_id);row.append(field(p.title,check),field('课程',course),split);pages.append(row);s.samples.push({p,check,course,split});}
      status.textContent=`已读取 ${data.datasets.length} 个数据集。`;if(data.tasks[0])renderTask(data.tasks[0]);
    }
    function fillCases(){invalidate();cases.replaceChildren();const dataset=s.data?.datasets.find(d=>d.id===datasets.value);for(const c of dataset?.cases||[]){const o=el('option',`${c.id} · ${c.course_id} · ${c.split}`);o.value=c.id;cases.append(o);}}
    async function loadCase(){
      invalidate();const serial=s.serial;const data=await command({action:'read_case',dataset_id:datasets.value,case_id:cases.value});if(!valid()||serial!==s.serial)return;
      s.annotation=data.annotation;s.nonce=Array.from(crypto.getRandomValues(new Uint8Array(24)),b=>b.toString(16).padStart(2,'0')).join('');
      status.textContent=`标注版本 ${data.annotation.revision} · ${data.annotation.status}。应用工作台标注后可保存草稿。`;
      accept.disabled=data.annotation.status!=='draft'||!data.annotation.annotator;reject.disabled=accept.disabled;
      history.replaceChildren();for(const h of data.history)history.append(el('li',`版本 ${h.revision} · ${h.status} · ${h.annotator||''} · ${h.review?.reviewer||''}`));
      frame.src=data.workbench_url;frame.hidden=false;
    }
    frame.onload=()=>{if(s.annotation&&s.nonce)frame.contentWindow.postMessage({type:'ppt-reference-init',session:s.annotation.source_sha256,nonce:s.nonce},'*');};
    s.message=event=>{const m=event.data;if(!valid()||event.source!==frame.contentWindow||m?.type!=='ppt-reference-correction'||!s.nonce||m.nonce!==s.nonce||m.session!==s.annotation?.source_sha256||m.correction?.session_sha256!==s.annotation?.source_sha256)return;s.mapping=m.correction.mapping;save.disabled=false;status.textContent='标注已读取，尚未保存。请填写标注者并保存草稿。';};window.addEventListener('message',s.message);
    const handle=fn=>async()=>{try{await fn();}catch(error){if(valid())status.textContent=error.message;}};
    reload.onclick=handle(refresh);datasets.onchange=fillCases;cases.onchange=invalidate;open.onclick=handle(loadCase);
    createButton.onclick=handle(async()=>{const samples=s.samples.filter(x=>x.check.checked).map(x=>({slide_id:x.p.slide_id,course_id:x.course.value.trim(),split:x.split.value}));await command({action:'create_dataset',dataset_id:id.value.trim(),samples});await refresh();});
    save.onclick=handle(async()=>{await command({action:'save_labels',dataset_id:datasets.value,case_id:cases.value,expected_revision:s.annotation.revision,source_sha256:s.annotation.source_sha256,annotator:annotator.value.trim(),mapping:s.mapping});await loadCase();});
    const review=decision=>handle(async()=>{await command({action:'review_labels',dataset_id:datasets.value,case_id:cases.value,expected_revision:s.annotation.revision,source_sha256:s.annotation.source_sha256,reviewer:reviewer.value.trim(),decision,note:note.value.trim()});await loadCase();});accept.onclick=review('accept');reject.onclick=review('reject');
    start.onclick=handle(async()=>{start.disabled=true;try{const count=(s.data?.datasets.find(d=>d.id===datasets.value)?.cases.length||0)*2*Number(repetitions.value);const data=await command({action:'start_experiment',dataset_id:datasets.value,before:{protocol:before.value,model_role:beforeRole.value},after:{protocol:after.value,model_role:afterRole.value},repetitions:Number(repetitions.value),max_model_calls:Math.min(128,Math.max(2,count)),max_http_calls:Math.min(256,Math.max(2,count*2))});if(valid())renderTask(data.task);}finally{start.disabled=false;}});
    cancel.onclick=handle(async()=>{if(s.task){const data=await API.post(`/api/projects/${encodeURIComponent(s.project)}/html-review/tasks/${encodeURIComponent(s.task.id)}/cancel`,{});if(valid())renderTask(data.task);}});
  }
  window.HtmlEvaluationPanel={mount,clear};
})();
