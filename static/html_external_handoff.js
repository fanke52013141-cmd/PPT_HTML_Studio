// External task files and explicit import/preview/save. Rendering stays in the shared services.
(function () {
  'use strict';
  if (window.HtmlExternalHandoff) return;
  const el = (tag, text = '', attributes = {}) => Object.assign(document.createElement(tag), { textContent: text, ...attributes });
  function download(blob, name) {
    const url = URL.createObjectURL(blob), anchor = el('a', '', { href: url, download: name });
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function mount(host, options) {
    const box = el('details'); box.dataset.externalHandoff = '';
    box.append(el('summary', 'AI 自动修改 / 外部 Agent 交接'));
    box.append(el('p', '填写目标后可直接运行 AI 自动修改；也可导出输入包，交给外部 Agent 后导入结果。'));
    const goalLabel = el('label', '任务目标'), goal = el('textarea', '', { maxLength: 4000 });
    goal.placeholder = '说明当前问题、希望达到的效果及必须保留的内容';
    goalLabel.append(goal); box.append(goalLabel);
    const mode = el('select'); mode.setAttribute('aria-label', '交接任务类型');
    for (const [value, text] of [['static_repair', '布局与风格修复'], ['animation_repair', '真实配音与动画修复']]) {
      mode.append(el('option', text, { value }));
    }
    box.append(mode);
    const criteria=el('details'), fonts=el('div'), pairs=el('div');
    criteria.append(el('summary','验收条件：字号与指定遮挡对象对'),el('p','条件由你确认后写入输入包。未配置对象对不代表全片无遮挡。'),fonts,pairs);
    const addFont=el('button','添加最低字号条件',{type:'button'}),addPair=el('button','添加遮挡检查对象对',{type:'button'});
    criteria.append(addFont,addPair);box.append(criteria);
    let fontRows=[],pairRows=[],conditionSerial=0;
    function fill(select,ids){const previous=select.value;select.replaceChildren();for(const id of ids)select.append(el('option',id,{value:id}));if(ids.includes(previous))select.value=previous;}
    function refreshCriteria(){
      const ctx=options.getContext(),ids=ctx.doc.scene.nodes.map(n=>n.id);
      for(const row of fontRows){fill(row.target,ctx.scope);row.parts();}
      for(const row of pairRows){fill(row.a,ids);fill(row.b,ids);}
    }
    addFont.onclick=()=>{
      const row=el('div'),target=el('select'),part=el('select'),minimum=el('input','',{type:'number',min:12,max:80,value:'22'}),remove=el('button','移除条件',{type:'button'});
      target.setAttribute('aria-label','字号条件对象');part.setAttribute('aria-label','字号条件部位');minimum.setAttribute('aria-label','最低字号');
      const record={target,part,minimum,id:`font-${++conditionSerial}`,parts(){const ctx=options.getContext(),node=ctx.doc.scene.nodes.find(n=>n.id===target.value);fill(part,(ctx.doc.capabilities.public_parts?.[node?.type]||[]).filter(p=>!['heading','tag','note'].includes(p)||node?.[p]));}};
      target.onchange=()=>record.parts();fontRows.push(record);remove.onclick=()=>{fontRows=fontRows.filter(r=>r!==record);row.remove();};
      row.append(target,part,minimum,remove);fonts.append(row);refreshCriteria();
    };
    addPair.onclick=()=>{
      const row=el('div'),a=el('select'),b=el('select'),remove=el('button','移除对象对',{type:'button'}),record={a,b};
      a.setAttribute('aria-label','遮挡对象一');b.setAttribute('aria-label','遮挡对象二');pairRows.push(record);
      remove.onclick=()=>{pairRows=pairRows.filter(r=>r!==record);row.remove();};row.append(a,b,remove);pairs.append(row);refreshCriteria();if(b.options.length>1)b.selectedIndex=1;
    };
    const strictLabel = el('label'), strict = el('input', '', { type: 'checkbox', checked: true });
    const diagnosticBaseline=el('input','',{type:'checkbox'}),diagnosticLabel=el('label','原页容量失败时允许导出诊断基线');diagnosticLabel.prepend(diagnosticBaseline);box.append(diagnosticLabel);
    strictLabel.append(strict, document.createTextNode('严格交接：需实际看图、能力声明与逐项验收记录'));
    box.append(strictLabel);
    const scope = el('p', '范围为当前选中对象；导出包含原文、画面、素材和实际风格。未保存修改请先处理。');
    const exportButton = el('button', '导出输入包', { type: 'button' });
    const file = el('input', '', { type: 'file', accept: '.json,.zip,application/json,application/zip', hidden: true });
    const importButton = el('button', '导入 Agent 输出', { type: 'button' });
    const feedbackButton = el('button', '导出检查反馈', { type: 'button', disabled: true });
    const fileLabel = el('p', '严格任务交付 ZIP：result.json、report.md、verification.json；静态候选再附 preflight.json。旧任务兼容 JSON；导入仅检查，不保存。');
    const actions = el('div'); actions.className = 'html-external-actions';
    actions.append(exportButton, importButton, feedbackButton, file);
    const deliveryReport = el('details'), reportBody = el('pre'); deliveryReport.hidden = true;
    deliveryReport.dataset.externalReport = '';
    deliveryReport.append(el('summary', '外部 Agent 交付报告（外部自述）'), reportBody);
    const save = el('button', '保存本次候选', { type: 'button', disabled: true });
    const status = el('p', '', { role: 'status' }), report = el('pre'), pictures = el('div');
    pictures.className = 'html-external-comparison';
    const fullFeedback=el('button','导出完整反馈包',{type:'button',disabled:true});
    const takeover=el('button','人工微调此候选',{type:'button',disabled:true}),restore=el('button','恢复工作草稿',{type:'button'}),problems=el('div');
    box.append(scope, actions, fullFeedback, fileLabel, status, deliveryReport, problems, pictures, report, takeover, restore, save); host.append(box);
    let receipt = null, result = null, feedback = null, feedbackZip = null, reference = null, busy = false, serial = 0;
    const current = () => options.isCurrent() && box.isConnected;
    function context() {
      const ctx = options.getContext();
      if (!ctx.saved) throw Error('有未保存的页面草稿；请先保存，或显式舍弃后重新导出/导入。');
      scope.textContent = `当前范围：${ctx.scope.join('、') || '尚未选择对象'}。原文、素材、关系和人工保护保持。`;
      return ctx;
    }
    function base(ctx) {
      return `/api/projects/${encodeURIComponent(ctx.projectId)}/html-visual/${encodeURIComponent(ctx.slideId)}/handoff`;
    }
    function showComparison(comparison) {
      pictures.replaceChildren();
      for (const [key, label] of [['before', '原实际画面'], ['after', '修改后实际画面']]) {
        for (const shot of comparison?.[key] || []) {
          const figure = el('figure'), image = el('img', '', { alt: label });
          if (!shot.image.startsWith('data:image/png;base64,')) continue;
          image.src = shot.image;
          figure.append(el('figcaption', `${label} · ${shot.timeMs}ms`), image); pictures.append(figure);
        }
      }
    }
    async function run(action) {
      if (busy || !current()) return;
      if (options.canStart && !options.canStart()) { status.textContent = '当前正在处理页面，请等待完成后重试。'; return; }
      busy = true; const token = ++serial; save.disabled = true;
      exportButton.disabled = importButton.disabled = feedbackButton.disabled = true;
      options.setBusy?.(true);
      try { await action(token); return true; }
      catch (error) { if (current()) { receipt = null; status.textContent = error.message; } return false; }
      finally {
        busy = false;
        if (current()) {
          options.setBusy?.(false); save.disabled = !receipt?.passed;
          exportButton.disabled = importButton.disabled = false; feedbackButton.disabled = !feedback;
        }
      }
    }
    const storageKey=()=>{const c=options.getContext();return `html-human-work:${c.projectId}:${c.slideId}`;};
    const workbench=window.HtmlHandoffWorkbench?.mount(box,{
      run:fn=>run(fn),select:options.selectObject,onSaved:options.onSaved,
      request:async(mode,payload)=>{const ctx=context(),response=await API.post(`${base(ctx)}/work/${mode}`,payload,{timeoutMs:180000});if(!current())throw Error('页面已切换');return response;}
    });
    function downloadBase64(value,name){download(new Blob([Uint8Array.from(atob(value),c=>c.charCodeAt(0))],{type:'application/zip'}),name);}
    fullFeedback.onclick=()=>{if(feedbackZip&&!busy)downloadBase64(feedbackZip,`feedback-${feedback.task_id.slice(0,12)}.zip`);};
    takeover.onclick=()=>run(async()=>{if(!reference)throw Error('请先导入合法静态候选');receipt=null;save.disabled=true;await workbench?.open(reference);localStorage.setItem(storageKey(),JSON.stringify(reference));});
    restore.onclick=()=>run(async()=>{const saved=localStorage.getItem(storageKey());if(!saved)throw Error('本页尚无可恢复工作草稿');receipt=null;save.disabled=true;await workbench?.open(JSON.parse(saved),true);});
    function showProblems(response){
      problems.replaceChildren();
      const issues=[...(response.review?.issues||[]),...(response.diagnostic?.issues||[])];
      for(const issue of issues){const target=issue.target?.split(':')[0]||issue.targets?.[0]||issue.targetId;
        const card=el('p'),text=el('span',`${issue.target||target||''} · ${issue.message||issue.code}`);
        card.append(text);if(target){const locate=el('button','定位对象',{type:'button'});locate.onclick=()=>options.selectObject?.(target);card.append(locate);}problems.append(card);}
      if(response.diagnostic){const label=el('p','以下为原Agent候选的播放器诊断图，未通过验收；指定遮挡检查可能尚未运行。');problems.append(label);
        for(const shot of response.diagnostic_pictures||[]){if(shot.image?.startsWith('data:image/png;base64,'))problems.append(el('img','',{src:shot.image,alt:'未通过验收的候选诊断图'}));}}
    }
    function taskInput() {
      const ctx = context();
      if (!goal.value.trim()) throw Error('请填写任务目标。');
      if (!ctx.scope.length) throw Error('请先选择需要修改的对象。');
      return { task_type: mode.value, goal: goal.value.trim(), scope: ctx.scope,
        font_requirements:fontRows.map(r=>({id:r.id,targetId:r.target.value,part:r.part.value,minimum_px:Number(r.minimum.value)})),
        overlap_pairs:pairRows.map(r=>[r.a.value,r.b.value]), expected_revision:ctx.doc.revision,
        expected_audio_revision:ctx.doc.audio_revision, require_verification:true,require_image_understanding:true,
        allow_diagnostic_baseline:diagnosticBaseline.checked };
    }
    function acceptResponse(response) {
      result = response.result; feedback = response.feedback; feedbackZip=response.feedback_bundle_base64;fullFeedback.disabled=!feedbackZip;
      reference=null;takeover.disabled=true;
      if(result?.status==='proposed'&&mode.value==='static_repair'&&response.result_hash){reference={task_id:result.task_id,result_hash:response.result_hash};takeover.disabled=!workbench;}
      showProblems(response);
      if (response.delivery?.report_markdown != null) {
        reportBody.textContent = response.delivery.report_markdown;
        deliveryReport.hidden = false; deliveryReport.open = true;
      }
      report.textContent = JSON.stringify({ message: response.message, diff: response.diff, review: response.review,
        validation:response.validation,acceptance:response.acceptance,external_verification:response.external_verification },null,2);
      showComparison(response.comparison);
      receipt = response.status === 'candidate' && response.passed ? response : null;
      save.disabled=!receipt;
    }
    const piAgent=window.HtmlPiAgent?.mount(box,{before:scope,getContext:options.getContext,isCurrent:current,getTask:taskInput,onSaved:options.onSaved,
      onResult:async response=>{if(!await run(async()=>{context();acceptResponse(response);}))throw Error('页面忙或有未保存修改，请稍后恢复任务结果');}});
    exportButton.onclick = () => run(async token => {
      const ctx = context();
      receipt = null; feedback = null; result = null;
      if (!goal.value.trim()) throw Error('请填写任务目标。');
      if (!ctx.scope.length) throw Error('请先选择需要交接的对象。');
      const font_requirements=fontRows.map(r=>({id:r.id,targetId:r.target.value,part:r.part.value,minimum_px:Number(r.minimum.value)}));
      const overlap_pairs=pairRows.map(r=>[r.a.value,r.b.value]);
      if(overlap_pairs.some(p=>!p[0]||p[0]===p[1]))throw Error('请选择两个不同的遮挡对象。');
      if(font_requirements.some(r=>!r.part||!ctx.scope.includes(r.targetId)||r.minimum_px<12||r.minimum_px>80))throw Error('字号条件须为当前scope中的公开部位，范围12—80。');
      status.textContent = '正在收集实际截图、素材、风格与时间资料…';
      const response = await API.post(`${base(ctx)}/export`, {
        task_type: mode.value, goal: goal.value.trim(), scope: ctx.scope, font_requirements,overlap_pairs,
        expected_revision: ctx.doc.revision, expected_audio_revision: ctx.doc.audio_revision,
        require_verification: strict.checked, require_image_understanding: strict.checked,allow_diagnostic_baseline:diagnosticBaseline.checked
      }, { timeoutMs: 180000 });
      if (!current() || token !== serial) return;
      const blob = await API.getBinary(response.download_url);
      if (!current() || token !== serial) return;
      download(blob, `external-agent-${ctx.slideId}.zip`);
      status.textContent = `输入包已导出；任务 ${response.task.task_id.slice(0, 12)}。让 Agent 按包内说明返回 delivery.zip 或 result.json。`;
    });
    importButton.onclick = () => { if (!busy && current()) file.click(); };
    feedbackButton.onclick = () => {
      if (!busy && current() && feedback) download(new Blob([JSON.stringify(feedback, null, 2)],
        { type: 'application/json' }), `feedback-${feedback.task_id.slice(0, 12)}.json`);
    };
    file.onchange = () => run(async token => {
      receipt = null; result = null; feedback = null; feedbackZip=null;reference=null;takeover.disabled=true;fullFeedback.disabled=true;problems.replaceChildren(); pictures.replaceChildren(); report.textContent = '';
      deliveryReport.hidden = true; reportBody.textContent = '';
      const ctx = context(), selected = file.files[0];
      file.value = ''; // Same filename may contain a revised second-round result.
      if (!selected) return;
      let payload;
      if (/\.zip$/i.test(selected.name)) {
        if (selected.size > 4 * 1024 * 1024) throw Error('交付 ZIP 超过4MB。');
        const bytes = new Uint8Array(await selected.arrayBuffer());
        let binary = '';
        for (let start = 0; start < bytes.length; start += 32768) binary += String.fromCharCode(...bytes.subarray(start, start + 32768));
        payload = { delivery_base64: btoa(binary) };
      } else {
        if (!/\.json$/i.test(selected.name)) throw Error('请选择 result.json 或 delivery.zip。');
        if (selected.size > 512 * 1024) throw Error('结果文件超过512KB；请仅返回标准 JSON 操作。');
        payload = { result: JSON.parse((await selected.text()).replace(/^\uFEFF/, '')) };
      }
      status.textContent = '正在核对任务身份并生成修改预览；尚未保存…';
      const response = await API.post(`${base(ctx)}/preview`, payload, { timeoutMs: 180000 });
      if (!current() || token !== serial) return;
      result = response.result; feedback = response.feedback; feedbackZip=response.feedback_bundle_base64;fullFeedback.disabled=!feedbackZip;
      if(result?.status==='proposed'&&mode.value==='static_repair'&&response.result_hash){reference={task_id:result.task_id,result_hash:response.result_hash};takeover.disabled=!workbench;}
      showProblems(response);
      if (response.delivery?.report_markdown != null) {
        reportBody.textContent = response.delivery.report_markdown;
        deliveryReport.hidden = false; deliveryReport.open = true;
      }
      report.textContent = JSON.stringify({ message: response.message, changes: response.changes,
        diff: response.diff, issues: response.issues, required_inputs: response.required_inputs, review: response.review,
        validation: response.validation, acceptance: response.acceptance, external_verification: response.external_verification,
        delivery: response.delivery && { sha256: response.delivery.sha256, files: response.delivery.files },
        usage: response.usage, usage_source: response.usage_source }, null, 2);
      showComparison(response.comparison);
      receipt = response.status === 'candidate' && response.passed ? response : null;
      status.textContent = receipt ? '检查通过，尚未保存。核对差异和画面后可保存本次候选。'
        : response.validation ? `检查未通过，未保存：${response.validation.message}。可导出检查反馈交给 Agent。`
          : '结果已读取，未保存；请按报告补充资料或修正问题。';
    });
    save.onclick = () => run(async token => {
      const ctx = context(), checked = receipt;
      if (!checked || !result) throw Error('请先导入结果并通过预览。');
      status.textContent = '正在按原保护规则保存…';
      await API.post(`${base(ctx)}/save`, { result, candidate_key: checked.candidate_key,
        result_hash: checked.result_hash }, { timeoutMs: 180000 });
      receipt = null;
      if (current() && token === serial) {
        status.textContent = '已保存；当前画面、语义和输出仍按原流程验收。';
        await options.onSaved();
      }
    });
    box.addEventListener('toggle', () => {
      if (box.open && current()) {
        const ctx = options.getContext();refreshCriteria();
        scope.textContent = `当前范围：${ctx.scope.join('、') || '尚未选择对象'}。导出包含实际截图、素材、原文和风格；未保存草稿请先处理。`;
      }
    });
    return { destroy() { serial++; receipt = null; feedback = null; piAgent?.destroy();workbench?.destroy();box.remove(); } };
  }
  async function exportDesign(projectId, slideId, design, isCurrent = () => true) {
    if (!design) throw Error('请先生成当前页设计图。');
    const base = `/api/projects/${encodeURIComponent(projectId)}/html-visual/${encodeURIComponent(slideId)}/handoff`;
    const response = await API.post(`${base}/export`, { task_type: 'design_reference',
      goal: '根据权威内容、注册风格和当前设计评估还原要求，列出缺少的输入或能力；不批准或保存页面。',
      design_candidate_key: design.key, scope: [] }, { timeoutMs: 180000 });
    if (!isCurrent()) return;
    const blob = await API.getBinary(response.download_url);
    if (isCurrent()) download(blob, `external-design-${slideId}.zip`);
  }
  window.HtmlExternalHandoff = { mount, exportDesign };
})();
