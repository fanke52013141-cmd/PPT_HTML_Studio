import assert from 'node:assert/strict';
export async function verifyAudioFreshness(tab) {
  const ui = tab.playwright;
  const observe = () => tab.getAXState({ emit: false });
  const status = text => ui.locator('[data-editor-status]').filter({ hasText: text }).waitFor({ state: 'visible' });
  async function click(name) { await ui.getByRole('button', { name, exact: true }).click(); await observe(); }
  async function server() {
    await click('读取服务端场景');
    await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
    return JSON.parse(await ui.locator('#fixture-result').textContent());
  }
  await status('修订');
  const before = await server(), oldSrc = await ui.locator('audio').getAttribute('src');
  const action = ui.locator('[data-timeline-action="fixture-action-0"]');
  await action.click(); await observe();
  const rect = await action.evaluate(el => el.parentElement.getBoundingClientRect().toJSON());
  const from = [rect.x + rect.width / 2, rect.y + rect.height / 2];
  await tab.drag(from, [from[0] + 24, from[1]]); await observe(); await status('动作修改已校验');
  await click('替换同长测试配音');
  await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
  await click('重播');
  await ui.locator('[data-timeline-status]').filter({ hasText: '变化' }).waitFor({ state: 'visible' });
  assert.equal(await ui.locator('audio').getAttribute('src'), null);
  assert.equal(await ui.locator('.timeline-editor-action-movable').count(), 0);
  await click('保存修改'); await status('配音产物已变化');
  assert.equal((await server()).revision, before.revision);
  await click('刷新配音与时序'); await status('配音与时序已刷新');
  const src = await ui.locator('audio').getAttribute('src'); assert(src && src !== oldSrc);
  await click('保存修改'); await status('已保存');
  const saved = await server();
  const expectedOffset = before.binding.actions['fixture-action-0'].offsetMs + 300;
  assert.equal(saved.binding.actions['fixture-action-0'].offsetMs, expectedOffset);
  assert.equal(saved.motion[0].durationMs, before.motion[0].durationMs);
  assert.equal(JSON.stringify(saved.binding.sourceBeats), JSON.stringify(before.binding.sourceBeats));
  assert.notEqual(saved.audio_revision, before.audio_revision);
  await click('保存修改'); await status('内容未变化'); assert.equal((await server()).revision, saved.revision);
  return { passed: true, syntheticReplacement: true, sameDurationReplacement: true,
    dirtyDraftPreserved: true, stalePlayStopped: true, staleSaveRejected: true, noOpRevision: saved.revision,
    originalOffsetMs: before.binding.actions['fixture-action-0'].offsetMs, savedOffsetMs: expectedOffset };
}

export async function verifyExistingNarration(tab) {
  const ui = tab.playwright, observe = () => tab.getAXState({ emit: false });
  const status = text => ui.locator('[data-editor-status]').filter({ hasText: text }).waitFor({ state: 'visible' });
  async function click(name) { await ui.getByRole('button', { name, exact: true }).click(); await observe(); }
  async function server() {
    await click('读取服务端场景');
    await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
    return JSON.parse(await ui.locator('#fixture-result').textContent());
  }
  await status('修订'); const before = await server();
  const mediaDurationSec = await ui.locator('audio').evaluate(el => el.duration);
  assert(mediaDurationSec > 19 && mediaDurationSec < 20);
  const id = 'header:enter', span = ui.locator(`[data-timeline-action="${id}"]`);
  await span.click(); await observe();
  const box = await span.evaluate(el => el.parentElement.getBoundingClientRect().toJSON());
  await tab.drag([box.x+box.width/2, box.y+box.height/2], [box.x+box.width/2+24, box.y+box.height/2]);
  await observe(); await status('动作修改已校验');
  await click('保存修改'); await status('已保存');
  const saved = await server();
  assert.equal(saved.binding.actions[id].offsetMs, before.binding.actions[id].offsetMs + 300);
  assert.equal(saved.binding.actions[id].beatId, before.binding.actions[id].beatId);
  assert.equal(saved.motion[0].durationMs, before.motion[0].durationMs);
  for (const ms of [0, 1000, 5500, 12000, 19000]) {
    const input = ui.getByRole('spinbutton', { name: '跳转毫秒', exact: true });
    await input.fill(String(ms)); await input.press('Tab'); await observe();
    assert(Math.abs(await ui.locator('audio').evaluate(el => el.currentTime * 1000) - ms) < 2);
    assert(Math.abs(Number((await ui.frameLocator('iframe').locator('#time').textContent()).replace(' s', '')) * 1000 - ms) < 2);
  }
  await click('重播'); assert.equal(await ui.locator('audio').evaluate(el => el.paused), false);
  await click('播放 / 暂停'); assert.equal(await ui.locator('audio').evaluate(el => el.paused), true);
  await click('刷新配音与时序'); await status('配音与时序已刷新');
  await click('重开编辑器');
  await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
  assert.equal((await server()).binding.actions[id].offsetMs, saved.binding.actions[id].offsetMs);
  return { passed: true, existingNarration: true, isolatedCopy: true, newTTS: false, mediaDurationSec,
    seekTimesMs: [0,1000,5500,12000,19000], offsetDeltaMs: 300, authoredDurationPreserved: true, savedRevision: saved.revision };
}

export async function verifyRetimingRefresh(tab) {
  const ui = tab.playwright, observe = () => tab.getAXState({ emit: false });
  async function click(name) { await ui.getByRole('button', { name, exact: true }).click(); await observe(); }
  async function read() {
    await click('读取服务端场景');
    await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
    return JSON.parse(await ui.locator('#fixture-result').textContent());
  }
  await ui.locator('.html-scene-editor:not([inert])').waitFor({ state: 'visible' });
  const before = await read(), duration = await ui.locator('audio').evaluate(el => el.duration);
  const beat = ui.locator('[data-timeline-action="beat:b2"]');
  const previousLeft = await beat.evaluate(el => Number(el.parentElement.dataset.left));
  await click('模拟配音时序变化');
  await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
  await click('刷新配音与时序');
  await ui.locator('[data-editor-status]').filter({ hasText: '配音与时序已刷新' }).waitFor({ state: 'visible' });
  const currentLeft = await beat.evaluate(el => Number(el.parentElement.dataset.left));
  assert(Math.abs((currentLeft - 20) - (previousLeft - 20) * 1.25) < 1);
  const after = await read(); assert.equal(after.revision, before.revision);
  assert.equal(JSON.stringify(after.binding), JSON.stringify(before.binding));
  assert.equal(JSON.stringify(after.motion), JSON.stringify(before.motion));
  assert(Math.abs(await ui.locator('audio').evaluate(el => el.duration) - duration * 1.25) < 0.01);
  await click('保存修改');
  await ui.locator('[data-editor-status]').filter({ hasText: '内容未变化' }).waitFor({ state: 'visible' });
  assert.equal((await read()).revision, before.revision);
  return { passed: true, syntheticRetiming: true, factor: 1.25, relativeBindingPreserved: true,
    authorMotionPreserved: true, noSceneRevisionChange: true, previousBeatLeft: previousLeft, currentBeatLeft: currentLeft };
}
