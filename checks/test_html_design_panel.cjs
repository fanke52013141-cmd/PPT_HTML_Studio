"use strict";
// Real browser/DOM, fixture API. No application server or user data.
const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("../html_engine/node_modules/playwright");

(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.HPS_CHROME});
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="step-panel-3"></div>');
    await page.evaluate(() => {
      const image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=';
      window.PPTStudio = {runtime:{state:{currentProject:{id:'fixture',visual_backend:'html'},slides:[{slide_id:'s1',title:'Fixture'}],activeSlideIndex:0}}};
      window.requests = [];
      window.API = {
        get:async url => ({design:{key:'a'.repeat(64),status:'needs_review',stale:false,image_url:image}}),
        post:async (url, body) => {
          requests.push({url,body});
          return body.design_candidate_key ? {design_candidate_key:body.design_candidate_key,review:{passed:true,screenshot_url:image}} :
            {stage:'design_review',design:{key:'b'.repeat(64),image_url:image},message:'Design ready'};
        },
      };
    });
    await page.addScriptTag({path:path.resolve(__dirname,'../static/html_review_panel.js')});
    await page.evaluate(() => window.HtmlReviewPanel.refresh());
    await page.waitForFunction(() => !document.querySelector('[data-html-design]').hidden);
    await page.locator('[data-action="accept-design"]').click();
    await page.waitForFunction(() => requests.length === 1 && document.querySelector('[data-html-design]').hidden);
    assert.equal((await page.evaluate(() => requests[0])).body.design_candidate_key, 'a'.repeat(64));
    await page.locator('[data-asset-instruction]').fill('简化主体轮廓');
    await page.locator('[data-action="retry-asset"]').click();
    await page.waitForFunction(() => requests.length === 2);
    assert.equal((await page.evaluate(() => requests[1])).body.asset_instruction,'简化主体轮廓');
    await page.locator('[data-action="produce"]').click();
    await page.waitForFunction(() => !document.querySelector('[data-html-design]').hidden);
    await page.locator('.html-design-revision summary').click();
    await page.locator('[data-design-instruction]').fill('增强标题层级');
    await page.locator('[data-action="revise-design"]').click();
    await page.waitForFunction(() => requests.length === 4);
    assert.equal((await page.evaluate(() => requests[3])).body.design_instruction,'增强标题层级');
    // Switching projects must not carry a previous candidate or instruction.
    await page.evaluate(() => {
      API.get = async () => ({design:null});
      PPTStudio.runtime.state.currentProject = {id:'next',visual_backend:'html'};
      HtmlReviewPanel.refresh();
    });
    assert(await page.locator('[data-html-design]').isHidden());
    assert.equal(await page.locator('[data-design-instruction]').inputValue(),'');
    console.log('HTML design panel: recovery, explicit confirmation, revision and project isolation passed');
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});
