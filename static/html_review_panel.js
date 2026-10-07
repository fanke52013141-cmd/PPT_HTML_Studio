// HTML 审阅/批准面板（工作区 Step 3 扩展，仅 HTML 后端项目可见）。
// 职责：按页触发计划生成、静态审阅、批准，并展示批准状态与对象级问题。
// 归属：本模块自带幂等的局部 DOM 绑定；传输与转义复用 api_client/ui_foundation。
(function initHtmlReviewPanel() {
  if (typeof window === 'undefined' || window.__htmlReviewPanelReady) return;
  window.__htmlReviewPanelReady = true;

  const MARKER = 'html-review-panel-section';

  function project() {
    return (window.PPTStudio && window.PPTStudio.runtime
      && window.PPTStudio.runtime.state.currentProject) || null;
  }

  function isHtmlProject() {
    return project()?.visual_backend === 'html';
  }

  function currentSlideId() {
    return window.PPTStudio?.runtime?.state?.currentSlideId
      || (document.querySelector('.slide-tab.active')?.dataset?.slideId)
      || '';
  }

  function ensureSection(host) {
    let section = host.querySelector(`#${MARKER}`);
    if (section) return section;
    section = document.createElement('section');
    section.id = MARKER;
    section.style.cssText = 'margin:0.75rem 0;padding:0.75rem 1rem;'
      + 'border:1px solid var(--border-color,#e4e9f1);border-radius:10px;background:#fff;';
    section.innerHTML = `
      <div style="font-weight:bold;margin-bottom:0.5rem;">HTML 场景审阅</div>
      <div style="display:flex;gap:0.6rem;flex-wrap:wrap;">
        <button type="button" data-html-plan class="secondary" style="padding:0.35rem 0.8rem;">生成计划</button>
        <button type="button" data-html-review class="secondary" style="padding:0.35rem 0.8rem;">静态审阅</button>
        <button type="button" data-html-approve class="success" style="padding:0.35rem 0.8rem;">批准本页</button>
      </div>
      <div data-html-status style="margin-top:0.5rem;font-size:0.85rem;color:var(--muted-color,#7d8ba1);white-space:pre-wrap;"></div>`;
    host.prepend(section);
    bind(section);
    return section;
  }

  function setStatus(section, text) {
    section.querySelector('[data-html-status]').textContent = text;
  }

  async function call(action, slideId, body) {
    const pid = project().id;
    const encoded = encodeURIComponent(slideId);
    const base = `/api/projects/${pid}/html-review/${encoded}`;
    if (action === 'plan') return API.post(`${base}/plan/generate`, body || {});
    if (action === 'review') return API.post(`${base}/review`, body || {});
    if (action === 'approve') return API.post(`${base}/approve`, body || {});
    throw new Error('unknown action');
  }
  function slide_id_path(slideId) {
    return encodeURIComponent(slideId);
  }

  function bind(section) {
    section.querySelector('[data-html-plan]')?.addEventListener('click', async () => {
      const slideId = currentSlideId();
      setStatus(section, '正在生成计划（使用已配置的大模型）…');
      try {
        const result = await call('plan', slideId);
        const map = result.evidence?.beat_map || {};
        setStatus(section, `计划已生成：结构 ${result.plan.structure}，`
          + `语块映射 ${Object.keys(map).length} 条；已写入生成记录（AC06/AC07）。`);
      } catch (error) {
        setStatus(section, '计划失败：' + (error?.message || error));
      }
    });
    section.querySelector('[data-html-review]')?.addEventListener('click', async () => {
      const slideId = currentSlideId();
      setStatus(section, '静态审阅中（编译 + 浏览器测量 + 截图）…');
      try {
        const result = await call('review', slideId);
        const report = result.review;
        if (report.passed) {
          setStatus(section, `审阅通过：${report.measuredObjects} 个文字对象完成容量测量；`
            + `截图 ${report.screenshot}`);
        } else {
          setStatus(section, '审阅未通过：' + (report.message || report.code)
            + '\n请按提示修正场景后重试；原已批准画面不受影响。');
        }
      } catch (error) {
        setStatus(section, '审阅失败：' + (error?.message || error));
      }
    });
    section.querySelector('[data-html-approve]')?.addEventListener('click', async () => {
      const slideId = currentSlideId();
      setStatus(section, '批准中（先自动执行静态审阅）…');
      try {
        const result = await call('approve', slideId);
        setStatus(section, `已批准：批准记录绑定场景/主题/模板/资产/运行时哈希（${result.approval.sha256.slice(0, 12)}…）。`
          + '任一相关变化会使批准自动失效。');
      } catch (error) {
        setStatus(section, '批准失败：' + (error?.message || error));
      }
    });
  }

  function refresh() {
    if (!isHtmlProject()) return;
    const panel = document.querySelector('[data-step="3"], #step-3');
    if (!panel) return;
    const section = ensureSection(panel);
    setStatus(section, '本页可先生成计划，再静态审阅，最后批准；'
      + '批准后修改场景/主题/模板/资产/运行时任意一项都会使批准失效。');
  }

  document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver(() => {
      if (isHtmlProject() && document.querySelector('[data-step="3"], #step-3')) refresh();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    refresh();
  });

  window.HtmlReviewPanel = { refresh };
})();
