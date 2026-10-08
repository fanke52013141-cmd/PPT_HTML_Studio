"use strict";
// Bounded browser-effect demonstration. Not the application's production registry.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {pathToFileURL}=require('url'),{chromium}=require('playwright');
const groups=[
 ['G','几何与路径','SVG','可见几何位于对象box内；控制点可越界50px；线宽1–8px。', ['直线与方向','折线','二次贝塞尔曲线','三次贝塞尔曲线','圆弧','圆与椭圆','矩形与圆角矩形','多边形与星形']],
 ['S','描边与连接','SVG','线宽1–8px；端帽/接头固定枚举；虚线2–24px；箭头按端点绑定。',['线宽层级','端帽：平/圆/方','接头：斜/圆/尖','虚线与点线','单向与双向箭头','内外轮廓']],
 ['F','填充与色彩','CSS/SVG','纯色/2–3色渐变；透明度0–1；图案限规则点/斜线。',['纯色填充','线性渐变','径向渐变','多色渐变','规则图案填充','半透明叠层']],
 ['E','表面、滤镜与合成','CSS/SVG','阴影偏移0–12px、模糊0–24px；滤镜限示例；不可推导真实物理材质。',['外阴影','内阴影','局部模糊','受控发光','背景模糊玻璃层','简单浮雕表面','混合模式','裁切与透明遮罩']],
 ['T','文字与标识','HTML/CSS/SVG','字号18–48px、字重400/700；真实文本；公式限可排版表达；图标为简单路径。',['字阶与字重','重点词与下划线','段落换行与行距','标签与编号','公式与上下标','沿曲线文字']],
 ['L','容器与信息组合','HTML/CSS/SVG','圆角0–24px；边线1–3px；间距12–40px；对象需ID和独立box。',['知识卡','分组与层级','网格与对齐','时间线与步骤','批注与指示','流程与关系']],
 ['D','数据与比例','SVG/Canvas','必须提供真实数据；示例最多12项；线性坐标；图例与数值为代码。',['柱状图','折线图','面积图','饼图与环图','进度与刻度','节点关系图']],
 ['C','Canvas二维示意','Canvas2D','确定性种子与时间；演示最多48对象；波/粒子/轨迹为示意，非物理仿真。',['有限粒子群','波形','轨迹与尾迹','热力色块','路径高亮','对象组平移']],
 ['M','运动与状态','CSS/SVG/JS','进度0–1；位移≤80px；缩放0.8–1.2；路径形变需相同命令结构。',['透明度出现','平移入场','缩放强调','二维旋转','描边绘制','遮罩揭示','兼容路径形变','数值递增','沿路径运动']]
];
const denied=new Set(['F05','E03','E04','E05','E06','E07']);
const catalog={format:'hps.browser_effect_demo',version:'0.1.0',status:'defined; demo rendering required; not production-integrated',
 theme:{background:'#FBFAF8',ink:'#405574',blue:'#4B83C9',pink:'#F4819B',green:'#4B987D',purple:'#B1A1EC'},
 effects:groups.flatMap(([prefix,category,backend,bounds,names])=>names.map((name,i)=>({id:prefix+String(i+1).padStart(2,'0'),name,category,backend,parameter_bounds:bounds,
 allowed_for_demo_style:!denied.has(prefix+String(i+1).padStart(2,'0')),integration_status:'browser_demo_only',evidence_kind:prefix==='M'?'three deterministic keyframes':'native browser rendering'})))};

function browserDemo(){
 const ink='#405574',blue='#4B83C9',pink='#F4819B',green='#4B987D';
 function svg(body){return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 160"><defs><linearGradient id="lin"><stop stop-color="#E8F1FB"/><stop offset="1" stop-color="#B1A1EC"/></linearGradient><radialGradient id="rad"><stop stop-color="white"/><stop offset="1" stop-color="#85A9F1"/></radialGradient><linearGradient id="multi"><stop stop-color="#85A9F1"/><stop offset=".5" stop-color="#B1A1EC"/><stop offset="1" stop-color="#F4819B"/></linearGradient><pattern id="pat" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="8" cy="8" r="2" fill="#85A9F1"/></pattern><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="none" stroke="#4B83C9" stroke-width="2"/></marker><clipPath id="clip"><circle cx="200" cy="80" r="65"/></clipPath><mask id="mask"><rect width="400" height="160" fill="url(#lin)"/></mask></defs>${body}</svg>`;}
 const line=(d,extra='')=>`<path d="${d}" fill="none" stroke="${blue}" stroke-width="4" ${extra}/>`;
 const text=(x,y,t,size=21)=>`<text x="${x}" y="${y}" font-size="${size}" fill="${ink}">${t}</text>`;
 const circle=(x,y,r,fill=blue)=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}"/>`;
 const rect=(x,y,w,h,fill=blue,rx=12)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}"/>`;
 const html=(content,css='')=>`<div class="html-example" style="${css}">${content}</div>`;
 const box=(content,css='')=>`<div style="border:1px solid #A3B5CC;border-radius:16px;background:white;padding:18px;${css}">${content}</div>`;
 function picture(id){
  switch(id){
   case'G01':return svg(line('M25 100L375 45')+text(30,145,'明确起点与终点'));
   case'G02':return svg(line('M25 110L120 40L220 110L370 40'));
   case'G03':return svg(line('M25 120Q200 -40 375 120')+line('M25 120L200 20L375 120','stroke-dasharray="5 8" opacity=".25"'));
   case'G04':return svg(line('M25 120C80 -30 300 210 375 25'));
   case'G05':return svg(line('M50 120A95 75 0 0 1 230 120')+line('M270 120A50 50 0 1 1 370 120'));
   case'G06':return svg(circle(95,80,58,'#E8F1FB')+`<ellipse cx="275" cy="80" rx="90" ry="46" fill="#FBE8ED" stroke="${pink}" stroke-width="3"/>`);
   case'G07':return svg(rect(30,30,150,100,'#E8F1FB',0)+rect(220,30,150,100,'#FBE8ED',24));
   case'G08':return svg(`<polygon points="40,130 100,20 165,130" fill="${blue}"/><polygon points="285,20 305,60 355,66 318,98 328,140 285,118 243,140 252,98 215,66 264,60" fill="${pink}"/>`);
   case'S01':return svg([1,3,6,8].map((w,i)=>line(`M70 ${25+i*35}L370 ${25+i*35}`,`style="stroke-width:${w}"`)+text(10,32+i*35,w+'px',17)).join(''));
   case'S02':return svg(['butt','round','square'].map((c,i)=>line(`M70 ${30+i*50}L350 ${30+i*50}`,`style="stroke-width:8;stroke-linecap:${c}"`)).join(''));
   case'S03':return svg(['bevel','round','miter'].map((c,i)=>line(`M${25+i*130} 125L${75+i*130} 30L${125+i*130} 125`,`style="stroke-width:8;stroke-linejoin:${c}"`)).join(''));
   case'S04':return svg(line('M20 40L380 40','stroke-dasharray="15 10"')+line('M20 85L380 85','stroke-dasharray="2 10" stroke-linecap="round"')+line('M20 130L380 130','stroke-dasharray="25 8 4 8"'));
   case'S05':return svg(line('M35 45L355 45','marker-end="url(#arr)"')+line('M35 120L355 120','marker-start="url(#arr)" marker-end="url(#arr)"'));
   case'S06':return svg(`<circle cx="105" cy="80" r="55" fill="white" stroke="${blue}" stroke-width="5"/><circle cx="285" cy="80" r="55" fill="#E8F1FB" stroke="${pink}" stroke-width="5"/>`);
   case'F01':return svg(rect(20,30,100,100,blue)+rect(150,30,100,100,pink)+rect(280,30,100,100,green));
   case'F02':return svg(rect(25,20,350,120,'url(#lin)'));
   case'F03':return svg(rect(25,20,350,120,'url(#rad)'));
   case'F04':return svg(rect(25,20,350,120,'url(#multi)'));
   case'F05':return svg(rect(25,20,350,120,'url(#pat)'));
   case'F06':return svg(`<circle cx="165" cy="80" r="62" fill="${blue}" opacity=".55"/><circle cx="235" cy="80" r="62" fill="${pink}" opacity=".55"/>`);
   case'E01':return html(box('轻微外阴影','width:260px;box-shadow:0 8px 20px #40557420'));
   case'E02':return html(box('内阴影与凹面','width:260px;background:#E8F1FB;box-shadow:inset 0 5px 12px #40557430'));
   case'E03':return html('<span style="filter:blur(3px);font-size:42px;color:#4B83C9">局部模糊示例</span>');
   case'E04':return html('<span style="border:2px solid #85A9F1;border-radius:18px;padding:18px;box-shadow:0 0 22px #85A9F1;color:#4B83C9">受控柔光</span>');
   case'E05':return html('<div style="position:absolute;width:240px;height:80px;background:linear-gradient(90deg,#F4819B,#85A9F1);transform:rotate(-15deg)"></div><div style="z-index:1;backdrop-filter:blur(16px);background:#ffffff70;border:1px solid white;border-radius:20px;padding:30px">背景模糊层</div>','position:relative;overflow:hidden');
   case'E06':return html(box('简单浮雕','width:260px;background:#E8F1FB;box-shadow:6px 6px 12px #40557420,-6px -6px 12px white'));
   case'E07':return html('<span style="position:absolute;left:95px;top:24px;width:100px;height:100px;background:#85A9F1;border-radius:50%"></span><span style="position:absolute;left:160px;top:24px;width:100px;height:100px;background:#F4819B;border-radius:50%;mix-blend-mode:multiply"></span>','position:relative;isolation:isolate');
   case'E08':return svg(`<defs><linearGradient id="fade"><stop stop-color="white"/><stop offset="1" stop-color="black"/></linearGradient><mask id="alpha-fade"><rect width="400" height="160" fill="url(#fade)"/></mask></defs><clipPath id="clip-small"><circle cx="95" cy="80" r="58"/></clipPath><g clip-path="url(#clip-small)">${rect(20,10,150,140,'url(#multi)',0)}</g><g mask="url(#alpha-fade)">${rect(200,20,180,120,blue,12)}</g>`);
   case'T01':return html('<div><b style="font-size:38px">标题 38px</b><div style="font-size:24px">正文 24px</div><div style="font-size:18px;color:#7D8BA1">说明 18px</div></div>');
   case'T02':return html('<p>用<span style="color:#DC527D;font-weight:bold">重点颜色</span>与<br><span style="text-decoration:underline;text-decoration-color:#F4819B;text-decoration-thickness:4px">下划线</span>表达强调</p>');
   case'T03':return html('<p style="width:310px;line-height:1.7;margin:0">正文按容器宽度换行。<br>行距、字距、对齐都由代码统一控制。</p>');
   case'T04':return html('<span style="padding:12px 20px;background:#E8F1FB;border-radius:26px">过程标签</span><span style="padding:12px 18px;background:#FBE8ED;border-radius:16px;margin-left:16px">01</span>');
   case'T05':return html('<span style="font-size:32px">H<sub>2</sub>O　x<sup>2</sup> + y<sup>2</sup> = r<sup>2</sup></span>');
   case'T06':return svg(`<path id="tp" d="M35 120Q200 10 365 120" fill="none" stroke="#A3B5CC"/><text font-size="23" fill="${ink}"><textPath href="#tp" startOffset="12%">文字可沿确定曲线排布</textPath></text>`);
   case'L01':return html(box('<b style="display:block;font-size:25px">知识点标题</b><span style="font-size:20px">准确内容与简洁说明</span>','width:330px;background:linear-gradient(105deg,white,#FBE8ED)'));
   case'L02':return html(box('<b>分组</b>'+box('子对象 A　子对象 B','padding:12px;margin-top:10px;background:#E8F1FB'),'width:340px;padding:16px'));
   case'L03':return html('<div style="display:grid;grid-template-columns:repeat(3,90px);gap:14px">'+Array.from({length:6},(_,i)=>box(String(i+1),'padding:6px;text-align:center;background:#E8F1FB')).join('')+'</div>');
   case'L04':return svg(line('M40 80L360 80')+[60,200,340].map((x,i)=>circle(x,80,14,[blue,pink,green][i])+text(x-28,130,'步骤'+(i+1),18)).join(''));
   case'L05':return svg(`<circle cx="100" cy="80" r="35" fill="none" stroke="${pink}" stroke-width="3"/>`+line('M135 80L200 45L350 45')+text(200,35,'指向真实对象',18));
   case'L06':return svg([25,155,285].map((x,i)=>rect(x,50,90,60,['#E8F1FB','#FBE8ED','#E7F3EC'][i])+text(x+20,86,['输入','过程','结果'][i],18)).join('')+line('M120 80L147 80','marker-end="url(#arr)"')+line('M250 80L278 80','marker-end="url(#arr)"'));
   case'D01':return svg(line('M35 15L35 140L380 140')+[80,150,220,290].map((x,i)=>rect(x,140-[60,110,80,95][i],40,[60,110,80,95][i],blue,3)).join(''));
   case'D02':return svg(line('M35 15L35 140L380 140')+line('M55 115L120 75L190 92L260 40L340 60')+[55,120,190,260,340].map((x,i)=>circle(x,[115,75,92,40,60][i],5,pink)).join(''));
   case'D03':return svg(`<path d="M35 140L55 115L120 75L190 92L260 40L340 60L340 140Z" fill="#E8F1FB"/>`+line('M55 115L120 75L190 92L260 40L340 60'));
   case'D04':return svg(`<circle cx="110" cy="80" r="55" fill="#E8F1FB"/><path d="M110 80L110 25A55 55 0 0 1 162 97Z" fill="${pink}"/><circle cx="290" cy="80" r="49" fill="none" stroke="#E8F1FB" stroke-width="20"/><circle cx="290" cy="80" r="49" fill="none" stroke="${blue}" stroke-width="20" stroke-dasharray="190 400" transform="rotate(-90 290 80)"/>`);
   case'D05':return svg(rect(25,55,350,40,'#E8F1FB',20)+rect(25,55,245,40,blue,20)+text(160,130,'70%　数据驱动'));
   case'D06':return svg(line('M70 80L200 30L330 80L200 135L70 80')+line('M70 80L330 80')+[[70,80],[200,30],[330,80],[200,135]].map(([x,y])=>circle(x,y,19,blue)).join(''));
   default:return '';
  }
 }
 function canvasDraw(canvas,id,t){const c=canvas.getContext('2d');c.clearRect(0,0,400,160);c.strokeStyle=blue;c.lineWidth=3;
  if(id==='C01'){for(let i=0;i<36;i++){const x=25+((i*79+t*80)%350),y=22+((i*43)%118);c.fillStyle=i%3?blue:pink;c.beginPath();c.arc(x,y,3+i%4,0,Math.PI*2);c.fill();}}
  if(id==='C02'||id==='C03'){c.beginPath();for(let x=10;x<390;x++){const y=80+Math.sin(x/28-t*3)*(id==='C02'?38:25);x===10?c.moveTo(x,y):c.lineTo(x,y);}c.stroke();if(id==='C03'){for(let i=0;i<18;i++){const x=40+i*18;c.globalAlpha=(i+1)/18;c.fillStyle=pink;c.beginPath();c.arc(x,80+Math.sin(x/28-t*3)*25,5,0,Math.PI*2);c.fill();}c.globalAlpha=1;}}
  if(id==='C04'){for(let y=0;y<5;y++)for(let x=0;x<10;x++){const v=(x+y)%7;c.fillStyle=`hsl(${210-v*15} 68% ${86-v*6}%)`;c.fillRect(10+x*38,5+y*30,34,25);}}
  if(id==='C05'){c.strokeStyle='#E8F1FB';c.beginPath();c.moveTo(20,130);c.bezierCurveTo(110,-20,240,180,380,20);c.stroke();c.strokeStyle=pink;c.beginPath();for(let k=0;k<=t*100;k++){const a=k/100,b=1-a,x=b*b*b*20+3*b*b*a*110+3*b*a*a*240+a*a*a*380,y=b*b*b*130+3*b*b*a*(-20)+3*b*a*a*180+a*a*a*20;k?c.lineTo(x,y):c.moveTo(x,y);}c.stroke();}
  if(id==='C06'){for(let i=0;i<5;i++){c.fillStyle=[blue,pink,green][i%3];c.fillRect(30+i*60+t*30,55,35,50);}}
 }
 function motion(id,t){const x=70+80*t;let body='';
  if(id==='M01')body=`<g opacity="${t}">${rect(40,40,70,70,pink)}</g>`;
  if(id==='M02')body=rect(10+70*t,45,60,60,blue);
  if(id==='M03')body=`<g transform="translate(70 80) scale(${.8+.4*t})">${rect(-30,-30,60,60,pink)}</g>`;
  if(id==='M04')body=`<g transform="rotate(${90*t} 70 80)">${rect(40,50,60,60,green,3)}</g>`;
  if(id==='M05')body=line('M15 100Q70 10 125 100',`pathLength="1" stroke-dasharray="1" stroke-dashoffset="${1-t}"`);
  if(id==='M06')body=`<clipPath id="reveal-${Math.round(t*100)}"><rect width="${140*t}" height="160"/></clipPath><g clip-path="url(#reveal-${Math.round(t*100)})">${rect(15,35,110,85,'url(#lin)')}</g>`;
  if(id==='M07')body=`<path d="M15 100Q70 ${100-85*t} 125 100L125 130L15 130Z" fill="#85A9F1"/>`;
  if(id==='M08')body=text(35,95,String(Math.round(t*100)),38);
  if(id==='M09'){const a=1-t;body=line('M15 115Q70 10 125 115','opacity=".35"')+circle(a*a*15+2*a*t*70+t*t*125,a*a*115+2*a*t*10+t*t*115,10,pink);}
  return `<div class="phase">${svg(body).replace('0 0 400 160','0 0 140 160')}<span>${Math.round(t*100)}%</span></div>`;
 }
 function render(){document.querySelectorAll('[data-effect]').forEach(el=>{const id=el.dataset.effect;if(id.startsWith('C')){const c=el.querySelector('canvas');canvasDraw(c,id,Number(window.progress||.75));}else if(id.startsWith('M'))el.innerHTML=[0,.5,1].map(t=>motion(id,t)).join('');else el.innerHTML=picture(id);});}
 window.renderEffects=render;render();window.demoReady=true;
}

(async()=>{
 const out=path.resolve(process.argv[2]);fs.mkdirSync(out,{recursive:true});
 const sheets=[['01','几何、路径与描边',['G','S']],['02','填充、阴影、滤镜与合成',['F','E']],['03','文字、标识与信息组合',['T','L']],['04','数据与Canvas二维示意',['D','C']],['05','运动与状态：起始/中间/结束',['M']]];
 const css=`*{box-sizing:border-box}body{margin:0;background:#EEF1F6;color:#405574;font:22px "Microsoft YaHei"}nav{padding:24px}nav a{margin-right:24px;color:#405574}.sheet{width:2048px;padding:36px;background:#FBFAF8;margin:20px auto}.sheet h1{font-size:36px;margin:0 0 8px}.subtitle{font-size:21px;margin:0 0 20px;color:#52647C}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.tile{border:1px solid #A3B5CC;border-radius:18px;background:white;padding:16px;height:270px}.tile h2{font-size:23px;margin:0 0 6px}.meta{font-size:17px;margin:0 0 4px;color:#52647C}.denied{color:#B85270}.example{height:165px;display:flex;align-items:center;justify-content:center}.example svg{width:100%;height:155px;font-family:"Microsoft YaHei"}.html-example{width:100%;height:150px;display:flex;align-items:center;justify-content:center;font-size:24px}canvas{width:100%;height:155px}.phase{width:33.33%;height:165px;text-align:center}.phase svg{height:135px}.phase span{font-size:18px}.footer{font-size:19px;color:#52647C;margin:24px 0 0;line-height:1.5}`;
 const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>固定二维效果集合 v0.1.0</title><style>${css}</style><nav>真实 HTML / CSS / SVG / Canvas 效果演示　${sheets.map(([id,title])=>`<a href="#s${id}">${title}</a>`).join('')}<label>Canvas时间 <input type="range" min="0" max="1" step=".01" value=".75" oninput="window.progress=Number(this.value);renderEffects()"></label></nav>${sheets.map(([id,title,prefixes])=>`<section class="sheet" id="s${id}"><h1>${id}　${title}</h1><p class="subtitle">固定效果集合 v0.1.0｜此页是真实浏览器截图，不是AI效果图｜编号用于模型精确选择</p><div class="grid">${catalog.effects.filter(e=>prefixes.includes(e.id[0])).map(e=>`<article class="tile"><h2>${e.id}　${e.name}</h2><p class="meta ${e.allowed_for_demo_style?'':'denied'}">${e.backend} · ${e.allowed_for_demo_style?'本次风格允许':'可实现，但本次风格禁用'}</p><div class="example" data-effect="${e.id}">${e.id[0]==='C'?'<canvas width="400" height="160"></canvas>':''}</div></article>`).join('')}</div><p class="footer">参数边界：${groups.filter(g=>prefixes.includes(g[0])).map(g=>g[3]).join(' ')}<br>能力示例≠应用已集成组件；图片负责独立插画，代码负责文字、图形、关系、数据及可控运动。参考图说明文字不进入最终画面。</p></section>`).join('')}<script>(${browserDemo.toString()})();</script></html>`;
 fs.writeFileSync(path.join(out,'effects-demo.html'),html);fs.writeFileSync(path.join(out,'effects-catalog.json'),JSON.stringify(catalog,null,2));
 const browser=await chromium.launch({headless:true,executablePath:process.env.HPS_CHROME||'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe'});
 const evidence={effects:catalog.effects.length,errors:[],sheets:[],canvas:[],motionFrames:[0,.5,1],status:'browser demonstration only'};
 try{
  const page=await browser.newPage({viewport:{width:2100,height:1600},deviceScaleFactor:1});page.on('pageerror',e=>evidence.errors.push(e.message));
  await page.goto(pathToFileURL(path.join(out,'effects-demo.html')).href);await page.waitForFunction(()=>window.demoReady);await page.evaluate(()=>document.fonts.ready);
  const missing=await page.locator('[data-effect]').evaluateAll(els=>els.filter(el=>!el.children.length).map(el=>el.dataset.effect));if(missing.length)throw new Error('Missing render: '+missing.join(','));
  evidence.canvas=await page.locator('canvas').evaluateAll(cs=>cs.map(c=>({nontransparentPixels:Array.from(c.getContext('2d').getImageData(0,0,c.width,c.height).data).filter((v,i)=>i%4===3&&v>0).length})));
  if(evidence.canvas.some(c=>!c.nontransparentPixels))throw new Error('Canvas render empty');
  for(const [id,title]of sheets){const file=`effects-${id}.png`;await page.locator('#s'+id).screenshot({path:path.join(out,file)});evidence.sheets.push({file,title,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,file))).digest('hex')});}
  for(const t of [0,.5,1]){await page.evaluate(t=>{window.progress=t;renderEffects();},t);await page.locator('#s04').screenshot({path:path.join(out,`canvas-frame-${t}.png`)});}
  if(evidence.errors.length)throw new Error(evidence.errors.join(';'));
  evidence.passed=true;fs.writeFileSync(path.join(out,'render-evidence.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify({effects:catalog.effects.length,allowed:catalog.effects.filter(e=>e.allowed_for_demo_style).length,sheets:5,passed:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
