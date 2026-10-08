// HTML workspace review panel. Explicit lifecycle events; no body observer.
(function initHtmlReviewPanel() {
  if (window.__htmlReviewPanelReady) return;
  window.__htmlReviewPanelReady = true;
  let generation = 0;
  let activeTask = null;
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
      if (section) section.hidden = true;
      window.HtmlSceneEditor?.close();
      return;
    }
    if (!section) {
      section = document.createElement('section');
      section.id = 'html-review-panel-section';
      section.className = "card soft-outline";
      section.innerHTML = `<style>#step-panel-3[data-html-mode="true"] .step3-toolbar-row,#step-panel-3[data-html-mode="true"] #step3-images-grid{display:none!important}</style><h3>HTML 场景生产与审阅</h3>
        <label>分镜页面 <select data-html-slide></select></label>
        <button class="success" type="button" data-action="produce">生成场景</button>
        <button type="button" data-action="review">静态审阅</button>
        <button class="success" type="button" data-action="approve">批准本页</button>
        <button type="button" data-action="edit">编辑对象与动作</button>
        <button type="button" data-action="cancel" hidden>停止生产任务</button>
        <div data-html-status role="status"></div>
        <img data-html-preview alt="当前场景的实际渲染" hidden style="max-width:100%">
        <div data-html-editor></div>`;
      host.prepend(section);
      section.querySelector('[data-html-slide]').addEventListener('change', event => {
        window.PPTStudio.runtime.state.activeSlideIndex = Number(event.target.value);
        refresh();
      });
      section.addEventListener('click', async event => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
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
          let result = await API.post(`${base}/${button.dataset.action}`, {});
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
          if (result.review) {
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
        finally { activeTask=null; section.querySelector('[data-action="cancel"]').hidden=true; section.querySelectorAll('button').forEach(b=>b.disabled=false); }
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
      generation++;
      section.dataset.context = key;
      section.querySelector('[data-action="cancel"]').hidden=true;
      status(section, slideId ? '先生成场景，查看实际画面，再批准。' : '请先选择分镜页面。');
      section.querySelector('[data-html-preview]').hidden = true;
    }
  }
  document.addEventListener('DOMContentLoaded', refresh);
  document.addEventListener('click', () => queueMicrotask(refresh));
  document.addEventListener('ppt:workspace-changed', refresh);
  window.HtmlReviewPanel = {refresh};
})();
