import assert from 'node:assert/strict';

export async function* verifyProductViewport(tab, cdp) {
  const ui=tab.playwright, frame=ui.frameLocator('iframe'), results=[];
  const status=text=>ui.locator('[data-editor-status]').filter({hasText:text}).waitFor({state:'visible'});
  await status('修订');
  try {
    for (const [width,height,dpr] of [[1280,900,1],[1280,900,1.5],[1280,900,2],[1920,1080,1],[1920,1080,1.5],[1920,1080,2]]) {
      await cdp.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:dpr,mobile:false});
      const button=ui.getByRole('button',{name:'布局编辑',exact:true});
      if(await button.getAttribute('aria-pressed')!=='true') await button.click();
      await ui.getByLabel('布局吸附',{exact:true}).uncheck();
      await ui.locator('[data-object="header"]').click(); await tab.getAXState({emit:false});
      const target=frame.getByLabel('布局对象 header',{exact:true});
      await target.click(); await tab.getAXState({emit:false});
      const box=await target.evaluate(el=>el.getBoundingClientRect().toJSON());
      const parent=await ui.locator('iframe').evaluate(el=>el.getBoundingClientRect().toJSON());
      const stage=await frame.locator('.visual-stage').evaluate(el=>el.getBoundingClientRect().toJSON());
      const start=[parent.x+box.x+Math.min(box.width/2,100),parent.y+box.y+Math.min(box.height/2,25)];
      await tab.drag(start,[start[0]+12,start[1]+8]); await status('布局修改已校验');
      const x=Number(await ui.locator('[data-field="presentation.offsetX"]').evaluate(el=>el.value));
      const y=Number(await ui.locator('[data-field="presentation.offsetY"]').evaluate(el=>el.value));
      assert(Math.abs(x-12*1600/stage.width)<=1); assert(Math.abs(y-8*900/stage.height)<=1);
      await ui.getByRole('button',{name:'撤销',exact:true}).click(); await status('会话编辑已恢复');
      assert.equal(await ui.locator('[data-field="presentation.offsetX"]').count(),0);
      results.push({width,height,dpr,authorX:x,authorY:y,stageWidth:stage.width});
      yield {cases:results.length,latest:results.at(-1)};
    }
    for(let i=0;i<10;i++) {
      await ui.getByRole('button',{name:'重开编辑器',exact:true}).click(); await status('修订');
      assert.equal(await ui.locator('iframe').count(),1);
      await ui.getByRole('button',{name:'布局编辑',exact:true}).click();
      await frame.locator('.hps-editor-layer').waitFor({state:'visible'});
      assert.equal(await frame.locator('.hps-editor-layer').count(),1);
      await tab.getAXState({emit:false});
    }
    return {passed:true,cases:results,reopenCycles:10,frames:1,layers:1};
  } finally {await cdp.send('Emulation.clearDeviceMetricsOverride');}
}

// Run with a cua_repl Tab and its documented CDP capability; no separate browser.
export async function* verifyCanvasStress(tab, cdp) {
  const ui = tab.playwright, results = [], latencies = [];
  try {
    for (const [width, height] of [[1280, 900], [1920, 1080]]) {
      for (const dpr of [1, 1.5, 2]) {
        await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor:dpr, mobile:false });
        for (const scale of ['.5', '1', '1.5', '2']) {
          await ui.locator('#scale').selectOption(scale);
          await ui.getByRole('button', {name:'重置',exact:true}).click();
          await tab.getAXState({emit:false});
          assert.equal(await ui.locator('.hps-editor-target').count(), 40);
          assert.equal(await ui.locator('.hps-editor-layer').count(), 1);
          const target = ui.getByLabel('布局对象 item-0', {exact:true});
          await target.click(); await tab.getAXState({emit:false});
          const box = await target.evaluate(el => el.getBoundingClientRect().toJSON());
          const start = [box.x + box.width / 2, box.y + box.height / 2];
          await tab.drag(start, [start[0]+12, start[1]+8]);
          await ui.locator('#status').filter({hasText:'完成1'}).waitFor({state:'visible'});
          await tab.getAXState({emit:false});
          const result = JSON.parse(await ui.locator('#result').textContent());
          const values = result.commits[0][0].values;
          assert(Math.abs(values.offsetX - 12 / Number(scale)) <= 1);
          assert(Math.abs(values.offsetY - 8 / Number(scale)) <= 1);
          assert.equal(result.commits.length, 1);
          assert.equal(result.commits[0].length, 1);
          assert(Math.abs(result.dpr - dpr) < 0.001);
          latencies.push(...result.samples);
          results.push({width,height,dpr,scale:Number(scale),offset:values});
        }
        yield {cases:results.length, latest:results.at(-1)};
      }
    }
    const sorted = latencies.sort((a,b)=>a-b), p95 = sorted[Math.ceil(sorted.length*.95)-1];
    assert(sorted.length >= 24);
    assert(p95 <= 100, `input-to-next-frame p95 ${p95}ms exceeds 100ms`);
    return {passed:true,cases:results,latency:{metric:'pointerdown-to-next-animation-frame',samples:sorted.length,p95_ms:p95},
      scope:'40-object production canvas adapter; separate from renderer/server/model latency'};
  } finally { await cdp.send('Emulation.clearDeviceMetricsOverride'); }
}
