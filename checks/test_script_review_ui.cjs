"use strict";
// Real DOM/editor behavior with isolated API doubles; never contacts a provider.
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const { chromium } = require("../html_engine/node_modules/playwright");
const root = path.resolve(__dirname, "..");
async function main() {
  const executablePath = process.env.HPS_CHROME || process.env.CHROME_PATH ||
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setContent("<body></body>");
    await page.evaluate(html => {
      const parsed = new DOMParser().parseFromString(html, "text/html");
      document.body.append(parsed.getElementById("step-panel-2"));
      document.getElementById("step-panel-2").style.display = "block";
      window.state = { currentProject: {id:"fixture"}, currentStep:2, slides:[], activeSlideIndex:0 };
      window.workspaceNavigationVersion = 1;
      window.isCurrentWorkspaceProject = (id, version) => state.currentProject.id === id && version === workspaceNavigationVersion;
      window.autoResizeNarrationTextarea = () => {};
      window.refreshCurrentProjectStatus = async () => {};
      window.offerArtifactRepair = async () => {};
      window.calls = [];
      window.review = {review_id:"revision-a", status:"pending", stale:false,
        candidate:{title:"test", slides:[{slide_id:"slide_001",slide_title:"test",narration:"没有统一标准。"}]},
        issues:[{slide_id:"slide_001",source_excerpt:"不适用于所有地区的统一标准 <img src=x onerror=alert(1)>",narration_excerpt:"没有统一标准。"}]};
      window.API = {
        get: async () => ({success:true}),
        getOptional: async url => url.includes("script/result") ? {success:true,script_plan:null,script_review:review} : {success:false},
        put: async (url,payload) => {
          calls.push({url,payload});
          return {success:true,script_plan:{title:payload.title,slides:payload.slides},
            script_review:{...review,status:"resolved"},visual_exists:false,visual_stale:false,workflow_pending:true};
        },
        post: async () => {throw new Error("Unexpected generation request");},
      };
    }, fs.readFileSync(path.join(root,"static/index.html"),"utf8"));
    await page.addScriptTag({path:path.join(root,"static/ui_foundation.js")});
    await page.addScriptTag({path:path.join(root,"static/storyboard.js")});
    await page.evaluate(() => loadStep2Data());
    assert.match(await page.locator("#step2-content-review").innerText(), /讲稿待核对/);
    assert.equal(await page.locator("#step2-content-review img").count(), 0);
    assert.equal(await page.locator("#step2-script-slides textarea").inputValue(), "没有统一标准。");
    assert.equal(await page.locator("#step2-btn-generate-visual").isDisabled(), true);
    await page.locator("#step2-script-slides textarea").fill("不存在适用于所有地区的统一标准。");
    await page.waitForTimeout(850); // Verify the normal 700ms autosave does not approve a review.
    assert.equal(await page.evaluate(() => calls.length), 0);
    await page.getByRole("button", {name:"保存修正讲稿",exact:true}).click();
    await page.waitForFunction(() => calls.length === 1 && !step2HasPendingReview());
    assert.equal(await page.evaluate(() => calls[0].payload.review_id), "revision-a");
    assert.equal(await page.locator("#step2-content-review").count(), 0);
    assert.equal(await page.locator("#step2-btn-generate-visual").isDisabled(), false);

    await page.evaluate(() => {
      acceptStep2ScriptReview({...review,stale:true});
      renderStep2Workspace();
    });
    assert.equal(await page.getByRole("button", {name:"保存修正讲稿",exact:true}).isDisabled(), true);
    assert.equal(await page.locator("#step2-btn-generate-visual").isDisabled(), true);

    // A save response for project A must not modify the state of project B.
    await page.evaluate(() => {
      acceptStep2ScriptReview(review); renderStep2Workspace();
      state.step2ScriptPlan.slides[0].narration = "不存在适用于所有地区的统一标准。";
      API.put = () => new Promise(resolve => window.finishSave = resolve);
      window.saving = saveStep2ScriptPlan({reviewConfirmed:true});
    });
    await page.evaluate(async () => {
      state.currentProject = {id:"other"}; workspaceNavigationVersion++;
      resetStep2ScriptState(); state.step2ScriptPlan = {title:"other",slides:[]};
      finishSave({success:true,script_plan:review.candidate,script_review:{...review,status:"resolved"}});
      await saving;
    });
    assert.equal(await page.evaluate(() => state.step2ScriptPlan.title), "other");
    assert.equal(await page.evaluate(() => step2ScriptReview), null);
    assert.deepEqual(errors, []);
    console.log("script review UI: reload, source text safety, explicit save, stale guard and project isolation passed");
  } finally { await browser.close(); }
}
main().catch(error => {console.error(error);process.exitCode=1;});
