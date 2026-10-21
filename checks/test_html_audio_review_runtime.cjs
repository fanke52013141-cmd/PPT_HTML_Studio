'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert'),{spawn}=require('child_process');
const {chromium}=require('../html_engine/node_modules/playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),run=fs.mkdtempSync(path.join(os.tmpdir(),'hps-editor-browser-audio-'));
 const child=spawn(require('./browser_python.cjs').pythonExecutable(root),[path.join(__dirname,'test_html_scene_editor_fixture.py'),run],{cwd:root,windowsHide:true});
 let stderr='',browser;child.stderr.on('data',data=>stderr+=data);
 try{
  const port=await new Promise((resolve,reject)=>{
   let output='';const timer=setTimeout(()=>reject(Error(stderr||'fixture timeout')),20000);
   child.stdout.on('data',data=>{output+=data;try{const value=JSON.parse(output.trim());clearTimeout(timer);resolve(value.port);}catch{}});
   child.on('exit',code=>{clearTimeout(timer);reject(Error(`fixture exited ${code}: ${stderr}`));});
  });
  browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
  const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${port}/audio-test`);
  await page.locator('audio').waitFor();
  await page.waitForFunction(()=>document.querySelector('audio').readyState>=1);
  const frame=page.frames().find(f=>f.url()==='about:srcdoc');
  assert(await frame.evaluate(()=>visualPlayer.ready));
  await page.getByRole('button',{name:'2. 句子 2',exact:true}).click();
  await frame.waitForFunction(()=>visualPlayer.timeMs===6000);
  assert.equal(await page.locator('audio').evaluate(a=>a.currentTime),6);
  assert.equal(await frame.locator('[data-track="subtitle"]').innerText(),'句子 2');
  await page.locator('audio').evaluate(a=>a.play());
  await page.waitForFunction(()=>document.querySelector('audio').currentTime>6.3);
  const clock=await page.evaluate(()=>{const a=document.querySelector('audio');const p=document.querySelector('iframe').contentWindow.visualPlayer;return {audio:a.currentTime*1000,visual:p.timeMs,visualPlaying:p.playing};});
  assert(Math.abs(clock.audio-clock.visual)<80,JSON.stringify(clock));assert.equal(clock.visualPlaying,false);
  await page.evaluate(()=>HtmlAudioReview.close());
  assert.equal(await page.locator('audio').evaluate(a=>a.paused),true);
  const frozen=await frame.evaluate(()=>visualPlayer.timeMs);
  await page.getByRole('button',{name:'1. 句子 1',exact:true}).click();
  assert.equal(await frame.evaluate(()=>visualPlayer.timeMs),frozen,'closed controller cannot change the frame');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['real editor binding','real shared runtime','decoded synthetic WAV','sentence subtitle and seek','audio and frame clock delta <80ms','no independent visual play','close freezes frame'],clock,scope:'isolated synthetic fixture, not real TTS or course acceptance'}));
 }finally{if(browser)await browser.close();child.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
