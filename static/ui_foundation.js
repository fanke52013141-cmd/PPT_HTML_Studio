// Shared UI primitives and cross-step text/input helpers.

function getToastPresentation(message) {
  const rawMessage = String(message ?? '').trim();
  const text = rawMessage
    .replace(/^(?:[\p{Extended_Pictographic}\uFE0F\u200D]+\s*)+/u, '')
    .trim();

  let tone = 'info';
  if (/^(?:❌|⛔|🚫)/u.test(rawMessage)
      || /(失败|错误|异常|被拒绝|中断|超时|无法|未能|未通过|不可用|无效|缺少|不能为空|请先|请填写|请至少|超过.{0,12}限制|HTTP\s*[45]\d\d)/i.test(rawMessage)) {
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
  if (presentation.tone !== 'error') return null;
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

function showCustomConfirm(title, message, onYes, onNo = null) {
  const modal = document.getElementById('modal-confirm');
  document.getElementById('confirm-title').innerText = title;
  document.getElementById('confirm-message').innerText = message;

  const btnYes = document.getElementById('btn-confirm-yes');
  const btnNo = document.getElementById('btn-confirm-no');

  // Clone controls so each confirmation owns exactly one callback pair.
  const newYes = btnYes.cloneNode(true);
  const newNo = btnNo.cloneNode(true);
  btnYes.parentNode.replaceChild(newYes, btnYes);
  btnNo.parentNode.replaceChild(newNo, btnNo);

  modal.style.display = 'flex';

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
