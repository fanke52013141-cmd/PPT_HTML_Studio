/* A04 explicit page lifecycle, shared transport, and separate human review. */
(function () {
  'use strict';
  let epoch=0;
  function text(tag,value) {const node=document.createElement(tag);node.textContent=value;return node;}
  async function mount(host,project,slide) {
    const token=++epoch;host.replaceChildren();if (!slide) return;
    const base=`/api/projects/${encodeURIComponent(project.id)}/html-review/${encodeURIComponent(slide)}/semantic`;
    host.append(text('h4','逐句语义 QA'));
    const state=text('p','读取语义审阅状态…');state.setAttribute('role','status');host.append(state);
    const results=document.createElement('div'),note=document.createElement('textarea');note.setAttribute('aria-label','语义人工审阅说明');note.maxLength=2000;note.placeholder='查看逐句帧、原句和结论后填写审阅说明';host.append(results,note);
    const start=text('button','开始逐句语义 QA'),reload=text('button','刷新语义结果'),approve=text('button','人工签收语义结果'),reject=text('button','退回语义结果');
    for (const button of [start,reload,approve,reject]) {button.type='button';host.append(button);}
    let current=null,taskId=null,polling=false;
    const cancel=text("button","停止语义审阅任务"),resume=text("button","继续原语义审阅任务");cancel.type="button";resume.type="button";cancel.hidden=true;resume.hidden=true;host.append(cancel,resume);
    async function refresh() {
      const response=await API.get(`${base}/status`);if(token!==epoch)return;
      current=response.semantic_qa;results.replaceChildren();
      const task=response.task;taskId=task?.id||null;
      resume.hidden=!task?.recovery?.can_resume;cancel.hidden=!["queued","running"].includes(task?.status);
      if(task&&!polling&&["queued","running"].includes(task.status)) follow(task).catch(error=>{if(token===epoch)state.textContent=error.message;});
      if(!current.required) state.textContent='旧版场景：未执行新语义 QA，保留原门禁。';
      else state.textContent=`工程：${current.engineering} · 语义：${current.semantic} · 听审：${current.audio} · 人工：${current.human}${current.reason ? ' · '+current.reason : ''}`;
      start.disabled=!current.required;approve.disabled=!current.key||current.engineering!=='passed'||current.semantic==='failed';reject.disabled=!current.key;
      for(const [index,beat] of (current.beats||[]).entries()) {
        const block=document.createElement('details');block.append(text('summary',`第${index+1}句 · ${beat.result?.verdict || '工程未通过'}`));block.append(text('p',beat.spoken_text));
        for(const evidence of beat.result?.evidence||[])block.append(text('p',`帧${evidence.frameIndex} · ${evidence.targetId||'页面'}：${evidence.observation}`));
        for(const [edge,time]of beat.times.entries()) {
          const image=document.createElement('img');image.alt=`${beat.id} 帧${edge} ${time}ms`;image.style.maxWidth='32%';image.loading='lazy';image.src=`${base}/frame?key=${encodeURIComponent(current.key)}&beat=${index}&edge=${edge}`;block.append(image);
        }
        results.append(block);
      }
    }
    async function follow(task) {
      if(polling)return;polling=true;start.disabled=true;taskId=task.id;
      try {
        while(token===epoch&&['queued','running'].includes(task.status)) {
          cancel.hidden=false;
          state.textContent=`逐句审阅：${task.progress?.completed_beats||0}/${task.progress?.total_beats||'?'} · ${task.status}`;
          await new Promise(resolve=>setTimeout(resolve,2000));if(token!==epoch)return;
          task=(await API.get(`/api/projects/${encodeURIComponent(project.id)}/html-review/tasks/${encodeURIComponent(task.id)}`)).task;
        }
        if(token!==epoch)return;
        polling=false;cancel.hidden=true;await refresh();
        if(task.status!=='succeeded')state.textContent=task.error||'语义审阅未完成；查看原任务，未知结果不可盲目重试';
      }finally{polling=false;if(token===epoch)start.disabled=!current?.required||polling;}
    }
    async function submit() {
      start.disabled=true;
      try {const result=await API.post(`${base}/submit`,{expected_revision:current.revision});if(token===epoch)await follow(result.task);}
      catch(error){if(token===epoch)state.textContent=error.message;}finally{if(token===epoch)start.disabled=!current?.required||polling;}
    }
    resume.addEventListener('click',async()=>{
      try{const result=await API.post(`/api/projects/${encodeURIComponent(project.id)}/html-review/tasks/${encodeURIComponent(taskId)}/resume`,{});if(token===epoch)await follow(result.task);}
      catch(error){if(token===epoch)state.textContent=error.message;}
    });
    cancel.addEventListener('click',async()=>{
      try{await API.post(`/api/projects/${encodeURIComponent(project.id)}/html-review/tasks/${encodeURIComponent(taskId)}/cancel`,{});if(token===epoch)state.textContent='停止请求已记录，当前供应商请求的返回结果仍会留作审计。';}
      catch(error){if(token===epoch)state.textContent=error.message;}
    });
    async function decision(value) {
      if(!note.value.trim()){state.textContent='请先查看逐句证据并填写人工审阅说明。';return;}
      try {await API.post(`${base}/decision`,{expected_revision:current.revision,report_key:current.key,decision:value,note:note.value});if(token===epoch)await refresh();}
      catch(error){if(token===epoch)state.textContent=error.message;}
    }
    start.addEventListener('click',submit);reload.addEventListener('click',()=>refresh().catch(error=>{if(token===epoch)state.textContent=error.message;}));
    approve.addEventListener('click',()=>decision('approved'));reject.addEventListener('click',()=>decision('rejected'));
    await refresh().catch(error=>{if(token===epoch)state.textContent=error.message;});
  }
  function close(){epoch++;}
  window.HtmlSemanticQA={mount,close};
}());
