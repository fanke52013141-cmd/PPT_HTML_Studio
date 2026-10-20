"use strict";
// Isolated real editor controls; no application server, providers or user data.
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {createInterface} = require('node:readline');
const {chromium} = require('../html_engine/node_modules/playwright');
const {captureLaunchOptions} = require('../html_engine/tools/browser-runtime.cjs');
const root = path.resolve(__dirname, '..'), run = process.argv[2];
const python = path.join(root, '.venv/Scripts/python.exe');
const piMode=process.argv.includes('--pi');

(async () => {
  const server = spawn(python, [path.join(__dirname, 'fixtures/html_handoff_bridge.py'), run,...(piMode?['--pi']:[])],
    {cwd:root, stdio:['pipe','pipe','pipe']});
  let browser, page, stderr=''; const errors=[]; server.stderr.on('data', chunk => {stderr += chunk;});
  const pending=[];
  createInterface({input:server.stdout}).on('line',line=>pending.shift()?.resolve(JSON.parse(line)));
  server.on('exit',code=>{while(pending.length)pending.shift().reject(Error('bridge exit '+code+' '+stderr));});
  const request=(method,url,payload)=>new Promise((resolve,reject)=>{
    pending.push({resolve,reject}); server.stdin.write(JSON.stringify({method,url,payload})+'\n');
  });
  try {
    const base = 'https://handoff-fixture.test', editor = `${base}/api/projects/isolated/html-visual/condensation/editor`;
    const readServer = async()=>JSON.parse(Buffer.from((await request('GET',editor)).body,'base64').toString());
    browser = await chromium.launch(captureLaunchOptions(chromium));
    page = await browser.newPage({acceptDownloads:true,viewport:{width:1440,height:1100}});
    await page.route('**/*',async route=>{
      try {
        const req=route.request(), response=await request(req.method(),req.url(),req.postData()?req.postDataJSON():null);
        fs.appendFileSync(path.join(run,'request-log.txt'),req.method()+' '+req.url()+' '+response.status+'\n');
        if(response.status>=400) fs.appendFileSync(path.join(run,'request-log.txt'),Buffer.from(response.body,'base64').toString()+'\n');
        await route.fulfill({...response,body:Buffer.from(response.body,'base64')});
      } catch(error) { await route.abort(); console.error(error); }
    });
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    await page.locator('[data-object="headline"]').click();
    let panel = page.locator('[data-external-handoff]');
    await panel.locator('summary').first().click();
    assert.ok(await panel.locator('input[type=file]').isHidden());
    assert.ok(await panel.locator('[data-external-report]').isHidden());
    const strict=panel.getByLabel('严格交接：需实际看图、能力声明与逐项验收记录');
    assert.ok(await strict.isChecked());
    await strict.uncheck(); // Exercise the preserved 0.2 legacy result route here; v2 is checked separately.
    await panel.locator('textarea').fill('调整标题字阶，保持正文、素材、关系和人工字段');
    if(piMode){
      const before=await readServer(),pi=panel.locator('[data-pi-agent]');
      await pi.getByRole('button',{name:'开始 AI 修改',exact:true}).click();
      await pi.getByRole('status').filter({hasText:'AI 修改完成，候选已显示'}).waitFor({timeout:180000});
      assert.equal((await readServer()).revision,before.revision);
      assert.ok(await panel.getByRole('button',{name:'保存本次候选',exact:true}).isEnabled());
      assert.ok(await panel.locator('.html-external-comparison img').count()>0);
      await pi.getByRole('button',{name:'恢复任务状态',exact:true}).click();
      await pi.getByRole('status').filter({hasText:'AI 修改完成，候选已显示'}).waitFor();
      assert.equal((await readServer()).revision,before.revision);
      await panel.getByRole('button',{name:'人工微调此候选',exact:true}).click();
      await panel.locator('[data-handoff-workbench]').waitFor();
      assert.deepEqual(errors,[]);
      const output={passed:true,checks:['actual Pi SDK','UI submit and poll','actual DOM and screenshots','automatic strict delivery display','no author save','persistent result recovery','human takeover','no page errors']};
      fs.writeFileSync(path.join(run,'pi-browser-report.json'),JSON.stringify(output,null,2));
      await page.screenshot({path:path.join(run,'pi-agent.png'),fullPage:true});
      console.log(JSON.stringify(output));return;
    }
    await panel.getByText('验收条件：字号与指定遮挡对象对',{exact:true}).click();
    await panel.getByRole('button',{name:'添加最低字号条件',exact:true}).click();
    await panel.getByLabel('最低字号',{exact:true}).fill('22');
    await panel.getByRole('button',{name:'添加遮挡检查对象对',exact:true}).click();
    await panel.getByLabel('遮挡对象一').selectOption('headline');
    await panel.getByLabel('遮挡对象二').selectOption('intro');
    const initial = await readServer();
    const download = page.waitForEvent('download');
    await panel.getByRole('button',{name:'导出输入包',exact:true}).click();
    const file = await download;
    const archive = path.join(run,'download.zip'); await file.saveAs(archive);
    const packet = JSON.parse(execFileSync(python,['-c',
      'import sys,json,zipfile;print(json.dumps(json.loads(zipfile.ZipFile(sys.argv[1]).read("task.json"))))',archive],{encoding:'utf8'}));
    assert.equal(packet.context.style.theme.id,initial.scene.themeRef.id);
    assert.ok(packet.files.some(f=>f.role==='actual_render'));
    assert.equal(packet.context.execution.font_requirements[0].minimum_px,22);
    assert.equal(packet.context.execution.font_requirements[0].targetId,'headline');
    assert.deepEqual(packet.context.execution.overlap_coverage.pairs,[['headline','intro']]);
    assert.ok(packet.files.some(f=>f.path==='decision-input.json'));
    const proposed = {format:'hps.html.external_result',version:'0.2.0',task_id:packet.task_id,status:'proposed',message:'调整公开字阶',
      operations:[{kind:'set_text_style',targetId:'headline',part:'text',values:{fontSizePx:28}}]};
    const reportText = '# Agent report\nself_checked / not_run\n<img src=x onerror="window.badReport=true">';
    const delivery = result => execFileSync(python, ['-c',
      'import sys,json,zipfile,io;d=json.load(sys.stdin);b=io.BytesIO();z=zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED);z.writestr("result.json",json.dumps(d[0]));z.writestr("report.md",d[1]);z.close();sys.stdout.buffer.write(b.getvalue())'],
      {input:JSON.stringify([result,reportText])});
    const bad = {...proposed,operations:[...proposed.operations,{kind:'set_presentation',targetId:'headline',values:{offsetY:-400}}]};
    const chooser = page.waitForEvent('filechooser');
    await panel.getByRole('button',{name:'导入 Agent 输出',exact:true}).click();
    await (await chooser).setFiles({name:'delivery.zip',mimeType:'application/zip',buffer:delivery(bad)});
    await panel.getByRole('status').filter({hasText:'检查未通过，未保存'}).waitFor({timeout:120000});
    assert.equal((await readServer()).revision,initial.revision);
    assert.ok(await panel.getByRole('button',{name:'保存本次候选',exact:true}).isDisabled());
    assert.ok((await panel.locator('[data-external-report] pre').textContent()).includes('<img'));
    assert.equal(await panel.locator('[data-external-report] img').count(),0);
    assert.equal(await page.evaluate(()=>window.badReport),undefined);
    const feedbackDownload=page.waitForEvent('download');
    await panel.getByRole('button',{name:'导出检查反馈',exact:true}).click();
    const feedbackFile=path.join(run,'feedback.json'); await (await feedbackDownload).saveAs(feedbackFile);
    const feedback=JSON.parse(fs.readFileSync(feedbackFile,'utf8'));
    assert.equal(feedback.task_id,packet.task_id); assert.equal(feedback.passed,false); assert.equal(feedback.validation.code,'SCENE_INVALID');
    const feedbackZipDownload=page.waitForEvent('download');
    await panel.getByRole('button',{name:'导出完整反馈包',exact:true}).click();
    await (await feedbackZipDownload).saveAs(path.join(run,'full-feedback.zip'));
    await panel.getByRole('button',{name:'人工微调此候选',exact:true}).click();
    const work=panel.locator('[data-handoff-workbench]');await work.waitFor();
    await work.getByRole('button',{name:'检查工作草稿',exact:true}).click();
    await work.getByRole('button',{name:'预览联动修复方案',exact:true}).waitFor();
    assert.equal((await readServer()).revision,initial.revision);
    await work.getByRole('button',{name:'预览联动修复方案',exact:true}).click();
    await work.getByText('联动方案检查通过；工作草稿尚未改变，请核对预览后确认。',{exact:true}).waitFor({timeout:120000});
    await work.getByText('工作版本 0',{exact:false}).waitFor();
    assert.equal((await readServer()).revision,initial.revision);
    await work.getByRole('button',{name:'确认应用此联动方案',exact:true}).click();
    await work.getByText('工作版本 1',{exact:false}).waitFor();
    assert.ok(await work.getByRole('button',{name:'保存工作草稿到页面',exact:true}).isDisabled());
    await work.getByRole('button',{name:'撤销人工修改',exact:true}).click();
    await work.getByText('工作版本 2',{exact:false}).waitFor();

    await work.getByLabel('人工修改操作',{exact:true}).selectOption({label:'位置与尺寸'});
    await work.locator('[data-work-field="offsetY"]').fill('0');
    await work.getByRole('button',{name:'应用到工作草稿',exact:true}).click();
    await work.getByText('工作版本 3',{exact:false}).waitFor();
    await work.getByText('工作草稿 · 诊断显示',{exact:false}).waitFor();
    const candidateFrame=page.frameLocator('iframe[title="人工候选工作画布"]');
    assert.ok((await work.getByText('水平偏移（向右为正）',{exact:true}).count())===1);
    await work.getByLabel('候选画布视图').selectOption('baseline');
    await work.getByText('只读对照，不会改变工作草稿。',{exact:true}).waitFor();
    assert.equal(await candidateFrame.locator('[data-editor-object]').count(),0);
    await work.getByLabel('候选画布视图').selectOption('work');
    await work.getByText('工作草稿 · 诊断显示',{exact:false}).waitFor();

    const proxy=candidateFrame.locator('[data-editor-object="headline"]');await proxy.waitFor();
    const originalRect=await proxy.boundingBox();
    await page.mouse.move(originalRect.x+originalRect.width/2,originalRect.y+originalRect.height/2);
    await page.mouse.down();await page.mouse.move(originalRect.x+originalRect.width/2+8,originalRect.y+originalRect.height/2+4,{steps:8});await page.mouse.up();
    await work.getByText('工作版本 4',{exact:false}).waitFor();
    assert.equal((await readServer()).revision,initial.revision);
    await work.getByRole('button',{name:'撤销人工修改',exact:true}).click();
    await work.getByText('工作版本 5',{exact:false}).waitFor();

    assert.equal((await readServer()).revision,initial.revision);
    await work.getByRole('button',{name:'撤销人工修改',exact:true}).click();
    await work.getByText('工作版本 6',{exact:false}).waitFor();
    await work.getByRole('button',{name:'重做人工修改',exact:true}).click();
    await work.getByText('工作版本 7',{exact:false}).waitFor();
    await work.getByRole('button',{name:'定位此对象',exact:true}).click();
    const resizeHandle=candidateFrame.locator('[data-direction="e"]').filter({visible:true}).first();
    const handleBox=await resizeHandle.boundingBox();
    await page.mouse.move(handleBox.x+handleBox.width/2,handleBox.y+handleBox.height/2);
    await page.mouse.down();await page.mouse.move(handleBox.x+handleBox.width/2-8,handleBox.y+handleBox.height/2,{steps:8});await page.mouse.up();
    await work.getByText('工作版本 8',{exact:false}).waitFor();
    await work.getByRole('button',{name:'撤销人工修改',exact:true}).click();
    await work.getByText('工作版本 9',{exact:false}).waitFor();
    await work.screenshot({path:path.join(run,'candidate-canvas.png')});

    await work.getByRole('button',{name:'检查工作草稿',exact:true}).click();
    await work.getByText('原系统检查通过，尚未保存',{exact:false}).waitFor({timeout:120000});
    assert.ok(await work.getByRole('button',{name:'保存工作草稿到页面',exact:true}).isEnabled());
    await page.evaluate(()=>HtmlSceneEditor.open(document.getElementById('host'),'isolated','condensation'));
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    panel=page.locator('[data-external-handoff]');await panel.locator('summary').first().click();
    await panel.getByRole('button',{name:'恢复工作草稿',exact:true}).click();
    await panel.locator('[data-handoff-workbench]').getByText('工作版本 9',{exact:false}).waitFor();
    const restoredWork=panel.locator('[data-handoff-workbench]');
    await restoredWork.locator('[data-work-group]').first().uncheck();
    await restoredWork.getByRole('button',{name:'采用所选组到工作草稿',exact:true}).click();
    await restoredWork.getByText('工作版本 10',{exact:false}).waitFor();
    await page.frameLocator('iframe[title="人工候选工作画布"]').locator('body').evaluate(()=>new Promise((resolve,reject)=>{
      const until=Date.now()+15000;const tick=()=>{const node=window.visualPlayer.scene?.nodes.find(n=>n.id==='headline');
      if(node&&!node.presentation?.typography?.text?.fontSizePx)resolve();else if(Date.now()>until)reject(Error('partial group not rendered'));else setTimeout(tick,30);};tick();}));
    await restoredWork.getByRole('button',{name:'撤销人工修改',exact:true}).click();
    await restoredWork.getByText('工作版本 11',{exact:false}).waitFor();

    assert.equal((await readServer()).revision,initial.revision);
    await panel.locator('input[type=file]').setInputFiles({name:'delivery.zip',mimeType:'application/zip',buffer:delivery(proposed)});
    await panel.getByRole('status').filter({hasText:'检查通过，尚未保存'}).waitFor({timeout:120000});
    assert.equal((await readServer()).revision,initial.revision);
    assert.ok(await panel.locator('.html-external-comparison img').count()>=2);
    await panel.getByRole('button',{name:'保存本次候选',exact:true}).click();
    await page.locator('[data-editor-status]').filter({hasText:`修订 ${initial.revision+1}`}).waitFor();
    await page.locator('.html-scene-editor:not([inert])').waitFor();
    const saved = await readServer();
    assert.equal(saved.revision,initial.revision+1);
    assert.equal(saved.scene.nodes.find(n=>n.id==='headline').presentation.typography.text.fontSizePx,28);
    panel = page.locator('[data-external-handoff]'); await panel.locator('summary').first().click();
    await panel.locator('input[type=file]').setInputFiles({name:'old-result.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(proposed))});
    await panel.getByRole('status').filter({hasText:'修订已变化'}).waitFor();
    assert.ok(await panel.getByRole('button',{name:'保存本次候选',exact:true}).isDisabled());
    assert.equal((await readServer()).revision,saved.revision);
    await page.locator('[data-object="headline"]').click();
    await page.locator('[data-field="runs.0.text"]').fill('有未保存的本地草稿');
    await page.locator('[data-field="runs.0.text"]').press('Tab');
    await panel.locator('input[type=file]').setInputFiles({name:'dirty-result.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(proposed))});
    await panel.getByRole('status').filter({hasText:'有未保存的页面草稿'}).waitFor();
    assert.equal((await readServer()).revision,saved.revision);
    await page.getByRole('button',{name:'读取保存版本',exact:true}).click();
    await page.getByLabel('已保存版本',{exact:true}).selectOption(String(initial.revision));
    await page.getByRole('button',{name:'预览恢复所选版本',exact:true}).click();
    await page.locator('[data-editor-status]').filter({hasText:'历史版本已进入当前草稿'}).waitFor();
    assert.equal((await readServer()).revision,saved.revision);
    await page.getByRole('button',{name:'保存修改',exact:true}).click();
    await page.locator('[data-editor-status]').filter({hasText:'已保存；本页需要重新审阅'}).waitFor();
    assert.equal((await readServer()).revision,saved.revision+1);
    assert.deepEqual(errors,[]);
    const output = {passed:true,checks:['actual export and ZIP','resolved theme','actual screenshots','ZIP output import','external report as text',
      'failed candidate cannot save','feedback download','same-filename retry','import does not save',
      'structured font and overlap export','human amendment draft','Chinese diagnostics and linked preview','explicit linked confirmation','partial dependency group adoption','group undo restore','canvas drag and resize','read-only candidate comparison','Chinese properties','persistent undo redo','saved version restore to new revision','persistent work restore','feedback ZIP','before/after images','explicit save and reopen','stale import blocked','dirty draft preserved','no page errors']};
    fs.writeFileSync(path.join(run,'browser-report.json'),JSON.stringify(output,null,2));
    await page.screenshot({path:path.join(run,'editor-handoff.png'),fullPage:true});
    console.log(JSON.stringify(output));
  } catch(error) {
    fs.writeFileSync(path.join(run,'browser-failure.json'),JSON.stringify({error:String(error),errors,stderr,html:page?await page.content():null},null,2));
    if(page) await page.screenshot({path:path.join(run,'browser-failure.png'),fullPage:true}).catch(()=>{});
    throw error;
  } finally { if(browser) await browser.close(); server.kill(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
