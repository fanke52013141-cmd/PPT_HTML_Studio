// Run through a documented cua_repl Tab. No browser is launched and no app state
// is mutated through evaluate: all edits are actual UI input in an isolated fixture.
import assert from 'node:assert/strict';
export let lastChecks = [], lastGesture = null;

export async function* verifyEditorLayoutSteps(tab) {
  const ui = tab.playwright, frame = ui.frameLocator('iframe'), results = [];
  lastChecks = results;
  const observe = () => tab.getAXState({ emit: false });
  const status = text => ui.locator('[data-editor-status]').filter({ hasText: text }).waitFor({ state: 'visible' });
  async function click(name) {
    const button = ui.getByRole('button', { name, exact: true });
    const enableLayout = name === '布局编辑' && await button.getAttribute('aria-pressed') !== 'true';
    await button.click();
    if (['读取服务端场景', '模拟并发修改', '重开编辑器', '关闭编辑器'].includes(name))
      await ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
    if (name === '布局编辑') await frame.locator('.hps-editor-layer').waitFor({ state: enableLayout ? 'visible' : 'detached' });
    if (name === '舍弃本地草稿并重载') await ui.locator('.html-scene-editor:not([inert])').waitFor({ state: 'visible' });
    await observe();
  }
  async function node(id, shift = false) { await ui.locator(`[data-object="${id}"]`).click(shift ? { modifiers: ['Shift'] } : {}); await observe(); }
  const field = key => ui.locator(`[data-field="presentation.${key}"]`);
  const value = async key => Number(await field(key).evaluate(el => el.value));
  async function readServer() {
    await click('读取服务端场景');
    await ui.locator('#fixture-result').filter({ hasText: '"revision"' }).waitFor({ state: 'visible' });
    return JSON.parse(await ui.locator('#fixture-result').textContent());
  }
  async function setField(key, number) {
    await field(key).click(); await field(key).press('ControlOrMeta+A');
    await field(key).pressSequentially(String(number)); await field(key).press('Tab'); await observe();
  }
  async function move(id, dx, dy, handle = null, expected = '布局修改已校验') {
    if (!handle) {
      // Existing selection is retained, including the group drag area.
      await frame.getByLabel(`布局对象 ${id}`, { exact: true }).click(); await observe();
    } else { await handle.click(); await observe(); }
    const target = handle || frame.getByLabel(`布局对象 ${id}`, { exact: true });
    const rect = await target.evaluate(el => el.getBoundingClientRect().toJSON());
    const viewport = await ui.locator('html').evaluate(el => ({ width: el.clientWidth, height: el.clientHeight }));
    const parent = await ui.locator('iframe').evaluate(el => el.getBoundingClientRect().toJSON());
    const left = Math.max(8, parent.x + rect.x), right = Math.min(viewport.width - 8, parent.x + rect.right);
    const top = Math.max(8, parent.y + rect.y), bottom = Math.min(viewport.height - 8, parent.y + rect.bottom);
    assert(right > left && bottom > top, 'gesture target must be visible');
    const point = [(left + right) / 2, (top + bottom) / 2];
    lastGesture = { id, point, delta: [dx, dy], target: rect, frame: parent };
    await tab.drag(point, [point[0] + dx, point[1] + dy]); await observe();
    await status(expected);
  }
  await status('修订');
  const before = await readServer();
  await click('布局编辑'); await ui.getByLabel('布局吸附', { exact: true }).uncheck(); await observe();
  assert.equal(await frame.locator('.hps-editor-layer').count(), 1);
  await node('header');
  await move('header', 12, 8);
  const headerX = await value('offsetX'), headerY = await value('offsetY');
  assert(headerX > 0 && headerY > 0); results.push('single drag -> author properties');
  await click('撤销'); await status('会话编辑已恢复'); assert.equal(await field('offsetX').count(), 0);
  await click('重做'); await status('会话编辑已恢复'); await field('offsetX').waitFor({ state: 'visible' });
  assert.equal(await value('offsetX'), headerX); results.push('undo/redo rerender');
  await click('保存修改'); await status('已保存');
  const savedHeader = await readServer(); assert(savedHeader.revision > before.revision);
  assert.equal(savedHeader.nodes.find(n => n.id === 'header').presentation.offsetX, headerX);
  await click('重开编辑器'); await status('修订'); await node('header'); assert.equal(await value('offsetY'), headerY);
  results.push('save/reopen position');
  yield { phase: 'position', checks: [...results] };

  await click('布局编辑'); await ui.getByLabel('布局吸附', { exact: true }).uncheck(); await observe(); await node('card-1');
  await move('card-1', -10, 0, frame.locator('[data-direction="e"]').filter({ visible: true }).first());
  const resized = await value('width'); assert(resized >= 20 && resized < 850);
  results.push('resize -> actual text reflow/validation');
  // A too-narrow text card must be rejected, and not consume another undo.
  await move('card-1', -240, 0, frame.locator('[data-direction="e"]').filter({ visible: true }).first(), '布局修改未应用');
  assert.equal(await value('width'), resized);
  await click('撤销'); await status('会话编辑已恢复'); assert.equal(await field('width').count(), 0);
  await click('重做'); await status('会话编辑已恢复'); await field('width').waitFor({ state: 'visible' });
  assert.equal(await value('width'), resized); results.push('capacity failure keeps draft and history');
  await click('保存修改'); await status('已保存');

  yield { phase: 'resize/failure', checks: [...results] };

  await node('card-1'); await node('card-2', true);
  assert((await ui.locator('[data-layout-selection]').textContent()).includes('2 个对象'));
  // Use the visible group area; its proxy children cannot select a new group.
  await move('card-1', 10, 8, frame.locator('.moveable-area').filter({ visible: true }).first());
  const groupX = await value('offsetX'); assert(groupX > 0);
  await node('card-2'); assert(Math.abs(await value('offsetX') - groupX) < 0.01);
  await click('撤销'); await status('会话编辑已恢复'); assert.equal(await field('offsetX').count(), 0);
  await node('card-1'); assert.equal(await field('offsetX').count(), 0);
  await click('重做'); await status('会话编辑已恢复'); await field('offsetX').waitFor({ state: 'visible' });
  assert.equal(await value('offsetX'), groupX); results.push('group movement is one undo transaction');
  await click('保存修改'); await status('已保存');

  yield { phase: 'group', checks: [...results] };

  await node('subject');
  const leader = frame.locator('[data-object-id="annotation"] path');
  const beforeLeader = await leader.getAttribute('d');
  await move('subject', 8, 0); assert.notEqual(await leader.getAttribute('d'), beforeLeader);
  results.push('image move recalculates relationship leader');
  await click('保存修改'); await status('已保存');
  const saved = await readServer();
  assert.deepEqual(saved.motion, before.motion); assert.deepEqual(saved.binding, before.binding);
  assert.deepEqual(saved.initialVisibleIds, before.initialVisibleIds);
  if (before.version === '0.7.0') {
    assert.equal(saved.version, before.version);
    for (const node of before.nodes) {
      const nonLayout = p => Object.fromEntries(Object.entries(p || {}).filter(([k]) => !['offsetX', 'offsetY', 'width', 'height'].includes(k)));
      assert.deepEqual(nonLayout(saved.nodes.find(n => n.id === node.id).presentation), nonLayout(node.presentation));
    }
    assert.equal(saved.nodes.find(n => n.id === 'header').presentation.variant, 'header-badge');
    results.push('0.7 presentation variants and non-layout styles preserved');
  }
  assert.equal(saved.nodes.find(n => n.id === 'subject').assetRef.id, before.nodes.find(n => n.id === 'subject').assetRef.id);
  results.push('motion/beat/hash/resource identities preserved');
  yield { phase: 'image/identities', checks: [...results] };

  await ui.getByRole('spinbutton', { name: '跳转毫秒', exact: true }).fill('0');
  await ui.getByRole('spinbutton', { name: '跳转毫秒', exact: true }).press('Tab'); await observe();
  assert.equal(await frame.locator('.hps-editor-layer').count(), 0);
  await click('布局编辑');
  assert(await frame.locator('.hps-editor-target[data-hidden="true"]').count() > 0);
  results.push('hidden objects have editor-only contours; seek removes overlay');
  await click('保存修改'); await status('内容未变化');
  assert.equal((await readServer()).revision, saved.revision); results.push('same-value save keeps revision');
  yield { phase: 'hidden/no-op', checks: [...results] };

  await node('header'); await setField('offsetX', headerX + 1);
  await click('模拟并发修改');
  await ui.locator('#fixture-result').filter({ hasText: '并发演示版本' }).waitFor({ state: 'visible' });
  await click('保存修改'); await status('修订冲突');
  assert.equal(await value('offsetX'), headerX + 1);
  await click('重开编辑器'); await status('修订冲突');
  assert.equal(await value('offsetX'), headerX + 1);
  await click('比较服务器版本');
  await ui.locator('.html-scene-editor pre').filter({ hasText: '并发演示版本' }).waitFor({ state: 'visible' });
  results.push('409 and reopen retain draft, comparison remains available');
  yield { phase: 'conflict', checks: [...results] };
  await click('舍弃本地草稿并重载'); await status('修订');
  await click('布局编辑'); assert.equal(await frame.locator('.hps-editor-layer').count(), 1);
  await click('布局编辑'); assert.equal(await frame.locator('.hps-editor-layer').count(), 0);
  await click('关闭编辑器'); assert.equal(await ui.locator('iframe').count(), 0);
  await click('重开编辑器'); await status('修订'); assert.equal(await ui.locator('iframe').count(), 1);
  results.push('toggle/close/reopen clean lifecycle');
  yield { passed: true, scenario: before.version, syntheticFixture: true, realBrowser: true,
    realProvider: false, checks: results, savedRevision: saved.revision, savedHeader: { headerX, headerY }, resizedWidth: resized };
}

export async function verifyEditorLayout(tab) {
  let result;
  for await (const phase of verifyEditorLayoutSteps(tab)) result = phase;
  return result;
}

// Run on a fresh fixture before the general edit/conflict suite. Coordinates are
// measured from visible proxy boxes; evaluate is read-only throughout.
export async function* verifyMarqueeAndSnapSteps(tab) {
  const ui = tab.playwright, frame = ui.frameLocator('iframe'), checks = [];
  const observe = () => tab.getAXState({ emit: false });
  const status = text => ui.locator('[data-editor-status]').filter({ hasText: text }).waitFor({ state: 'visible' });
  const proxy = id => frame.getByLabel(`布局对象 ${id}`, { exact: true });
  const box = locator => locator.evaluate(el => el.getBoundingClientRect().toJSON());
  const field = ui.locator('[data-field="presentation.offsetX"]');
  const offset = async () => await field.count() ? Number(await field.evaluate(el => el.value)) : 0;
  async function click(name) { await ui.getByRole('button', { name, exact: true }).click(); await observe(); }
  async function drag(locator, dx, dy) {
    const target = await box(locator), parent = await box(ui.locator('iframe'));
    const point = [parent.x + target.x + target.width / 2, parent.y + target.y + target.height / 2];
    await tab.drag(point, [point[0] + dx, point[1] + dy]); await observe(); await status('布局修改已校验');
  }
  await ui.locator('.html-scene-editor:not([inert])').waitFor({ state: 'visible' });
  await click('布局编辑'); await frame.locator('.hps-editor-layer').waitFor({ state: 'visible' });
  await ui.getByLabel('布局吸附', { exact: true }).uncheck(); await observe();
  const first = await box(proxy('card-1')), second = await box(proxy('card-2'));
  const parent = await box(ui.locator('iframe'));
  const from = [parent.x + Math.min(first.x, second.x) - 6, parent.y + first.y - 6];
  const to = [parent.x + Math.max(first.right, second.right) + 6, parent.y + second.bottom + 6];
  const viewport = await ui.locator('html').evaluate(el => ({ width: el.clientWidth, height: el.clientHeight }));
  assert(from[0] > 0 && from[1] > 0 && to[0] < viewport.width && to[1] < viewport.height, 'marquee must be fully visible');
  await tab.drag(from, to); await observe();
  const selected = await ui.locator('[data-object][aria-pressed="true"]').evaluateAll(els => els.map(el => el.dataset.object).sort());
  assert.equal(JSON.stringify(selected), JSON.stringify(['card-1', 'card-2']));
  assert.equal(await frame.locator('.hps-editor-target[data-editor-object="annotation"]').count(), 0);
  checks.push('marquee selects exactly two cards and excludes annotation');
  await drag(frame.locator('.moveable-area').filter({ visible: true }).first(), 10, 0);
  const firstX = await offset(); assert(firstX > 0);
  await ui.locator('[data-object="card-2"]').click(); await observe();
  assert(Math.abs(await offset() - firstX) < 0.01);
  await click('撤销'); await status('会话编辑已恢复'); assert.equal(await offset(), 0);
  await ui.locator('[data-object="card-1"]').click(); await observe(); assert.equal(await offset(), 0);
  checks.push('marquee group moves together and one undo restores both');
  yield { phase: 'marquee', checks: [...checks] };

  const stage = await box(frame.locator('.visual-stage')), scale = stage.width / 1600;
  await drag(proxy('card-1'), 30 * scale, 0);
  const displaced = await offset(); assert(Math.abs(displaced - 30) < 1);
  await ui.getByLabel('布局吸附', { exact: true }).check(); await observe();
  // Approach from the left: headline is 10 author pixels wider, so a rightward
  // residual could legitimately snap the card's right edge to the headline.
  await drag(proxy('card-1'), -displaced * scale - 2.5, 0);
  const snapped = await offset(); assert(Math.abs(snapped * scale) < 0.6, 'enabled guide snaps to original slot edge');
  await click('撤销'); await status('会话编辑已恢复');
  assert(Math.abs(await offset() - displaced) < 0.01);
  await ui.getByLabel('布局吸附', { exact: true }).uncheck(); await observe();
  await drag(proxy('card-1'), -displaced * scale - 2.5, 0);
  const unsnapped = await offset(); assert(Math.abs(unsnapped * scale + 2.5) < 1, 'disabled guide preserves pointer residual');
  assert(Math.abs((unsnapped - snapped) * scale) > 1.2);
  checks.push('enabled slot guides snap within threshold; disabled guides preserve residual');
  await click('撤销'); await status('会话编辑已恢复');
  await click('撤销'); await status('会话编辑已恢复'); assert.equal(await offset(), 0);
  yield { phase: 'slot-snap', checks: [...checks], scale, snappedAuthorOffset: snapped, unsnappedAuthorOffset: unsnapped };

  // Displace the other card off every registered slot edge so the next snap
  // proves element guidelines, rather than coincident static slot guidelines.
  await ui.locator('[data-object="card-2"]').click(); await observe();
  await drag(proxy('card-2'), 40 * scale, 0);
  const otherX = await offset();
  await ui.locator('[data-object="card-1"]').click(); await observe();
  await ui.getByLabel('布局吸附', { exact: true }).check(); await observe();
  await drag(proxy('card-1'), otherX * scale - 2.5, 0);
  const objectSnapped = await offset();
  assert(Math.abs((objectSnapped - otherX) * scale) < 0.6, 'snaps to another object away from slot guides');
  checks.push('other-object edge snaps independently of registered slot edges');
  await click('撤销'); await status('会话编辑已恢复'); assert.equal(await offset(), 0);
  await click('撤销'); await status('会话编辑已恢复');
  await ui.locator('[data-object="card-2"]').click(); await observe(); assert.equal(await offset(), 0);
  await click('布局编辑'); await frame.locator('.hps-editor-layer').waitFor({ state: 'detached' });
  yield { passed: true, realBrowser: true, syntheticFixture: true, checks, scale,
    snappedAuthorOffset: snapped, unsnappedAuthorOffset: unsnapped, objectSnappedAuthorOffset: objectSnapped };
}

export async function verifyLateLayoutPreview(tab) {
  const ui = tab.playwright;
  const fixtureDone = () => ui.locator('section[aria-label="隔离回归控制"][aria-busy="false"]').waitFor({ state: 'visible' });
  await ui.locator('.html-scene-editor:not([inert])').waitFor({ state: 'visible' });
  await ui.getByRole('button', { name: '延迟下一次预览', exact: true }).click(); await fixtureDone();
  await ui.getByRole('button', { name: '校验预览', exact: true }).click();
  assert.notEqual(await ui.locator('.html-scene-editor').getAttribute('inert'), null);
  await ui.getByRole('button', { name: '关闭编辑器', exact: true }).click(); await fixtureDone();
  assert.equal(await ui.locator('iframe').count(), 0);
  await ui.getByRole('button', { name: '重开编辑器', exact: true }).click(); await fixtureDone();
  assert.equal(await ui.locator('iframe').count(), 1);
  assert.equal(await ui.locator('.html-scene-editor').getAttribute('inert'), null);
  const frame = ui.frameLocator('iframe');
  assert.equal(await frame.locator('.hps-editor-layer').count(), 0);
  await ui.getByRole('button', { name: '布局编辑', exact: true }).click();
  await frame.locator('.hps-editor-layer').waitFor({ state: 'visible' });
  await ui.locator('[data-object="annotation"]').click();
  await ui.locator('[data-object="card-1"]').click({ modifiers: ['Shift'] });
  assert.equal(await ui.locator('[data-object="annotation"]').getAttribute('aria-pressed'), 'false');
  assert.equal(await ui.locator('[data-object="card-1"]').getAttribute('aria-pressed'), 'true');
  await tab.getAXState({ emit: false });
  return { passed: true, delayedResponseMs: 500, closedWhileInert: true,
    reopenedFrames: 1, editorLayers: await frame.locator('.hps-editor-layer').count(), annotationExcludedFromGroup: true };
}
