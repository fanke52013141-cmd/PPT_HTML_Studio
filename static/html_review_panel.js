// HTML workspace review panel. Explicit lifecycle events; no body observer.
(function initHtmlReviewPanel() {
  if (window.__htmlReviewPanelReady) return;
  window.__htmlReviewPanelReady = true;
  let generation = 0;
  let activeTask = null;
  let lastTask = null;
  let designCandidate = null;
  let acceptedDesignKey = null;
  let manualCandidate = null;
  function clearManual(section) {
    manualCandidate = null;
    const box = section.querySelector('[data-html-manual-candidate]');
    if (box) { box.hidden = true; box.querySelectorAll('img').forEach(image => image.removeAttribute('src')); }
  }
  async function showManual(section, current, task, token) {
    clearManual(section);
    if (task.status !== 'failed' || task.input_state !== 'current' || !task.recovery?.requires_verification) return;
    const base = `/api/projects/${encodeURIComponent(current.project.id)}/html-review/${encodeURIComponent(current.slideId)}/manual-candidate/${encodeURIComponent(task.id)}`;
    try {
      const result = await API.get(base);
      if (token !== generation) return;
      manualCandidate = { ...result.candidate, base };
      const box = section.querySelector('[data-html-manual-candidate]');
      box.hidden = false;
      box.querySelector('[data-manual-source]').textContent = `原任务 ${task.id} · 候选 ${manualCandidate.key.slice(0, 12)} · 最终工程检查${manualCandidate.engineering === 'passed' ? '通过' : '未通过'}，模型还原结论未知。`;
      box.querySelector('[data-manual-design]').src = manualCandidate.design_url;
      box.querySelector('[data-manual-preview]').src = manualCandidate.preview_url;
      box.querySelector('[data-manual-decision]').textContent = manualCandidate.decision
        ? `已记录人工${manualCandidate.decision.decision === 'accept' ? '接受' : '驳回'}：${manualCandidate.decision.note}。原生产任务仍保持失败。`
        : manualCandidate.engineering === 'passed'
          ? '请对照原设计与实际页面，填写具体判断依据后决定。接受仅留存候选评审，不会保存作者页面或批准正式视觉。'
          : `此候选工程检查未通过，只能记录驳回；首个问题：${manualCandidate.engineering_issues?.[0]?.message || '请检查版式容量'}。`;
      box.querySelectorAll('[data-manual-action]').forEach(button => button.hidden = Boolean(manualCandidate.decision));
      box.querySelector('[data-manual-action="accept"]').hidden ||= manualCandidate.engineering !== 'passed';
    } catch (error) {
      if (token === generation) status(section, `候选不可评审：${error.message}`);
    }
  }
  function showAssetRetry(section, key) {
    acceptedDesignKey = key;
    section.querySelector('[data-html-asset-retry]').hidden = !key;
  }
  function showDesign(section, design, base) {
    designCandidate = design;
    const box = section.querySelector('[data-html-design]');
    box.hidden = !design;
    if (!design) return;
    const image = box.querySelector('img');
    image.src = design.image_url || `${base}/design/${encodeURIComponent(design.key)}/image`;
    box.querySelector('[data-action="accept-design"]').disabled = Boolean(design.stale);
    box.querySelector('[data-design-state]').textContent = design.stale ? '内容或修订已变化，请重新生成设计。' : '这是设计参考。确认后生成独立素材和实际 HTML；最终页面仍需审阅。';
  }
  function context() {
    const state = window.PPTStudio?.runtime?.state;
    const project = state?.currentProject;
    const slide = state?.slides?.[state.activeSlideIndex] || state?.slides?.[0];
    return { project, slideId: slide?.slide_id || slide?.id || '' };
  }
  function status(section, message) {
    const target = section.querySelector('[data-html-status]');
    if (target.textContent !== message) target.textContent = message;
  }
  const stageLabels = {queued:'等待处理',running:'正在处理',plan:'内容规划',brief:'设计规划',design:'设计参考',design_understanding:'设计理解与素材分工',design_reconstruction:'依据设计图还原',design_fidelity_review:'设计还原审核',compile:'构建画面',review:'页面检查',rebuild:'重建影响',json_request:'模型请求',json_returned:'模型已返回',image_request:'图片请求',image_returned:'图片已返回',image_unknown:'图片结果待核实',json_unknown:'模型结果待核实',design_review:'等待设计确认'};
  const taskStatusLabels={queued:'等待处理',running:'生产中',succeeded:'任务结束',failed:'生产失败',interrupted:'任务中断',cancelled:'已停止'};
  function taskFacts(section, task) {
    lastTask = task;
    const box = section.querySelector('[data-html-task]');
    box.replaceChildren();
    section.querySelector('[data-action="resume"]').hidden=true;
    section.querySelector('[data-action="cancel"]').hidden=true;
    if (!task) return;
    const line = text => {const p=document.createElement('p');p.textContent=text;box.append(p);};
    line(`页面 ${task.slide_id || '未知'} · ${taskStatusLabels[task.status] || task.status} · ${stageLabels[task.stage] || task.stage || ''} · 第 ${task.attempt || 1} 次尝试`);
    if (task.input_state === 'stale') line('此任务对应旧输入，不能作为当前页面完成结果。');
    if (task.snapshot_id) line(`输入版本：${task.snapshot_id}`);
    const progress=task.progress || {};
    if (progress.model_stream) {
      const stream=progress.model_stream;
      const labels={waiting:'等待模型响应',thinking:'模型思考中',outputting:'正在接收结果',completed:'结果接收完成',failed:'接收中断，需核验原请求'};
      line(`${labels[stream.state] || '模型处理中'} · ${Math.round(stream.elapsed_seconds || 0)} 秒 · 已接收正文 ${stream.content_chars || 0} 字符`);
    }
    if (progress.repair_round != null) line(`排版修复：${progress.repair_round} / ${progress.max_rounds} 轮`);
    for (const skill of progress.runtime_skill?.skills || []) line(`已加载 Skill：${skill.id} ${skill.version}`);
    const returned=Object.values(task.stages || {}).filter(s=>s.state==='returned');
    if (returned.length) line(`已记录阶段：${returned.map(s=>stageLabels[s.stage] || s.stage).join('、')}`);
    if (progress.reused_stages?.length) line(`已复用 ${progress.reused_stages.length} 个原请求结果；后续检查仍需通过。`);
    if (task.error) line(`失败原因：${task.error}`);
    if (task.recovery?.requires_verification) line('供应商结果或回执需先核实，不能直接重复请求。');
    const resume=section.querySelector('[data-action="resume"]');
    resume.hidden=!task.recovery?.can_resume || task.input_state !== 'current';
    resume.disabled=false;
    section.querySelector('[data-action="cancel"]').hidden=!['queued','running'].includes(task.status);
  }
  async function followTask(section, task, current, token) {
    if (token !== generation) return null;
    if (!['queued','running'].includes(task.status) && !task.input_state) {
      task=(await API.get(`/api/projects/${encodeURIComponent(current.project.id)}/html-review/tasks/${encodeURIComponent(task.id)}`)).task;
      if(token!==generation) return null;
    }
    activeTask={id:task.id,project:current.project.id,slide:current.slideId};
    while (token === generation) {
      taskFacts(section, task);
      if (!['queued','running'].includes(task.status)) return task;
      status(section, '任务正在处理，阶段状态会自动更新。');
      await new Promise(resolve=>setTimeout(resolve,900));
      if (token !== generation) return null;
      try {
        task=(await API.get(`/api/projects/${encodeURIComponent(current.project.id)}/html-review/tasks/${encodeURIComponent(task.id)}`)).task;
      } catch(error) {
        if (token === generation) status(section, `状态连接中断，正在重试：${error.message}`);
      }
    }
    return null;
  }
  async function restoreTask(section, current, token) {
    try {
      const response=await API.get(`/api/projects/${encodeURIComponent(current.project.id)}/html-review/${encodeURIComponent(current.slideId)}/task/current`);
      if (token !== generation) return;
      if (!response.task) return;
      section.querySelectorAll('[data-action="produce"],[data-action="accept-design"],[data-action="revise-design"],[data-action="retry-asset"]').forEach(b=>b.disabled=true);
      const task=await followTask(section,response.task,current,token);
      if (!task || token !== generation) return;
      await showManual(section,current,task,token);
      if (task.status !== 'succeeded') status(section, task.error || taskStatusLabels[task.status] || '任务状态待检查');
      else if (task.input_state === 'stale') status(section,'旧任务已结束；当前页面需要重新检查。');
      else if (task.input_state === 'unknown') status(section,'旧任务缺少完整版本信息，请重新检查当前页面。');
      else if (task.result?.stage !== 'design_review') status(section,'已恢复生产记录；可编辑实际页面，审阅后再批准。');
      if (task.status === 'succeeded' && task.input_state === 'current') {
        const base=`/api/projects/${encodeURIComponent(current.project.id)}/html-review/${encodeURIComponent(current.slideId)}`;
        if(task.result?.stage === 'design_review') {
          const design=await API.get(`${base}/design/current`);
          if(token!==generation) return;
          showDesign(section,design.design,base);
        } else if(task.result?.review?.screenshot) {
          const image=section.querySelector('[data-html-preview]');
          image.src=`${base}/screenshot`; image.hidden=false;
        }
      }
    } catch(error) {if(token===generation) status(section,`任务恢复失败：${error.message}`);}
    finally {
      if(token===generation) {
        activeTask=null;
        section.querySelectorAll('[data-action="produce"],[data-action="accept-design"],[data-action="revise-design"],[data-action="retry-asset"]').forEach(b=>b.disabled=false);
        if(designCandidate?.stale) section.querySelector('[data-action="accept-design"]').disabled=true;
        section.querySelector('[data-action="resume"]').disabled=false;
      }
    }
  }
  function refresh() {
    const host = document.getElementById('step-panel-3');
    if (!host) return;
    const {project, slideId} = context();
    const mode = project?.visual_backend === "html" ? "true" : "false";
    if (host.dataset.htmlMode !== mode) host.dataset.htmlMode = mode;
    let section = host.querySelector('#html-review-panel-section');
    if (project?.visual_backend !== 'html') {
      window.HtmlSemanticQA?.close();
      if (section && !section.hidden) {generation++; activeTask=null; designCandidate=null; acceptedDesignKey=null;}
      if (section) section.hidden = true;
      if (section) {section.dataset.context=''; taskFacts(section,null);}
      window.HtmlSceneEditor?.close();
      window.HtmlAssetSheets?.close();
      return;
    }
    if (!section) {
      section = document.createElement('section');
      section.id = 'html-review-panel-section';
      section.className = "card soft-outline";
      section.innerHTML = `<style>#step-panel-3[data-html-mode="true"] .step3-toolbar-row,#step-panel-3[data-html-mode="true"] #step3-images-grid{display:none!important}</style><h3>HTML 场景生产与审阅</h3>
        <label>分镜页面 <select data-html-slide></select></label>
        <button class="success" type="button" data-action="produce">生成设计与场景</button>
        <button type="button" data-action="review">静态审阅</button>
        <button class="success" type="button" data-action="approve">批准本页</button>
        <button type="button" data-action="edit">编辑对象与动作</button>
        <button type="button" data-action="models">项目生成模型</button>
        <button type="button" data-action="sheets">批量生成配图</button>
        <button type="button" data-action="cancel" hidden>停止生产任务</button>
        <div data-html-status role="status"></div><div data-html-task aria-label="生产任务记录"></div><button type="button" data-action="resume" hidden>继续原生产任务</button>
        <div data-html-manual-candidate hidden>
          <h4>人工候选评审（原请求结果未知）</h4><p data-manual-source></p>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px">
            <figure><figcaption>原设计参考</figcaption><img data-manual-design alt="原设计参考" style="width:100%"></figure>
            <figure><figcaption>实际候选截图</figcaption><img data-manual-preview alt="候选页面实际截图" style="width:100%"></figure>
          </div>
          <p data-manual-decision></p>
          <label>判断依据 <textarea data-manual-note maxlength="2000" placeholder="说明具体一致或不一致的对象、位置与可读性"></textarea></label>
          <button type="button" data-manual-action="accept">记录接受</button>
          <button type="button" data-manual-action="reject">记录驳回</button>
        </div>
        <div data-html-design hidden>
          <p data-design-state></p>
          <img alt="待确认的黑灰白页面设计参考" style="max-width:100%">
          <label>设计修改方向 <textarea data-design-instruction maxlength="2000" placeholder="例如：加强标题层级，减少卡片边框"></textarea></label>
          <button type="button" data-action="revise-design">修改设计参考</button>
          <button class="success" type="button" data-action="accept-design">确认设计并生成实际页面</button>
        </div>
        <div data-html-asset-retry hidden>
          <label>主体素材修改方向 <textarea data-asset-instruction maxlength="2000" placeholder="例如：简化细节，增强主体轮廓"></textarea></label>
          <button type="button" data-action="retry-asset">仅返工主体素材</button>
        </div>
        <img data-html-preview alt="当前场景的实际渲染" hidden style="max-width:100%">
        <div data-html-editor></div>
        <div data-html-models hidden></div><div data-semantic-qa></div>`;
      const sheetHost = document.createElement('div'); sheetHost.dataset.htmlSheets = ''; sheetHost.hidden = true; section.append(sheetHost);
      host.prepend(section);
      section.querySelector('[data-html-slide]').addEventListener('change', event => {
        window.PPTStudio.runtime.state.activeSlideIndex = Number(event.target.value);
        refresh();
      });
      section.addEventListener('click', async event => {
        const manualButton = event.target.closest('button[data-manual-action]');
        if (manualButton) {
          if (!manualCandidate) return;
          const note = section.querySelector('[data-manual-note]').value.trim();
          if (note.length < 8) { status(section, '请先填写至少 8 字的具体判断依据。'); return; }
          manualButton.disabled = true;
          try {
            const result = await API.post(`${manualCandidate.base}/decision`, {key:manualCandidate.key,decision:manualButton.dataset.manualAction,note});
            manualCandidate.decision = result.candidate.decision;
            section.querySelector('[data-manual-decision]').textContent = `已记录人工${manualCandidate.decision.decision === 'accept' ? '接受' : '驳回'}：${manualCandidate.decision.note}。原生产任务仍保持失败。`;
            section.querySelectorAll('[data-manual-action]').forEach(button => button.hidden = true);
          } catch (error) { status(section, `候选决定未保存：${error.message}`); manualButton.disabled = false; }
          return;
        }
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        if (button.dataset.action === 'sheets') {
          const current = context(); const container = section.querySelector('[data-html-sheets]');
          container.hidden = !container.hidden;
          if (container.hidden) {window.HtmlAssetSheets?.close(); return;}
          try {await window.HtmlAssetSheets.open(container, current.project);}
          catch(error) {status(section, `素材板加载失败：${error.message}`);}
          return;
        }
        if (button.dataset.action === 'models') {
          const current = context();
          const container = section.querySelector('[data-html-models]');
          if (!window.ProjectModelBinding) { status(section, '模型配置模块尚未加载。'); return; }
          container.hidden = !container.hidden;
          if (!container.hidden) await window.ProjectModelBinding.mount(container, current.project);
          return;
        }
        if (button.dataset.action === 'edit') {
          const current = context();
          if (!current.slideId) { status(section, '请先选择分镜页面。'); return; }
          if (!window.HtmlSceneEditor) { status(section, '场景编辑器脚本尚未接入。'); return; }
          try { await window.HtmlSceneEditor.open(section.querySelector('[data-html-editor]'), current.project.id, current.slideId); }
          catch(error) { status(section, `编辑器加载失败：${error.message}`); }
          return;
        }
        if (button.dataset.action === 'cancel') {
          if (!activeTask) return;
          try { await API.post(`/api/projects/${encodeURIComponent(activeTask.project)}/html-review/tasks/${encodeURIComponent(activeTask.id)}/cancel`, {}); }
          catch(error) { status(section, `停止失败：${error.message}`); }
          return;
        }
        const current = context();
        if (!current.slideId) { status(section, '请先选择分镜页面。'); return; }
        const token = ++generation;
        const base = `/api/projects/${encodeURIComponent(current.project.id)}/html-review/${encodeURIComponent(current.slideId)}`;
        section.querySelectorAll('button:not([data-action="cancel"])').forEach(b=>b.disabled=true);
        status(section, '处理中…');
        try {
          let action = button.dataset.action;
          let payload = action === 'produce' ? {plan_version: '0.2.0'} : {};
          if (action === 'accept-design') {
            if (!designCandidate || designCandidate.stale) throw new Error('请先生成并审阅当前设计。');
            payload = {design_candidate_key: designCandidate.key}; action = 'produce';
          } else if (action === 'revise-design') {
            const instruction = section.querySelector('[data-design-instruction]').value.trim();
            if (!instruction) throw new Error('请填写本轮设计修改方向。');
            payload = {design_instruction: instruction, plan_version:'0.2.0'}; action = 'produce';
          } else if (action === 'retry-asset') {
            const instruction = section.querySelector('[data-asset-instruction]').value.trim();
            if (!acceptedDesignKey || !instruction) throw new Error('请填写主体素材修改方向，并确认当前设计仍有效。');
            payload = {design_candidate_key: acceptedDesignKey, asset_instruction: instruction}; action = 'produce';
          }
          let result = action === 'resume' ? await API.post(`/api/projects/${encodeURIComponent(current.project.id)}/html-review/tasks/${encodeURIComponent(lastTask.id)}/resume`, {}) : await API.post(`${base}/${action}`, payload);
          if (result.task) {
            const task = await followTask(section,result.task,current,token);
            if (!task || token !== generation) return;
            if (task.status !== 'succeeded') throw new Error(task.error || taskStatusLabels[task.status] || '任务状态待检查');
            if (task.input_state === 'stale') throw new Error('任务对应旧输入，请重新读取当前页面。');
            result = task.result;
            if (result.review?.screenshot) result.review.screenshot_url = `${base}/screenshot`;
          }
          if (token !== generation || context().project?.id !== current.project.id || context().slideId !== current.slideId) return;
          if (result.stage === 'design_review' && result.design) {
            showAssetRetry(section, null);
            showDesign(section, result.design, base);
            status(section, result.message);
          } else if (result.review) {
            showDesign(section, null, base);
            if (result.design_candidate_key) showAssetRetry(section, result.design_candidate_key);
            status(section, result.review.passed ? '静态检查通过，请查看画面后决定是否批准。' : `检查未通过：${result.review.message || result.review.code}`);
            if (result.review.screenshot_url) {
              const image = section.querySelector('[data-html-preview]');
              image.src = result.review.screenshot_url; image.hidden = false;
            }
          } else if (result.approval) {
            status(section, '本页已批准；相关输入变化后需要重新审阅。');
            if (typeof window.refreshCurrentProjectStatus === 'function') await window.refreshCurrentProjectStatus();
          }
          else status(section, result.message || '场景已生成，可以静态审阅。');
        } catch(error) { if (token === generation) status(section, `操作失败：${error.message}`); }
        finally {
          if (token === generation) {
            activeTask=null; section.querySelector('[data-action="cancel"]').hidden=true;
            section.querySelectorAll('button').forEach(b=>b.disabled=false);
            if (designCandidate?.stale) section.querySelector('[data-action="accept-design"]').disabled=true;
          }
        }
      });
    }
    section.hidden = false;
    const slides = window.PPTStudio.runtime.state.slides || [];
    const optionsKey = JSON.stringify(slides.map(s=>[s.slide_id || s.id,s.title || s.slide_title || '']));
    const select = section.querySelector('[data-html-slide]');
    if (select.dataset.options !== optionsKey) {
      select.replaceChildren(...slides.map((slide,index)=>{
        const option=document.createElement('option'); option.value=String(index);
        option.textContent=`${index+1}. ${slide.title || slide.slide_title || slide.slide_id || slide.id}`;
        return option;
      }));
      select.dataset.options=optionsKey;
    }
    select.value=String(Math.max(0,slides.findIndex(s=>(s.slide_id || s.id)===slideId)));
    const key = `${project.id}:${slideId}`;
    if (section.dataset.context !== key) {
      window.HtmlSceneEditor?.close();
      section.querySelector('[data-html-editor]').replaceChildren();
      if (section.dataset.project !== project.id) {
        window.HtmlAssetSheets?.close();
        const sheets = section.querySelector('[data-html-sheets]'); sheets.replaceChildren(); sheets.hidden = true;
        const modelContainer = section.querySelector('[data-html-models]');
        modelContainer.replaceChildren();
        modelContainer.hidden = true;
        section.dataset.project = project.id;
      }
      window.HtmlSemanticQA?.close();
      generation++;
      activeTask=null;
      taskFacts(section,null);
      designCandidate = null;
      showAssetRetry(section, null);
      showDesign(section, null, '');
      clearManual(section);
      section.querySelector('[data-design-instruction]').value = '';
      section.querySelector('[data-asset-instruction]').value = '';
      section.querySelectorAll('button').forEach(b=>b.disabled=false);
      section.dataset.context = key;
      section.querySelector('[data-action="cancel"]').hidden=true;
      status(section, slideId ? '先生成设计参考，确认后生成实际页面，再审阅批准。' : '请先选择分镜页面。');
      section.querySelector('[data-html-preview]').hidden = true;
      if (slideId) {
        const token = generation;
        window.HtmlSemanticQA?.mount(section.querySelector("[data-semantic-qa]"),project,slideId);
        restoreTask(section,{project,slideId},token);
        const base = `/api/projects/${encodeURIComponent(project.id)}/html-review/${encodeURIComponent(slideId)}`;
        API.get(`${base}/design/current`).then(result => {
          if (token !== generation || section.hidden) return;
          if (result.design?.status === 'needs_review') {
            showDesign(section, result.design, base);
            status(section, result.design.stale ? '旧设计已过期，请重新生成。' : '已恢复待确认的设计参考。');
          } else if (result.design?.status === 'accepted_for_reconstruction' && !result.design.stale) {
            showAssetRetry(section, result.design.key);
          }
        }).catch(error => {if (token === generation) status(section, `设计恢复失败：${error.message}`);});
      }
    }
  }
  document.addEventListener('DOMContentLoaded', refresh);
  document.addEventListener('click', () => queueMicrotask(refresh));
  document.addEventListener('ppt:workspace-changed', refresh);
  window.HtmlReviewPanel = {refresh};
})();
