// Shared UI primitives and cross-step text/input helpers.

function getToastPresentation(message) {
  const rawMessage = String(message ?? '').trim();
  const text = rawMessage
    .replace(/^(?:[\p{Extended_Pictographic}\uFE0F\u200D]+\s*)+/u, '')
    .trim();

  let tone = 'info';
  // 只有真实失败/报错才允许进入通知容器：请求错误、保存/生成/渲染失败、
  // 超时中断、服务端拒绝等。输入引导与校验提示（请先/请填写/不能为空等）
  // 属于预期交互，就地呈现即可，全局弹出会让用户误以为不断出错。
  if (/^(?:❌|⛔|🚫)/u.test(rawMessage)
      || /(失败|错误|异常|被拒绝|中断|超时|无法|未能|不可用|无效|HTTP\s*[45]\d\d)/i.test(rawMessage)) {
    tone = 'error';
  } else if (/^(?:⚠️?|❗)/u.test(rawMessage)) {
    tone = 'warning';
  } else if (/^(?:✅|🎉|✨)/u.test(rawMessage) || /(成功|已生成|已保存|已确认|已完成|已删除|已应用|已启动)/.test(rawMessage)) {
    tone = 'success';
  }

  return { text: text || '操作已完成', tone };
}

const TOAST_ERROR_COOLDOWN_MS = 60_000;
const recentErrorToasts = new Map();

function showToast(message, duration = 1800) {
  const presentation = getToastPresentation(message);
  if (presentation.tone !== 'error') {
    if (presentation.tone !== 'success' && /(请先|请输入|请填写|请选择|请至少|不能为空|缺少|未通过|暂无|没有可|尚未|至少保留|范围太小|笔迹太短|选区太小)/.test(presentation.text)) {
      showInlineNotice(presentation.text);
    }
    return null;
  }
  const container = document.getElementById('toast-container');
  if (!container) return null;
  const toastKey = presentation.text;
  const now = Date.now();
  for (const [key, shownAt] of recentErrorToasts) {
    if (now - shownAt >= TOAST_ERROR_COOLDOWN_MS) recentErrorToasts.delete(key);
  }
  if (recentErrorToasts.has(toastKey)) return null;
  const duplicate = Array.from(container.children).find(item => item.dataset.toastKey === toastKey);
  if (duplicate) return duplicate;
  recentErrorToasts.set(toastKey, now);
  while (container.children.length >= 1) {
    container.firstElementChild?.remove();
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${presentation.tone}`;
  toast.dataset.toastKey = toastKey;
  toast.setAttribute('role', 'alert');
  const content = document.createElement('div');
  content.className = 'toast-content';
  content.textContent = presentation.text;
  toast.appendChild(content);
  container.appendChild(toast);
  // 失败通知短暂显示；点击可复制完整报错。
  toast.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(String(message ?? '')); } catch (_) {}
  });
  const visibleDuration = Math.max(4500, Number(duration) || 4500);
  setTimeout(() => {
    toast.style.animation = 'slideUp 0.3s ease-in reverse';
    setTimeout(() => toast.remove(), 300);
  }, visibleDuration);
}

// Compatibility for legacy validation callers: keep guidance beside the
// current interaction while genuine failures retain the global Toast policy.
function showInlineNotice(message) {
  if (!document.querySelectorAll) return;
  const modal = [...document.querySelectorAll('.modal-overlay')].filter(node => node.getClientRects().length).at(-1);
  const scope = modal?.querySelector('.modal-content') || modal
    || [...document.querySelectorAll('.step-panel')].find(node => node.getClientRects().length)
    || document.getElementById('page-home');
  if (!scope) return;
  let notice = scope.querySelector('.inline-validation-notice');
  if (!notice) {
    notice = document.createElement('p');
    notice.className = 'inline-validation-notice workspace-operation-status';
    notice.setAttribute('role', 'status');
    const header = scope.querySelector('.workflow-header, h2, h3');
    if (header) header.insertAdjacentElement('afterend', notice);
    else scope.prepend(notice);
  }
  notice.textContent = message;
  notice.hidden = false;
  notice.scrollIntoView({ block: 'nearest' });
}

function presentCustomConfirm(title, message, onYes, onNo = null, labels = {}) {
  const modal = document.getElementById('modal-confirm');
  modal.returnFocus = document.activeElement;
  document.getElementById('confirm-title').innerText = title;
  document.getElementById('confirm-message').innerText = message;

  const btnYes = document.getElementById('btn-confirm-yes');
  const btnNo = document.getElementById('btn-confirm-no');

  // Clone controls so each confirmation owns exactly one callback pair.
  const newYes = btnYes.cloneNode(true);
  const newNo = btnNo.cloneNode(true);
  newYes.disabled = false;
  newNo.disabled = false;
  newYes.textContent = labels.confirm || '确认';
  newNo.textContent = labels.cancel || '取消';
  btnYes.parentNode.replaceChild(newYes, btnYes);
  btnNo.parentNode.replaceChild(newNo, btnNo);

  modal.style.display = 'flex';
  newNo.focus();

  newYes.addEventListener('click', async () => {
    modal.style.display = 'none';
    newYes.disabled = true;
    newNo.disabled = true;
    try {
      if (onYes) await onYes();
    } catch (error) {
      showToast(`操作失败：${error.message}`, 6000);
    } finally {
      newYes.disabled = false;
      newNo.disabled = false;
    }
  });

  newNo.addEventListener('click', () => {
    modal.style.display = 'none';
    if (onNo) onNo();
  });
}

// Promise callers queue their dialogs so one operation cannot replace another's decision.
let confirmationQueue = Promise.resolve();
function showCustomConfirm(title, message, onYes, onNo = null, labels = {}) {
  const result = confirmationQueue.then(() => new Promise(resolve => {
    presentCustomConfirm(title, message, () => {
      resolve(true);
      return onYes?.();
    }, () => {
      resolve(false);
      return onNo?.();
    }, labels);
  }));
  confirmationQueue = result.catch(() => false);
  return result;
}

function confirmAction(title, message, labels = {}) {
  return showCustomConfirm(title, message, null, null, labels);
}

function requestTextInput(title, label, initialValue = '') {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.display = 'flex';
    const panel = document.createElement('div');
    panel.className = 'modal-content';
    const heading = document.createElement('h3');
    heading.textContent = title;
    const field = document.createElement('label');
    field.textContent = label;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = initialValue;
    input.required = true;
    field.appendChild(input);
    const error = document.createElement('p');
    error.className = 'field-error';
    error.setAttribute('role', 'status');
    const actions = document.createElement('div');
    actions.className = 'config-editor-actions';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'secondary';
    cancel.textContent = '取消';
    const submit = document.createElement('button');
    submit.type = 'button';
    submit.className = 'success';
    submit.textContent = '保存';
    const finish = value => { overlay.remove(); resolve(value); };
    cancel.addEventListener('click', () => finish(null));
    submit.addEventListener('click', () => {
      if (!input.value.trim()) {
        error.textContent = '名称不能为空';
        input.setAttribute('aria-invalid', 'true');
        input.focus();
        return;
      }
      finish(input.value.trim());
    });
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); submit.click(); }
    });
    actions.append(cancel, submit);
    panel.append(heading, field, error, actions);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
  });
}

function setDisabledReason(button, disabled, reason = '') {
  if (!button) return;
  button.disabled = disabled;
  const id = `hint-${button.id}`;
  let hint = document.getElementById(id);
  if (!hint && button.id && reason) {
    hint = document.createElement('span');
    hint.id = id;
    hint.className = 'control-hint';
    button.insertAdjacentElement('afterend', hint);
  }
  if (hint) {
    const text = disabled ? reason : '';
    if (hint.textContent !== text) hint.textContent = text;
    hint.hidden = !text;
    const ids = (button.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean).filter(value => value !== id);
    if (text) ids.push(id);
    if (ids.length) button.setAttribute('aria-describedby', ids.join(' '));
    else button.removeAttribute('aria-describedby');
  }
  button.removeAttribute('title');
}

function clearFieldError(field) {
  if (!field) return;
  const errorId = field.dataset.errorId;
  if (errorId) document.getElementById(errorId)?.remove();
  const ids = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== errorId);
  if (ids.length) field.setAttribute('aria-describedby', ids.join(' '));
  else field.removeAttribute('aria-describedby');
  field.removeAttribute('aria-invalid');
  delete field.dataset.errorId;
}

let fieldErrorSequence = 0;
function showFieldError(field, message) {
  if (!field) return;
  clearFieldError(field);
  const error = document.createElement('p');
  error.id = `field-error-${++fieldErrorSequence}`;
  error.className = 'field-error';
  error.textContent = message;
  error.setAttribute('role', 'status');
  field.insertAdjacentElement('afterend', error);
  field.dataset.errorId = error.id;
  field.setAttribute('aria-invalid', 'true');
  field.setAttribute('aria-describedby', `${field.getAttribute('aria-describedby') || ''} ${error.id}`.trim());
  field.scrollIntoView({ block: 'nearest' });
  field.focus();
}

// Legacy modules still open dialogs with style.display. Observe that lifecycle,
// and close through their existing buttons so drafts and cleanup callbacks survive.
function initModalAccessibility() {
  if (initModalAccessibility.started) return;
  initModalAccessibility.started = true;
  const stack = [];
  const inertBefore = new Map();
  const visible = node => node.isConnected && !node.hidden && getComputedStyle(node).display !== 'none';
  const controls = modal => [...modal.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')]
    .filter(node => !node.disabled && node.tabIndex >= 0 && node.getClientRects().length && !node.closest('[inert]'));
  const closeControl = modal => modal.querySelector('#btn-confirm-no') || [...modal.querySelectorAll('button')]
    .find(button => !button.disabled && (/^(取消|关闭|返回)$/.test(button.textContent.trim()) || /(?:close|cancel)/.test(button.id)));
  function sync() {
    let restore = null;
    for (let i = stack.length - 1; i >= 0; i--) {
      if (!visible(stack[i].modal)) {
        restore = stack[i].opener;
        stack.splice(i, 1);
      }
    }
    for (const modal of document.querySelectorAll('.modal-overlay')) {
      if (!visible(modal) || stack.some(entry => entry.modal === modal)) continue;
      const panel = modal.querySelector('.modal-content') || modal;
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      if (!panel.hasAttribute('aria-labelledby') && !panel.hasAttribute('aria-label')) {
        panel.setAttribute('aria-label', panel.querySelector('h2,h3,h4')?.textContent.trim() || '操作对话框');
      }
      panel.tabIndex = -1;
      stack.push({ modal, opener: modal.returnFocus || document.activeElement, panel });
      delete modal.returnFocus;
    }
    // Restore previous inert values before applying the current top dialog.
    for (const [node, value] of inertBefore) node.inert = value;
    inertBefore.clear();
    const top = stack.at(-1);
    if (top) {
      let branch = top.modal;
      while (branch && branch !== document.body) {
        for (const node of branch.parentElement?.children || []) {
          if (node === branch || ['SCRIPT', 'STYLE'].includes(node.tagName)) continue;
          inertBefore.set(node, node.inert);
          node.inert = true;
        }
        branch = branch.parentElement;
      }
      if (!top.modal.contains(document.activeElement)) {
        (top.modal.id === 'modal-confirm' ? closeControl(top.modal) : controls(top.modal)[0] || top.panel)?.focus();
      }
    } else if (restore?.isConnected && !restore.closest('[inert]')) restore.focus();
  }
  const observer = new MutationObserver(records => {
    if (records.some(record => record.type === 'childList'
      || record.target.matches?.('.modal-overlay'))) sync();
  });
  observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['style', 'hidden', 'class'] });
  document.addEventListener('keydown', event => {
    const top = stack.at(-1);
    if (!top) return;
    if (event.key === 'Escape') {
      const close = closeControl(top.modal);
      if (close) { event.preventDefault(); event.stopImmediatePropagation(); close.click(); }
    } else if (event.key === 'Tab') {
      const items = controls(top.modal);
      const index = items.indexOf(document.activeElement);
      if (!items.length) { event.preventDefault(); top.panel.focus(); }
      else if (event.shiftKey && index <= 0) { event.preventDefault(); items.at(-1).focus(); }
      else if (!event.shiftKey && (index < 0 || index === items.length - 1)) { event.preventDefault(); items[0].focus(); }
    }
  }, true);
  document.addEventListener('focusin', event => {
    const top = stack.at(-1);
    if (top && !top.modal.contains(event.target)) (controls(top.modal)[0] || top.panel).focus();
  });
  document.addEventListener('input', event => {
    clearFieldError(event.target);
    const scope = event.target.closest?.('.modal-content, .step-panel');
    const notice = scope?.querySelector('.inline-validation-notice');
    if (notice) notice.hidden = true;
  });
  sync();
}

function escHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function narrationDedupeKey(text) {
  return String(text || '')
    .replace(/<#\d+(?:\.\d{1,2})?#>|\([A-Za-z-]+\)/g, '')
    .toLocaleLowerCase()
    .replace(/[\s\p{P}\p{S}_]+/gu, '');
}

function autoResizeTextarea(textarea) {
  if (!textarea) return;
  if (textarea.tagName === 'TEXTAREA') textarea.rows = 1;
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight + 2}px`;
}
