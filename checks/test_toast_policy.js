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

for (const message of ['生成已完成', '⚠️ 正在排队，请等待', '暂无可下载内容']) {
  assert.equal(sandbox.showToast(message), null, message);
}
assert.equal(children.length, 0);

sandbox.showToast('❌ 图片上传失败');
assert.equal(children.length, 1);
assert.equal(children[0].className, 'toast toast-error');
sandbox.showToast('❌ 图片上传失败');
assert.equal(children.length, 1);
children[0].remove();
now = 30_000;
assert.equal(sandbox.showToast('❌ 图片上传失败'), null, 'expired DOM alone must not re-alert');
now = 61_000;
sandbox.showToast('❌ 图片上传失败');
assert.equal(children.length, 1);
sandbox.showToast('请先填写模型');
assert.equal(children.length, 1, 'a blocked action replaces the previous error');
assert.equal(children[0].child.textContent, '请先填写模型');
assert.equal(sandbox.getToastPresentation('请先填写模型').tone, 'error');
assert.equal(sandbox.getToastPresentation('⚠️ 正在生成图片，请等待').tone, 'warning');

console.log('error-only toast policy checks passed');
