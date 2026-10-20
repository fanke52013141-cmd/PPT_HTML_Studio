// Project Pi candidates: transport/recovery only; original editors own application.
(() => {
  'use strict';
  let active;
  function open(phase) {
    const project=window.PPTStudio?.runtime?.state?.currentProject;
    if(!project || project.visual_backend !== 'html') { window.showToast?.('请先进入 HTML 项目'); return; }
    active?.close();
    const dialog=document.createElement('dialog');
    dialog.className='html-pi-workflow-dialog';
    dialog.innerHTML='<h3>Pi Agent 候选任务</h3><p>后台执行；结果供原编辑器采用，不覆盖正式内容。</p><label>主题或补充要求<textarea data-input rows="3" maxlength="2000"></textarea></label><div><button data-start>开始任务</button><button data-restore>恢复上次任务</button><button data-cancel disabled>停止任务</button><button data-close>关闭</button></div><p data-status role="status"></p><pre data-result style="max-height:45vh;overflow:auto;white-space:pre-wrap"></pre><button data-download hidden>下载候选</button>';
    document.body.append(dialog); active=dialog;
    const find=name=>dialog.querySelector(`[data-${name}]`), API=window.API;
    const key=`pi-workflow:${project.id}:${phase}`, base=`/api/projects/${encodeURIComponent(project.id)}/agent/jobs`;
    let reference=null, result=null, timer;
    const current=()=>dialog.open&&window.PPTStudio?.runtime?.state?.currentProject?.id===project.id;
    const remember=value=>{reference=value;localStorage.setItem(key,JSON.stringify(value));};
    function stop(){clearTimeout(timer);}
    function failed(error){find('status').textContent=error.message;find('start').disabled=Boolean(reference);}
    async function poll(){
      if(!current()||!reference?.job_id)return;
      try{
        const job=await API.get(`${base}/${encodeURIComponent(reference.job_id)}`);
        if(!current())return;
        const labels={queued:'排队中',running:'执行中',succeeded:'已完成',failed:'失败',cancelled:'已停止',interrupted:'已中断'};
        find('status').textContent=`${labels[job.status]||job.status} · ${job.progress}% · 模型调用 ${job.usage?.model_calls||0}`;
        find('cancel').disabled=!job.can_cancel;
        if(['queued','running'].includes(job.status)){timer=setTimeout(poll,1500);return;}
        find('start').disabled=false;
        if(job.status==='succeeded'){
          result=job.result;
          find('result').textContent=phase==='article'?result.candidate.content:
            (result.candidate.slides||[]).map((slide,index)=>`${index+1}. ${slide.slide_title||slide.slide_id}\n${slide.narration||
              (slide.visual_elements||[]).map(element=>`${element.visual_description}\n对应讲稿：${element.narration}`).join('\n\n')}`).join('\n\n');
          find('download').hidden=false;
        }else find('status').textContent=job.error?.message||job.status;
      }catch(error){failed(error);}
    }
    find('start').onclick=async()=>{
      if(!current())return;
      const input=find('input').value.trim();
      if(phase==='article'&&!input){find('status').textContent='请填写主题';return;}
      const payload={idempotency_key:crypto.randomUUID(),task:phase==='article'?{task_type:'article.generate',topic:input}:
        {task_type:'storyboard.plan',phase,requirement:input},delivery_policy:'candidate'};
      find('start').disabled=true;find('download').hidden=true;find('result').textContent='';
      try{
        remember({pending:payload});
        const job=await API.post(base,payload,{timeoutMs:15000});remember({job_id:job.job_id});await poll();
      }catch(error){
        if([400,404,409,422].includes(error.status)){reference=null;localStorage.removeItem(key);}
        failed(error);
      }
    };
    find('restore').onclick=async()=>{
      try{
        reference=JSON.parse(localStorage.getItem(key)||'null');
        if(!reference)throw Error('没有可恢复的任务');
        find('start').disabled=true;
        if(reference.pending){const job=await API.post(base,reference.pending,{timeoutMs:15000});remember({job_id:job.job_id});}
        stop();await poll();
      }catch(error){failed(error);}
    };
    find('cancel').onclick=async()=>{
      try{await API.post(`${base}/${encodeURIComponent(reference.job_id)}/cancel`,{});stop();await poll();}
      catch(error){failed(error);}
    };
    find('download').onclick=()=>{
      if(!current()||!result)return;
      const article=phase==='article', data=article?result.candidate.content:JSON.stringify(result.candidate,null,2);
      const url=URL.createObjectURL(new Blob([data],{type:article?'text/markdown;charset=utf-8':'application/json'}));
      const link=document.createElement('a');link.href=url;link.download=article?'article-candidate.md':`${phase}-candidate.json`;link.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    find('close').onclick=()=>dialog.close();
    dialog.addEventListener('close',()=>{stop();dialog.remove();if(active===dialog)active=null;},{once:true});
    dialog.showModal();
    if(phase==='article'){find('input').maxLength=500;find('input').value=document.getElementById('step1-topic-input')?.value||'';}
    try{reference=JSON.parse(localStorage.getItem(key)||'null');}catch(_){reference=null;}
    if(reference){find('start').disabled=true;find('status').textContent='存在历史任务，请先恢复并核对状态';}
  }
  document.addEventListener('click',event=>{const button=event.target.closest('[data-pi-workflow]');if(button)open(button.dataset.piWorkflow);});
  window.HtmlPiWorkflows={open};
})();
