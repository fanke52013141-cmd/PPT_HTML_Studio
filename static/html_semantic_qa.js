/* A04 explicit page lifecycle, shared transport, and separate human review. */
(function () {
  'use strict';
  let epoch=0;
  function text(tag,value) {const node=document.createElement(tag);node.textContent=value;return node;}
  async function mount(host,project,slide) {
    const token=++epoch;host.replaceChildren();if (!slide) return;
    const base=`/api/projects/${encodeURIComponent(project.id)}/html-review/${encodeURIComponent(slide)}/semantic`;
    host.append(text('h4','逐句画面核验'));
    const state=text('p','读取语义审阅状态…');state.setAttribute('role','status');host.append(state);
    const results=document.createElement('div'),note=document.createElement('textarea');note.setAttribute('aria-label','本页核验说明');note.maxLength=2000;note.placeholder='对照讲稿与画面，填写具体一致或需要修改的地方';host.append(results,note);
    const start=text('button','开始逐句核验'),reload=text('button','刷新核验结果'),approve=text('button','人工签收本页核验'),reject=text('button','退回本页核验');
    for (const button of [start,reload,approve,reject]) {button.type='button';host.append(button);}
    let current=null,taskId=null,polling=false,requestBlocked=false;
    function canStart() {
      // A missing report can be generated; missing or invalid source inputs cannot.
      return Boolean(current?.required && !polling && !requestBlocked &&
        (!current.reason || ['semantic_report_missing_or_invalid','semantic_or_human_review_required'].includes(current.reason)));
    }
    const cancel=text("button","停止语义审阅任务"),resume=text("button","继续原语义审阅任务");cancel.type="button";resume.type="button";cancel.hidden=true;resume.hidden=true;host.append(cancel,resume);
    async function refresh() {
      const response=await API.get(`${base}/status`);if(token!==epoch)return;
      const previousKey=current?.key;
      current=response.semantic_qa;results.replaceChildren();
      if(previousKey&&previousKey!==current.key)note.value='';
      note.hidden=!current.key;
      const task=response.task;taskId=task?.id||null;
      requestBlocked=Boolean(task?.recovery?.requires_verification);
      resume.hidden=!task?.recovery?.can_resume;cancel.hidden=!["queued","running"].includes(task?.status);
      if(task&&!polling&&["queued","running"].includes(task.status)) follow(task).catch(error=>{if(token===epoch)state.textContent=error.message;});
      const labels={passed:'通过',failed:'未通过',unknown:'待检查',stale_or_missing:'待核验',confirmed:'已确认',pending:'待确认',not_evaluated:'待试听',approved:'已签收',rejected:'已退回',needs_review:'待人工检查'};
      const reasons={SEMANTIC_SCENE_MISSING:'先完成本页 HTML 还原',SEMANTIC_AUDIO_REQUIRED:'先生成本页配音',semantic_report_missing_or_invalid:'尚无当前核验报告',semantic_or_human_review_required:'请查看证据并完成本页签收'};
      if(!current.required) state.textContent='旧版页面沿用原有画面和音频门禁，本页不要求新版逐句核验。';
      else state.textContent=`页面检查：${labels[current.engineering]||'待检查'} · 讲稿对应：${labels[current.semantic]||'待核验'} · 音频：${labels[current.audio]||'待试听'} · 人工：${labels[current.human]||'待确认'}${current.reason ? '。'+(reasons[current.reason]||'画面或音频输入需要核对，请刷新当前状态') : ''}`;
      if(requestBlocked)state.textContent+=' · 原请求结果待核实，不能重复提交。';
      start.disabled=!canStart();approve.disabled=!current.key||current.engineering!=='passed'||current.semantic==='failed';reject.disabled=!current.key;
      for(const [index,beat] of (current.beats||[]).entries()) {
        const verdicts={related:'一致',unrelated:'不一致',unclear:'待人工判断',omitted:'遗漏讲稿内容',contradiction:'画面与讲稿矛盾'};
        const block=document.createElement('details');block.append(text('summary',`第${index+1}句 · ${verdicts[beat.result?.verdict] || '待人工检查'}`));block.append(text('p',beat.spoken_text));
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
      }finally{polling=false;if(token===epoch)start.disabled=!canStart();}
    }
    async function submit() {
      if(!canStart())return;
      start.disabled=true;
      try {const result=await API.post(`${base}/submit`,{expected_revision:current.revision});if(token===epoch)await follow(result.task);}
      catch(error){if(token===epoch)state.textContent=error.message;}finally{if(token===epoch)start.disabled=!canStart();}
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
      try {
        await API.post(`${base}/decision`,{expected_revision:current.revision,report_key:current.key,decision:value,note:note.value});
        if(token===epoch){await refresh();await window.refreshCurrentProjectStatus?.();}
      }
      catch(error){if(token===epoch)state.textContent=error.message;}
    }
    start.addEventListener('click',submit);reload.addEventListener('click',()=>refresh().catch(error=>{if(token===epoch)state.textContent=error.message;}));
    approve.addEventListener('click',()=>decision('approved'));reject.addEventListener('click',()=>decision('rejected'));
    await refresh().catch(error=>{if(token===epoch)state.textContent=error.message;});
  }
  function close(){epoch++;}
  window.HtmlSemanticQA={mount,close};
}());
