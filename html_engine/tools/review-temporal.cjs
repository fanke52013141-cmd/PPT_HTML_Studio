"use strict";
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const {checkTemporalPage,timeCoverage,overlapPolicy}=require('./temporal-review.cjs');
const [scenePath,specPath,outDir]=process.argv.slice(2);
(async()=>{
  const scene=JSON.parse(fs.readFileSync(scenePath,'utf8')),spec=JSON.parse(fs.readFileSync(specPath,'utf8'));
  const policy=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../visual/qa/overlap-policy.json'),'utf8'));
  timeCoverage(scene,spec);overlapPolicy(scene,spec,policy);
  fs.mkdirSync(outDir,{recursive:true});
  const browser=await chromium.launch(require("./browser-runtime.cjs").captureLaunchOptions(chromium));
  try {
    const page=await browser.newPage({viewport:{width:1648,height:1200}}),errors=[];
    page.on('pageerror',e=>errors.push(e.name));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../visual/preview/index.html')).href);
    await page.waitForFunction(()=>window.visualPlayer?.ready,{}, {timeout:20000});
    const assets=require('./project-resources.cjs').loadProjectResources();
    const applied=await page.evaluate(async({scene,assets})=>window.visualPlayer.apply(scene,assets),{scene,assets});
    if(!applied) throw Error(await page.locator('#status').innerText());
    const report=await checkTemporalPage(page,scene,spec,outDir,policy);
    report.pageErrors=errors;report.passed=report.passed && !errors.length;
    fs.writeFileSync(path.join(outDir,'report.json'),JSON.stringify(report,null,2));
  }finally{await browser.close();}
})().catch(e=>{
  fs.mkdirSync(outDir,{recursive:true});fs.writeFileSync(path.join(outDir,'report.json'),JSON.stringify({passed:false,code:'TEMPORAL_REVIEW_FAILED',message:e.message}));process.exitCode=1;
});
