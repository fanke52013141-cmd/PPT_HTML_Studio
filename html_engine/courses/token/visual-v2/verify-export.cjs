// Visual study only: inspect deterministic frames or export the same browser stage.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {spawn, execFileSync} = require('node:child_process');
const {once} = require('node:events');
const {chromium} = require('../../../node_modules/playwright');
const definition = require('./design-definition.json');
const exportMode = process.argv.includes('--export');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const write = (name, value) => fs.writeFileSync(path.join(__dirname, 'evidence', name), JSON.stringify(value,null,2)+'\n');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.HPS_CHROME ? {executablePath:process.env.HPS_CHROME} : {})});
  const errors=[];
  try {
    const page = await browser.newPage({viewport:{width:1648,height:1180}, deviceScaleFactor:1});
    page.on('pageerror', e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
    await page.evaluate(()=>window.visualV2Ready);
    const frame=page.locator('#frame');
    if (exportMode) {
      execFileSync('ffmpeg',['-version'],{stdio:'ignore'});
      execFileSync('ffprobe',['-version'],{stdio:'ignore'});
      await page.addStyleTag({content:'main{max-width:none;margin:0;padding:0}header,nav,.transport,#status,details{display:none}#frame{width:1280px;border-radius:0;box-shadow:none}'});
      await page.setViewportSize({width:1280,height:720});
      await page.waitForTimeout(100);
      const out=path.resolve(__dirname,'../../../../outputs/token-visual-v2');
      fs.mkdirSync(out,{recursive:true});
      const stem='token-visual-v2-'+crypto.randomUUID();
      const temp=path.join(out,stem+'.partial.mp4'), final=path.join(out,stem+'.mp4');
      const fps=24, count=definition.sceneList.reduce((a,s)=>a+s.durationMs,0)*fps/1000;
      const ff=spawn('ffmpeg',['-hide_banner','-loglevel','error','-f','image2pipe','-vcodec','png','-framerate',String(fps),'-i','pipe:0','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',temp],{stdio:['pipe','ignore','pipe'],windowsHide:true});
      let stderr=''; ff.stderr.on('data',b=>stderr=(stderr+b.toString()).slice(-4096));
      ff.stdin.on('error',()=>{});
      const closed=once(ff,'close');
      for(let i=0;i<count;i++) {
        await page.evaluate(t=>window.visualV2.renderAtCourse(t), i*1000/fps);
        const png=await frame.screenshot();
        if(!ff.stdin.write(png)) await Promise.race([once(ff.stdin,'drain'),closed.then(()=>{throw new Error(stderr || 'Encoder closed before all frames');})]);
        if(i%240===0) console.log(`Export ${i}/${count}`);
      }
      ff.stdin.end();
      const [code]=await closed;
      assert.equal(code,0,stderr);
      const probe=JSON.parse(execFileSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',temp],{encoding:'utf8'}));
      assert.equal(probe.streams[0].width,1280); assert.equal(probe.streams[0].height,720);
      assert.equal(Number(probe.streams[0].nb_frames),count);
      assert.equal(probe.streams.length,1);
      execFileSync('ffmpeg',['-v','error','-i',temp,'-f','null','-'],{stdio:'pipe'});
      assert.deepEqual(errors,[]);
      fs.renameSync(temp,final);
      write('video-export.json',{file:path.basename(final),localOutputDirectory:'outputs/token-visual-v2',fps,frames:count,durationSeconds:count/fps,width:1280,height:720,audio:false,sha256:hash(fs.readFileSync(final)),decode:'passed',revision:definition.revision});
      console.log(final);
    } else {
      const captures=[], geometry=[];
      let prefix=0;
      for(const scene of definition.sceneList) {
        for(const [i,local] of scene.keyframes.entries()) {
          const t=prefix+Math.min(local,scene.durationMs-1);
          await page.evaluate(t=>window.visualV2.renderAtCourse(t),t);
          const png=await frame.screenshot();
          await page.evaluate(()=>window.visualV2.renderAtCourse(0));
          await page.evaluate(t=>window.visualV2.renderAtCourse(t),t);
          assert.equal(hash(await frame.screenshot()),hash(png),'Seek order changed pixels');
          const filename=`${scene.id}-${i}.png`;
          fs.writeFileSync(path.join(__dirname,'evidence',filename),png);
          captures.push({scene:scene.id,localTimeMs:Math.min(local,scene.durationMs-1),file:filename,sha256:hash(png)});
        }
        fs.copyFileSync(path.join(__dirname,'evidence',`${scene.id}-4.png`),path.join(__dirname,'evidence',`${scene.id}-final.png`));
        geometry.push(await page.evaluate(()=>({snapshot:window.visualV2.snapshot(),objects:[...document.querySelectorAll('.scene:not([hidden]) [data-object-id]')].map(el=>window.visualV2.geometry(el.dataset.objectId))})));
        const textBounds=await page.evaluate(()=>[...document.querySelectorAll('.scene:not([hidden]) .text,.scene:not([hidden]) .chip')].filter(el=>Number(getComputedStyle(el).opacity)>0).map(el=>{
          const range=document.createRange();range.selectNodeContents(el);
          const r=range.getBoundingClientRect(), b=el.getBoundingClientRect();
          return {id:el.dataset.objectId,overflow:r.width>b.width+2||r.height>b.height+2};
        }).filter(x=>x.overflow));
        assert.deepEqual(textBounds,[],`${scene.id} text overflow`);
        prefix+=scene.durationMs;
      }
      await page.evaluate(()=>window.visualV2.renderAtCourse(64999));
      for (const [id,width] of [['capacity.history',450],['capacity.question',150],['capacity.reserve',300],['capacity.attempt',450]]) {
        const g=await page.evaluate(id=>window.visualV2.geometry(id),id);
        assert.ok(Math.abs(g.rect.width-width)<1,`${id} wrong numeric width`);
      }
      await page.evaluate(()=>window.visualV2.renderAtCourse(5000));
      assert.equal(await page.evaluate(()=>window.visualV2.geometry('transient.token.0').opacity),1);
      await page.evaluate(()=>window.visualV2.renderAtCourse(15999));
      assert.equal(await page.evaluate(()=>window.visualV2.geometry('transient.token.0').opacity),0);
      await page.evaluate(()=>window.visualV2.renderAtCourse(31000));
      assert.equal((await page.evaluate(()=>window.visualV2.snapshot())).scene,'billing');
      await page.locator('#mode').selectOption('design'); assert.ok(await page.locator('#reference').isVisible());
      await page.locator('#play').click(); assert.ok(await page.locator('#stage').isVisible());
      await page.locator('#pause').click(); assert.equal(await page.evaluate(()=>window.visualV2.playing),false);
      assert.deepEqual(errors,[]);
      write('actual-geometry.json',geometry);
      write('verification.json',{revision:definition.revision,frames:captures,seekOrderPixelEquality:'passed',textBounds:'passed for visible final text',numericCapacityProportions:'passed',transientLifecycle:'passed',chapterBoundary:'passed',designAndPlayControls:'passed',browser:browser.version(),pageErrors:errors,aestheticApproval:'pending-user'});
      console.log('25 keyframes, deterministic seeking, text bounds, math and controls passed.');
    }
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
