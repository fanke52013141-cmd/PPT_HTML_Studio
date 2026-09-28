// Shared authenticated JSON/FormData transport for the classic frontend.
// UI error presentation remains delegated to the shared showToast contract.

const API = {
  // 请求超时（毫秒）。LLM/TTS 等长任务后端有较长超时，但前端不能无限等待，
  // 否则用户得不到失败反馈、界面卡死。超过此时间用 AbortSignal 中断请求。
  REQUEST_TIMEOUT_MS: 120000,

  async fetch(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      options.timeoutMs || this.REQUEST_TIMEOUT_MS
    );
    try {
      const method = String(options.method || 'GET').toUpperCase();
      const headers = new Headers(options.headers || {});
      if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        headers.set('X-PPT-Studio-Request', '1');
      }
      const response = await fetch(url, {
        ...options,
        headers,
        signal: options.signal || controller.signal
      });
      if (options.responseType === 'blob') {
        if (response.ok) return response.blob();
        const rawText = await response.text();
        let detail = response.statusText || '请求失败';
        let body = {};
        if (rawText) {
          try {
            const data = JSON.parse(rawText);
            detail = data.detail || data.message || detail;
            body = data;
          } catch (_) {
            detail = `HTTP ${response.status} ${detail}`;
          }
        }
        const message = typeof detail === 'string'
          ? detail
          : (detail?.message || JSON.stringify(detail));
        const blobError = new Error(message);
        blobError.status = response.status;
        blobError.body = body;
        throw blobError;
      }
      const contentType = response.headers.get('content-type') || '';
      const rawText = await response.text();
      let data = {};
      if (rawText) {
        if (contentType.includes('application/json')) {
          try {
            data = JSON.parse(rawText);
          } catch (e) {
            data = { detail: response.statusText || '请求失败' };
          }
        } else {
          // 非 JSON 响应（如 HTML 错误页）只展示状态摘要，避免把内部
          // 堆栈/路径直接展示给用户造成信息泄露。
          data = { detail: `HTTP ${response.status} ${response.statusText || '请求失败'}` };
        }
      }
      if (!response.ok) {
        const detail = data.detail || data.message || response.statusText || '请求失败';
        const message = typeof detail === 'string'
          ? detail
          : (detail?.message || JSON.stringify(detail));
        // 附加结构化上下文(状态码/响应体),供调用方做 409 等分支处理;
        // 既有消费方只读 message,保持向后兼容。
        const statusError = new Error(message);
        statusError.status = response.status;
        statusError.body = data;
        throw statusError;
      }
      return data;
    } catch (error) {
      if (error && error.name === 'AbortError') {
        if (!options.silent) {
          showToast(`❌ 请求超时（${Math.round((options.timeoutMs || this.REQUEST_TIMEOUT_MS) / 1000)}秒），请重试`);
        }
        throw new Error('请求超时');
      }
      if (!options.silent) showToast(`❌ 错误: ${error.message}`);
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  async get(url, extra = {}) {
    return this.fetch(url, extra);
  },

  // [配置包压缩包 20260908] 下载二进制资源（如 ZIP 配置包），返回 Blob。
  async getBinary(url) {
    return this.fetch(url, { responseType: 'blob' });
  },

  // Binary POST response for protected configuration exports.  The request
  // still goes through the shared marker/timeout/error contract above.
  async postBinary(url, body, extra = {}) {
    return this.fetch(url, {
      method: 'POST',
      body: JSON.stringify(body || {}),
      headers: { 'Content-Type': 'application/json' },
      responseType: 'blob',
      ...extra
    });
  },

  async post(url, body, extra = {}) {
    const isFormData = body instanceof FormData;
    // [配置包压缩包 20260908] ArrayBuffer/Blob 按原始字节上传（ZIP 配置包导入）。
    const isRawBody = body instanceof ArrayBuffer || body instanceof Blob;
    return this.fetch(url, {
      method: 'POST',
      body: isRawBody ? body : (isFormData ? body : JSON.stringify(body)),
      headers: isFormData
        ? {}
        : { 'Content-Type': isRawBody ? 'application/octet-stream' : 'application/json' },
      ...extra
    });
  },

  async put(url, body, extra = {}) {
    return this.fetch(url, {
      method: 'PUT',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
      ...extra
    });
  },

  async patch(url, body, extra = {}) {
    return this.fetch(url, {
      method: 'PATCH',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
      ...extra
    });
  },

  async delete(url, body = null) {
    return this.fetch(url, body === null
      ? { method: 'DELETE' }
      : { method: 'DELETE', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } });
  }
};

window.API = API;
