"""Self-contained local reference correction UI; no network or author writes."""
import base64
from html import escape
import json
from pathlib import Path


def render_workbench(reference, screenshot, correction, image_size, targets, *, annotation_mode=False):
    images = ['data:image/png;base64,'+base64.b64encode(source.read_bytes()).decode('ascii')
              for source in (Path(reference), Path(screenshot))]
    data = json.dumps({'correction': correction, 'size': image_size, 'targets': targets,'annotationMode':annotation_mode}, ensure_ascii=False).replace('<', '\\u003c')
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>原图定位复核</title><style>body{font:16px/1.6 system-ui;margin:24px;color:#172033;background:#f8fafc}main{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;display:block}figure{margin:0;background:white;min-width:0}.viewport{overflow:auto;max-height:600px}.editor{background:white;border:1px solid #cbd5e1;padding:16px;margin:16px 0}.fields{display:flex;flex-wrap:wrap;gap:12px}.fields label{display:grid;gap:4px;min-width:0;max-width:100%}input,select{font:inherit;padding:6px;min-width:0;max-width:100%;box-sizing:border-box}.coords input{width:100px}#transcript{width:360px}#identity{width:480px}.hint{overflow-wrap:anywhere}#reference{width:100%}details{margin:16px 0}#reference{position:relative}.box{position:absolute;border:2px solid #dc2626;box-sizing:border-box;pointer-events:none;color:#b91c1c;font-size:12px}textarea{box-sizing:border-box;width:100%;height:360px;font:14px/1.5 monospace}button{padding:10px;margin:8px 8px 8px 0}#status{white-space:pre-wrap}@media(max-width:800px){main{grid-template-columns:1fr}.fields label{width:100%}#transcript,#identity{width:100%}}</style>
<h1>原图定位复核</h1><p>选择对象部件，在原图拖框，填写实际转录与身份依据后应用。嵌入主面板时可直接使用修正并提交审核；此操作不保存作者页面或批准视觉。</p><main>
<figure><figcaption>原图：红框为当前文字部件定位；坐标使用原图像素。</figcaption><div class="viewport"><div id="reference"><img alt="原图" src="''' + escape(images[0], quote=True) + '''"></div></div></figure>
<figure><figcaption>当前 HTML 截图</figcaption><img alt="当前HTML截图" src="''' + escape(images[1], quote=True) + '''"></figure></main>
<p>拖框后先应用到所选文字部件；如有边框背景，再选择“框选容器”核对容器边界。服务端会检查对象身份、完整性、准确文字和范围。</p>
<section class="editor"><div class="fields"><label>对象 / 部件<select id="part"></select></label><label>文字区域<select id="region"></select></label><label>查看比例<select id="zoom"><option value="100">适应窗口</option><option value="150">150%</option><option value="200">200%</option></select></label><label>导入修正文件<input id="import" type="file" accept="application/json,.json"></label></div>
<p id="expected" class="hint"></p><div class="fields"><label>图上实际转录<input id="transcript" maxlength="300"></label><label>身份依据<input id="identity" maxlength="300"></label></div>
<div class="fields coords"><label>左 x<input id="xPx" type="number" min="0" step="1"></label><label>上 y<input id="yPx" type="number" min="0" step="1"></label><label>宽<input id="widthPx" type="number" min="1" step="1"></label><label>高<input id="heightPx" type="number" min="1" step="1"></label></div>
<button id="apply">应用文字框</button><button id="add">新增文字区域</button><button id="remove">删除文字区域</button><button id="absent">对象未找到</button><button id="uncertain">对象不确定</button>
<details><summary>容器边界</summary><div class="fields coords"><label>容器状态<select id="container"><option value="absent">无容器</option><option value="present">有容器</option><option value="uncertain">不确定</option></select></label><label>左 x<input id="cx" type="number" min="0" step="1"></label><label>上 y<input id="cy" type="number" min="0" step="1"></label><label>宽<input id="cw" type="number" min="1" step="1"></label><label>高<input id="ch" type="number" min="1" step="1"></label></div><button id="apply-container">应用容器</button></details></section>
<details><summary>高级 JSON 编辑</summary><label for="mapping">定位数据</label><textarea id="mapping" spellcheck="false"></textarea></details><button id="preview">更新红框</button><button id="download">下载修正文件</button><p id="status" role="status"></p>
<script type="application/json" id="data">''' + data + '''</script><script>
const data=JSON.parse(document.getElementById('data').textContent),input=document.getElementById('mapping'),status=document.getElementById('status');
const el=id=>document.getElementById(id),keys=['xPx','yPx','widthPx','heightPx'];
input.value=JSON.stringify(data.correction,null,2);
function read(){const c=JSON.parse(input.value);if(c.session_sha256!==data.correction.session_sha256)throw Error('会话不匹配');if(!c.mapping||!Array.isArray(c.mapping.targets))throw Error('缺少对象清单');return c;}
function selection(c){const [i,j]=el('part').value.split(':').map(Number);return {row:c.mapping.targets[i],part:c.mapping.targets[i].part_regions[j]};}
function box(values){const b=Object.fromEntries(keys.map((k,i)=>[k,Number(values[i])]));if(values.some(v=>String(v).trim()==='')||!keys.every(k=>Number.isSafeInteger(b[k]))||b.xPx<0||b.yPx<0||b.widthPx<=0||b.heightPx<=0||b.xPx+b.widthPx>data.size[0]||b.yPx+b.heightPx>data.size[1])throw Error('框须为原图内的整数像素');return b;}
function sync(){const c=read(),old=el('part').value;el('part').replaceChildren();for(const [i,row]of c.mapping.targets.entries()){for(const [j,p]of row.part_regions.entries()){const option=document.createElement('option');option.value=i+':'+j;option.textContent=row.targetId+' / '+p.partId+' · '+p.status;el('part').appendChild(option);}}if([...el('part').options].some(o=>o.value===old))el('part').value=old;loadPart();}
function loadPart(){const {row,part}=selection(read()),expected=data.targets.find(t=>t.targetId===row.targetId)?.text_parts.find(p=>p.partId===part.partId)?.text;el('expected').textContent='准确来源：'+(expected??'请核对原文')+'；请按图上实际文字转录。';el('identity').value=row.identity_evidence??'';el('region').replaceChildren();for(let i=0;i<Math.max(part.regions.length,1);i++){const option=document.createElement('option');option.value=String(i);option.textContent=part.regions.length?'区域 '+(i+1):'新区域';el('region').appendChild(option);}const b=row.container_box;el('container').value=row.container_presence;['cx','cy','cw','ch'].forEach((k,i)=>el(k).value=b?b[keys[i]]:'');loadRegion();}
function loadRegion(){const {part}=selection(read()),region=part.regions[Number(el('region').value)];el('transcript').value=region?.text??'';for(const k of keys)el(k).value=region?region.box[k]:'';}
function preview(){try{const c=read(),root=el('reference');root.querySelectorAll('.box').forEach(n=>n.remove());for(const row of c.mapping.targets){const regions=row.part_regions.flatMap(p=>p.regions.map(r=>({label:p.partId,box:r.box})));if(row.container_box)regions.push({label:'container',box:row.container_box});for(const r of regions){const b=box(keys.map(k=>r.box[k])),n=document.createElement('div');n.className='box';n.textContent=row.targetId+'/'+r.label;Object.assign(n.style,{left:(b.xPx/data.size[0]*100)+'%',top:(b.yPx/data.size[1]*100)+'%',width:(b.widthPx/data.size[0]*100)+'%',height:(b.heightPx/data.size[1]*100)+'%'});root.appendChild(n);}}status.textContent='预览已更新；导入时仍须通过来源和完整性检查。';return true;}catch(e){status.textContent='JSON或定位无效：'+e.message;return false;}}
function save(c){input.value=JSON.stringify(c,null,2);sync();preview();}
function action(fn){try{fn();}catch(e){status.textContent=e.message;}}
el('part').onchange=()=>action(loadPart);el('region').onchange=()=>action(loadRegion);
el('apply').onclick=()=>action(()=>{const c=read(),{row,part}=selection(c),b=box(keys.map(k=>el(k).value)),text=el('transcript').value,evidence=el('identity').value.trim();if(!text.trim()||!evidence)throw Error('请输入实际转录和身份依据');part.regions[Number(el('region').value)]={text,box:b};part.status='located';row.status='located';row.identity_evidence=evidence;save(c);if(row.part_regions.some(p=>p.status!=='located'))status.textContent='已应用；该对象还有未定位部件，请继续补齐后导入。';});
el('add').onclick=()=>action(()=>{const {part}=selection(read()),option=document.createElement('option');if(part.regions.length>=12)throw Error('每部件最多12个区域');option.value=String(part.regions.length);option.textContent='新区域';el('region').appendChild(option);el('region').value=option.value;loadRegion();});
el('remove').onclick=()=>action(()=>{const c=read(),{row,part}=selection(c);part.regions.splice(Number(el('region').value),1);if(!part.regions.length){part.status='not_found';row.status='located';}save(c);});
function unresolved(value){const c=read(),{row}=selection(c);row.status=value;row.container_presence=value==='not_found'?'absent':'uncertain';row.container_box=null;for(const p of row.part_regions){p.status=value;p.regions=[];}row.identity_evidence=el('identity').value.trim()||null;save(c);}
el('absent').onclick=()=>action(()=>unresolved('not_found'));el('uncertain').onclick=()=>action(()=>unresolved('ambiguous'));
el('apply-container').onclick=()=>action(()=>{const c=read(),{row}=selection(c);row.container_presence=el('container').value;row.container_box=row.container_presence==='present'?box(['cx','cy','cw','ch'].map(k=>el(k).value)):null;save(c);});
el('zoom').onchange=()=>el('reference').style.width=el('zoom').value+'%';
el('preview').onclick=()=>{if(preview())action(sync);};
el('import').onchange=async()=>{try{const file=el('import').files[0];if(!file)return;if(file.size>1000000)throw Error('修正文件超过1MB');const c=JSON.parse(await file.text());if(c.session_sha256!==data.correction.session_sha256)throw Error('导入文件属于其他会话');const signature=v=>JSON.stringify(v.mapping.targets.map(r=>[r.targetId,r.part_regions.map(p=>p.partId)]));if(signature(c)!==signature(data.correction))throw Error('对象或部件身份不匹配');input.value=JSON.stringify(c,null,2);sync();preview();}catch(e){status.textContent='导入失败：'+e.message;}};
el('download').onclick=()=>action(()=>{const c=read();const signature=v=>JSON.stringify(v.mapping.targets.map(r=>[r.targetId,r.part_regions.map(p=>p.partId)]));if(signature(c)!==signature(data.correction))throw Error('对象或部件身份不匹配');if(!preview())return;for(const row of c.mapping.targets){if(row.status==='located'&&row.part_regions.some(p=>p.status!=='located'||!p.regions.length))throw Error('请补齐该对象所有文字部件：'+row.targetId);}const u=URL.createObjectURL(new Blob([JSON.stringify(c,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='correction.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
// Pointer coordinates are original-image pixels, independent of zoom/scroll.
const mode=document.createElement('select');mode.id='draw-mode';mode.setAttribute('aria-label','框选类型');
for(const [value,text]of [['text','框选文字区域'],['container','框选容器']]){const o=document.createElement('option');o.value=value;o.textContent=text;mode.append(o);}
const use=document.createElement('button');use.id='use-correction';use.textContent='使用修正，返回主面板';use.hidden=true;
el('part').parentElement.parentElement.append(mode,use);
el('reference').style.touchAction='none';el('reference').querySelector('img').draggable=false;let drag=null,channel=null;
function point(event){const r=el('reference').getBoundingClientRect();return [Math.max(0,Math.min(data.size[0],Math.round((event.clientX-r.left)/r.width*data.size[0]))),Math.max(0,Math.min(data.size[1],Math.round((event.clientY-r.top)/r.height*data.size[1])))];}
el('reference').addEventListener('pointerdown',event=>{if(event.button!==0)return;drag=point(event);el('reference').setPointerCapture(event.pointerId);event.preventDefault();});
el('reference').addEventListener('pointercancel',()=>{drag=null;});
el('reference').addEventListener('pointermove',event=>{if(!drag)return;const end=point(event);let n=el('reference').querySelector('[data-drag-preview]');if(!n){n=document.createElement('div');n.className='box';n.dataset.dragPreview='';el('reference').append(n);}Object.assign(n.style,{left:(Math.min(drag[0],end[0])/data.size[0]*100)+'%',top:(Math.min(drag[1],end[1])/data.size[1]*100)+'%',width:(Math.abs(end[0]-drag[0])/data.size[0]*100)+'%',height:(Math.abs(end[1]-drag[1])/data.size[1]*100)+'%'});});
el('reference').addEventListener('pointerup',event=>action(()=>{if(!drag)return;const end=point(event),start=drag;drag=null;
const b=box([Math.min(start[0],end[0]),Math.min(start[1],end[1]),Math.abs(end[0]-start[0]),Math.abs(end[1]-start[1])]);
const fields=mode.value==='container'?['cx','cy','cw','ch']:keys;fields.forEach((k,i)=>el(k).value=b[keys[i]]);
if(mode.value==='container')el('container').value='present';status.textContent='框已读取；请核对实际转录与身份后点击应用。';}));
window.addEventListener('message',event=>{const m=event.data;if(parent===window||event.source!==parent||m?.type!=='ppt-reference-init'||m.session!==data.correction.session_sha256||typeof m.nonce!=='string'||m.nonce.length<16)return;channel={nonce:m.nonce,session:m.session};use.hidden=false;});
use.onclick=()=>action(()=>{const c=read();if(!preview())return;const signature=v=>JSON.stringify(v.mapping.targets.map(r=>[r.targetId,r.part_regions.map(p=>p.partId)]));if(signature(c)!==signature(data.correction))throw Error('对象或部件身份不匹配');if(!data.annotationMode)for(const row of c.mapping.targets){if(row.status==='located'&&row.part_regions.some(p=>p.status!=='located'||!p.regions.length))throw Error('请补齐所有文字部件');}if(channel){parent.postMessage({type:'ppt-reference-correction',...channel,correction:c},'*');status.textContent='修正已发送主面板；请在主面板显式提交审核。';}});
action(sync);preview();
</script></html>'''
    if annotation_mode:
        html=html.replace('当前 HTML 截图','标注仅核对原图').replace('原图定位复核','评测原图标注')
        html=html.replace('<h1>评测原图标注</h1>', '<style>main{grid-template-columns:1fr}main figure+figure{display:none}</style><h1>评测原图标注</h1>')
        html=html.replace('使用修正，返回主面板','使用标注，返回工作台')
        html=html.replace('嵌入主面板时可直接使用修正并提交审核；此操作不保存作者页面或批准视觉。','使用标注后在工作台保存草稿，再由独立复核者审核；此操作不批准生产画面。')
        html=html.replace('修正已发送主面板；请在主面板显式提交审核。','标注已发送工作台；请填写标注者并保存草稿。')
    return html
