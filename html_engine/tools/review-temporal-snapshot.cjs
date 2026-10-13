"use strict";
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const {chromium}=require('playwright'),{resolveBrowser}=require('./browser-runtime.cjs');
const {timeCoverage,overlapPolicy,checkTemporalPage}=require('./temporal-review.cjs');
const [folder,specPath,output]=process.argv.slice(2);
(async()=>{
  const scene=JSON.parse(fs.readFileSync(path.join(folder,'input/scene.json'),'utf8'));
  const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
  const spec={...JSON.parse(fs.readFileSync(specPath,'utf8')),clock:manifest.clock};
  const policy=JSON.parse(fs.readFileSync(path.join(folder,'source/qa-policy.json'),'utf8'));
  let browser,report={passed:false,code:'TEMPORAL_SNAPSHOT_FAILED'};
  fs.mkdirSync(output,{recursive:true});
  try {
    timeCoverage(scene,spec);overlapPolicy(scene,spec,policy);
    browser=await chromium.launch({headless:true,executablePath:resolveBrowser(chromium)});
    const page=await browser.newPage({viewport:{width:1648,height:1200},deviceScaleFactor:1}),errors=[];
    page.on('pageerror',e=>errors.push(e.name));
    await page.route('**/*',route=>/^https?:/.test(route.request().url())?route.abort():route.continue());
    await page.goto(pathToFileURL(path.resolve(folder,'preview/index.html')).href+'?export');
    await page.waitForFunction(()=>window.visualPlayer?.ready || document.querySelector('#status')?.textContent.startsWith('未应用'),{}, {timeout:20000});
    if(!await page.evaluate(()=>!!window.visualPlayer?.ready)) throw Error('SNAPSHOT_PREPARE_FAILED');
    report=await checkTemporalPage(page,scene,spec,output,policy);
    report.pageErrors=errors;report.passed=report.passed && !errors.length;
  } catch(e) {report={passed:false,code:'TEMPORAL_SNAPSHOT_FAILED',message:e.message};}
  finally {
    if(browser) await browser.close();
    fs.writeFileSync(path.join(output,'raw-report.json'),JSON.stringify(report,null,2));
    if(!report.passed) process.exitCode=1;
  }
})();
