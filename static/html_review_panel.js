// HTML workspace review panel. Explicit lifecycle events; no body observer.
(function initHtmlReviewPanel() {
  if (window.__htmlReviewPanelReady) return;
  window.__htmlReviewPanelReady = true;
  let generation = 0;
  let activeTask = null;
  let designCandidate = null;
  let acceptedDesignKey = null;
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
  function refresh() {
    const host = document.getElementById('step-panel-3');
    if (!host) return;
    const {project, slideId} = context();
    const mode = project?.visual_backend === "html" ? "true" : "false";
    if (host.dataset.htmlMode !== mode) host.dataset.htmlMode = mode;
    let section = host.querySelector('#html-review-panel-section');
    if (project?.visual_backend !== 'html') {
      if (section && !section.hidden) {generation++; activeTask=null; designCandidate=null; acceptedDesignKey=null;}
      if (section) section.hidden = true;
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
        <div data-html-status role="status"></div>
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
        <div data-html-models hidden></div>`;
      const sheetHost = document.createElement('div'); sheetHost.dataset.htmlSheets = ''; sheetHost.hidden = true; section.append(sheetHost);
      host.prepend(section);
      section.querySelector('[data-html-slide]').addEventListener('change', event => {
        window.PPTStudio.runtime.state.activeSlideIndex = Number(event.target.value);
        refresh();
      });
      section.addEventListener('click', async event => {
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
          let payload = {};
          if (action === 'accept-design') {
            if (!designCandidate || designCandidate.stale) throw new Error('请先生成并审阅当前设计。');
            payload = {design_candidate_key: designCandidate.key}; action = 'produce';
          } else if (action === 'revise-design') {
            const instruction = section.querySelector('[data-design-instruction]').value.trim();
            if (!instruction) throw new Error('请填写本轮设计修改方向。');
            payload = {design_instruction: instruction}; action = 'produce';
          } else if (action === 'retry-asset') {
            const instruction = section.querySelector('[data-asset-instruction]').value.trim();
            if (!acceptedDesignKey || !instruction) throw new Error('请填写主体素材修改方向，并确认当前设计仍有效。');
            payload = {design_candidate_key: acceptedDesignKey, asset_instruction: instruction}; action = 'produce';
          }
          let result = await API.post(`${base}/${action}`, payload);
          if (result.task) {
            let task = result.task;
            activeTask = {id:task.id,project:current.project.id,slide:current.slideId};
            section.querySelector('[data-action="cancel"]').hidden=false;
            while (task.status === 'queued' || task.status === 'running') {
              await new Promise(resolve => setTimeout(resolve, 700));
              if (token !== generation) return;
              task = (await API.get(`/api/projects/${encodeURIComponent(current.project.id)}/html-review/tasks/${encodeURIComponent(task.id)}`)).task;
            }
            if (task.status !== 'succeeded') throw new Error(task.error || `任务${task.status}`);
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
      generation++;
      designCandidate = null;
      showAssetRetry(section, null);
      showDesign(section, null, '');
      section.querySelector('[data-design-instruction]').value = '';
      section.querySelector('[data-asset-instruction]').value = '';
      section.querySelectorAll('button').forEach(b=>b.disabled=false);
      section.dataset.context = key;
      section.querySelector('[data-action="cancel"]').hidden=true;
      status(section, slideId ? '先生成设计参考，确认后生成实际页面，再审阅批准。' : '请先选择分镜页面。');
      section.querySelector('[data-html-preview]').hidden = true;
      if (slideId) {
        const token = generation;
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
