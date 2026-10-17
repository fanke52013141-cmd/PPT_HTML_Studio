// Actual UI-only regression, executed via a documented cua Tab on a fresh
// --presentation fixture. Synthetic silent audio is not real-provider evidence.
import assert from 'node:assert/strict';
export async function* verifyEditorTimelineSteps(tab) {
  const ui = tab.playwright, checks = [];
  const observe = () => tab.getAXState({ emit: false });
  const status = text => ui.locator('[data-editor-status]').filter({ hasText: text }).waitFor({ state: 'visible' });
  async function click(name) { await ui.getByRole('button', { name, exact: true }).click(); await observe(); }
  async function server() {
    await click('读取服务端场景');
    await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
    return JSON.parse(await ui.locator('#fixture-result').textContent());
  }
  async function gesture(id, dx, handle = null) {
    const span = ui.locator(`[data-timeline-action="${id}"]`);
    await span.click(); await observe();
    const rect = await (handle ? ui.locator(`.timeline-editor-action:has([data-timeline-action="${id}"]) ${handle}`) : span)
      .evaluate(el => (el.classList.contains('timeline-editor-action-right-stretch') || el.classList.contains('timeline-editor-action-left-stretch') ? el : el.parentElement).getBoundingClientRect().toJSON());
    const from = [rect.x + rect.width / 2, rect.y + rect.height / 2];
    await tab.drag(from, [from[0] + dx, from[1]]); await observe();
  }
  await status('修订');
  await ui.locator('[data-timeline-status]').filter({ hasText: '配音驱动' }).waitFor({ state: 'visible' });
  const before = await server();
  assert.equal(await ui.locator('audio').evaluate(el => el.duration), 18);
  assert(await ui.locator('[data-timeline-action="beat:b1"]').count());
  await gesture('fixture-action-0', 24); await status('动作修改已校验');
  await click('保存修改'); await status('已保存');
  const moved = await server();
  assert.equal(moved.binding.actions['fixture-action-0'].offsetMs, 300);
  assert.equal(moved.motion[0].durationMs, before.motion[0].durationMs);
  assert.equal(moved.binding.actions['fixture-action-0'].beatId, before.binding.actions['fixture-action-0'].beatId);
  checks.push('move 0.3s changes only original beat offset and preserves authored duration');
  yield { phase: 'move/save', checks: [...checks] };

  await gesture('fixture-action-0', 16, '.timeline-editor-action-right-stretch'); await status('动作修改已校验');
  await click('撤销'); await status('会话编辑已恢复');
  assert((await ui.locator('[data-timeline-action="fixture-action-0"]').getAttribute('title')).includes('作者 800ms'));
  await click('重做'); await status('会话编辑已恢复');
  await click('保存修改'); await status('已保存');
  const resized = await server(); assert.equal(resized.motion[0].durationMs, 1000);
  assert.equal(resized.binding.actions['fixture-action-0'].offsetMs, 300);
  assert.equal(JSON.stringify(resized.binding.sourceBeats), JSON.stringify(before.binding.sourceBeats));
  checks.push('right resize, one undo/redo, save and original source hashes preserved');
  await gesture('fixture-action-0', 16, '.timeline-editor-action-left-stretch'); await status('动作修改已校验');
  assert((await ui.locator('[data-timeline-action="fixture-action-0"]').getAttribute('title')).includes('作者 800ms'));
  await click('撤销'); await status('会话编辑已恢复');
  assert((await ui.locator('[data-timeline-action="fixture-action-0"]').getAttribute('title')).includes('作者 1000ms'));
  checks.push('left resize changes duration/offset together and one undo restores both');
  yield { phase: 'resize/history', checks: [...checks] };

  // 6s would move the bound action outside b1; original author data stays intact.
  await gesture('fixture-action-0', 480); await status('动作修改未应用');
  await click('保存修改'); await status('内容未变化');
  assert.equal((await server()).revision, resized.revision);
  checks.push('cross-beat gesture rejects and same-value save keeps revision');
  await click('重开编辑器');
  await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
  await status('修订');
  assert((await ui.locator('[data-timeline-action="fixture-action-0"]').getAttribute('title')).includes('作者 1000ms'));
  for (const ms of [4300, 500, 17000, 0]) {
    await ui.getByRole('spinbutton', { name: '跳转毫秒', exact: true }).fill(String(ms));
    await ui.getByRole('spinbutton', { name: '跳转毫秒', exact: true }).press('Tab'); await observe();
    const audioMs = await ui.locator('audio').evaluate(el => el.currentTime * 1000);
    assert(Math.abs(audioMs - ms) < 2);
    assert(Math.abs(Number((await ui.frameLocator('iframe').locator('#time').textContent()).replace(' s', '')) * 1000 - ms) < 2);
  }
  await click('重播');
  assert.equal(await ui.locator('audio').evaluate(el => el.paused), false);
  await click('播放 / 暂停');
  assert.equal(await ui.locator('audio').evaluate(el => el.paused), true);
  checks.push('reopen retains edits; seek/play/pause use the real audio element');
  yield { passed: true, realBrowser: true, syntheticAudio: true, realProvider: false, checks, revision: resized.revision };
}

export async function verifyNoAudioTimeline(tab) {
  const ui = tab.playwright;
  await ui.locator('[data-timeline-status]').filter({ hasText: '无有效配音' }).waitFor({ state: 'visible' });
  assert.equal(await ui.locator('.timeline-editor-action-movable').count(), 0);
  assert.equal(await ui.locator('.timeline-editor-action-flexible').count(), 0);
  assert.equal(await ui.locator('audio').getAttribute('src'), null);
  await ui.getByRole('button', { name: '重播', exact: true }).click(); await tab.getAXState({ emit: false });
  assert.equal(await ui.frameLocator('iframe').locator('#play').textContent(), '暂停');
  await ui.getByRole('button', { name: '播放 / 暂停', exact: true }).click(); await tab.getAXState({ emit: false });
  assert.equal(await ui.frameLocator('iframe').locator('#play').textContent(), '播放');
  return { passed: true, syntheticFixture: true, noAudioReadOnly: true, authorPlayerUsed: true };
}

export async function verifyTimelineCursor(tab) {
  const ui = tab.playwright;
  await ui.locator('.timeline-editor-time-unit-scale').filter({ hasText: /^2$/ }).click();
  await tab.getAXState({ emit: false });
  const clicked = await ui.locator('audio').evaluate(el => el.currentTime * 1000);
  assert(Math.abs(clicked - 2000) < 12);
  const box = await ui.locator('.timeline-editor-cursor-top').evaluate(el => el.getBoundingClientRect().toJSON());
  await tab.drag([box.x + box.width / 2, box.y + 6], [box.x + box.width / 2 + 40, box.y + 6]);
  await tab.getAXState({ emit: false });
  const dragged = await ui.locator('audio').evaluate(el => el.currentTime * 1000);
  assert(Math.abs(dragged - clicked - 500) < 12);
  return { passed: true, clickedMs: clicked, draggedMs: dragged };
}
