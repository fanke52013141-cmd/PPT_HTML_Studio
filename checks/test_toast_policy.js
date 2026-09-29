const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'static', 'ui_foundation.js'), 'utf8');
let now = 0;
const children = [];
const container = {
  children,
  get firstElementChild() { return children[0]; },
  appendChild(item) { children.push(item); },
};
const sandbox = {
  Date: { now: () => now },
  document: {
    getElementById: id => id === 'toast-container' ? container : null,
    createElement: () => ({
      dataset: {},
      style: {},
      appendChild(item) { this.child = item; },
      setAttribute() {},
      addEventListener() {},
      remove() {
        const index = children.indexOf(this);
        if (index >= 0) children.splice(index, 1);
      },
    }),
  },
  setTimeout() {},
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: 'ui_foundation.js' });

// 引导/校验/进度类消息一律静默：它们是预期交互，不是故障信号。
const silentMessages = [
  '生成已完成',
  '⚠️ 正在排队，请等待',
  '暂无可下载内容',
  '请先填写模型',
  '请先选择一个项目',
  '项目名称不能为空',
  '第 2 页标题不能为空',
  '分镜结构尚未通过校验，请检查当前页内容',
  '请先添加至少一个分镜，再进入图片生成。',
  '请填写接口密钥 (API Key)',
  '第 3 页缺少生图提示词，请先重新进入本步骤。',
  '图片生成 System Content 不能为空',
  '⚠️ 请至少添加一页幻灯片',
];
for (const message of silentMessages) {
  assert.equal(sandbox.showToast(message), null, message);
  assert.notEqual(sandbox.getToastPresentation(message).tone, 'error', message);
}
assert.equal(children.length, 0, 'guidance messages must never reach the toast container');

// 只有真实失败/报错才弹出。
const errorMessages = [
  '❌ 图片上传失败',
  '保存失败：网络中断',
  '❌ 错误: 服务器内部错误',
  '渲染失败: Remotion 进程退出',
  '音频生成失败：凭据无效',
  '字幕无法导出：请求超时',
  '保存被拒绝: 分镜版本冲突',
];
for (const message of errorMessages) {
  now += 61_000;
  children.length = 0;
  sandbox.showToast(message);
  assert.equal(children.length, 1, message);
  assert.equal(children[0].className, 'toast toast-error', message);
}

// 同一错误 60 秒内不重复弹出。
children.length = 0;
sandbox.showToast('❌ 图片上传失败');
assert.equal(children.length, 1);
assert.equal(children[0].className, 'toast toast-error');
sandbox.showToast('❌ 图片上传失败');
assert.equal(children.length, 1);
children[0].remove();
now += 30_000;
assert.equal(sandbox.showToast('❌ 图片上传失败'), null, 'expired DOM alone must not re-alert');
assert.equal(children.length, 0);
now += 31_000;
sandbox.showToast('❌ 图片上传失败');
assert.equal(children.length, 1);

console.log('error-only toast policy checks passed');
