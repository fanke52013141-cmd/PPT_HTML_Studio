// Reference correction uses the original project task API and author/approval gates.
(function () {
  'use strict';
  if (window.HtmlReferenceReview) return;
  const states = new WeakMap();
  const node = (tag, text = '') => Object.assign(document.createElement(tag), {textContent:text});
  async function refresh(section, current, original, isCurrent) {
    let state = states.get(section);
    if (!state) {
      const box=node('section'), title=node('h4','原图定位复核'), message=node('p');
      message.setAttribute('role','status'); box.dataset.referenceReview='';box.hidden=true;
      const continuation=node('button','复用原设计继续还原');continuation.type='button';continuation.hidden=true;
      const open=node('button','打开定位复核'), submit=node('button','提交修正，继续审核'), cancel=node('button','停止复核');
      [open,submit,cancel].forEach(b=>b.type='button');submit.disabled=true;cancel.hidden=true;
      const label=node('label','导入 correction.json '), file=node('input');file.type='file';file.accept='.json,application/json';label.append(file);
      const frame=node('iframe');frame.title='原图定位复核工作台';frame.setAttribute('sandbox','allow-scripts allow-downloads');frame.hidden=true;frame.style.cssText='width:100%;height:760px;border:1px solid #ddd';
      box.append(title,message,open,label,submit,cancel,continuation,frame);section.querySelector('[data-html-task]').parentElement.after(box);
      state={box,message,open,submit,cancel,file,frame,continuation,serial:0};states.set(section,state);
      frame.onload=()=>{if(state.reference&&state.nonce)frame.contentWindow.postMessage({type:'ppt-reference-init',session:state.reference.key,nonce:state.nonce},'*');};
      window.addEventListener('message',event=>{const m=event.data;
        if(event.source!==frame.contentWindow||m?.type!=='ppt-reference-correction'||!state.nonce||m.nonce!==state.nonce||m.session!==state.reference?.key||m.correction?.session_sha256!==state.reference?.key||!state.isCurrent()||state.box.hidden)return;
        state.correction=m.correction;submit.disabled=false;message.textContent='框选修正已应用；点击提交修正继续审核。';
      });
      continuation.onclick=async()=>{const serial=state.serial;continuation.disabled=true;try{await API.post(state.productionBase+'/produce',{plan_version:'0.2.0',design_candidate_key:state.reference.continuation_design_key,reference_review_key:state.task.result.reference_review_key});if(serial===state.serial){message.textContent='已提交原设计续接；仍需通过原完整检查与保存门禁。';document.dispatchEvent(new Event('ppt:html-candidate-changed'));}}catch(error){if(serial===state.serial)message.textContent=error.message;}finally{continuation.disabled=false;}};
      open.onclick=()=>{frame.src=state.reference.workbench_url;frame.hidden=false;};
      file.onchange=async()=>{
        const serial=state.serial;
        try {const f=file.files[0];if(!f)return;if(f.size>1000000)throw Error('修正文件超过1MB');
          const correction=JSON.parse(await f.text());if(serial!==state.serial)return;
          if(correction.session_sha256!==state.reference.key)throw Error('修正文件不属于当前会话');
          state.correction=correction;submit.disabled=false;message.textContent='修正文件已读取；提交时检查准确文字、完整框和当前来源。';
        } catch(error){state.correction=null;submit.disabled=true;message.textContent=error.message;}
      };
      submit.onclick=async()=>{
        const serial=state.serial;submit.disabled=true;
        try {const result=await API.post(state.base+'/resume',state.correction);if(serial!==state.serial)return;await follow(result.task,serial);}
        catch(error){if(serial===state.serial)message.textContent=error.message;}
      };
      cancel.onclick=async()=>{try{if(state.task)await API.post(`/api/projects/${encodeURIComponent(state.project)}/html-review/tasks/${encodeURIComponent(state.task.id)}/cancel`,{});}catch(error){message.textContent=error.message;}};
      async function follow(task,serial){
        state.task=task;
        while(serial===state.serial&&state.isCurrent()){
          const active=['queued','running'].includes(task.status);cancel.hidden=!active;
          message.textContent=active?'定位复核正在执行。原生产任务、作者页面和视觉批准保持原状态。':task.status==='succeeded'
            ?`复核已结束：${task.result?.review?.result?.status||'请查看证据'}。尚未保存作者页面或批准画面。`:`复核停止：${task.error||task.status}；不会自动重发。`;
          continuation.hidden=!(task.status==='succeeded'&&task.result?.review?.result?.status==='pass'&&task.result?.reference_review_key&&state.reference.continuation_design_key);
          if(!active)return;
          await new Promise(resolve=>setTimeout(resolve,900));if(serial!==state.serial||!state.isCurrent())return;
          task=(await API.get(`/api/projects/${encodeURIComponent(state.project)}/html-review/tasks/${encodeURIComponent(task.id)}`)).task;
          state.task=task;
        }
      }
      state.follow=follow;
    }
    const serial=++state.serial;state.nonce=Array.from(crypto.getRandomValues(new Uint8Array(24)),b=>b.toString(16).padStart(2,'0')).join('');state.isCurrent=isCurrent;state.box.hidden=true;state.frame.hidden=true;state.frame.removeAttribute('src');state.correction=null;state.submit.disabled=true;state.file.value='';
    if(!original?.progress?.reference_workbench||!['failed','interrupted'].includes(original.status))return;
    state.project=current.project.id;state.continuation.hidden=true;
    state.productionBase=`/api/projects/${encodeURIComponent(state.project)}/html-review/${encodeURIComponent(current.slideId)}`;
    state.base=`/api/projects/${encodeURIComponent(state.project)}/html-review/${encodeURIComponent(current.slideId)}/reference/${encodeURIComponent(original.id)}`;
    try{const result=await API.get(state.base);if(serial!==state.serial||!isCurrent())return;
      state.reference=result.reference;state.open.disabled=false;state.box.hidden=false;state.message.textContent=`待复核对象：${result.reference.unresolved_targets.join('、')||'请核对定位'}。打开复核后可直接框选并使用修正，再显式提交审核。`;
      if(result.reference.task)await state.follow(result.reference.task,serial);
    }catch(error){if(serial===state.serial&&isCurrent()){state.box.hidden=false;state.open.disabled=true;state.message.textContent=`定位复核不可用：${error.message}`;}}
  }
  function clear(section) {const state=states.get(section);if(!state)return;++state.serial;state.nonce=null;state.box.hidden=true;state.frame.hidden=true;state.frame.removeAttribute('src');state.correction=null;state.submit.disabled=true;}
  window.HtmlReferenceReview={refresh,clear};
})();
