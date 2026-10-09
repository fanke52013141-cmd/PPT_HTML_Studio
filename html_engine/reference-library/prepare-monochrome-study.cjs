"use strict";
const fs=require("fs"), path=require("path"), {pathToFileURL}=require("url"), {chromium}=require("../node_modules/playwright");
const destination=path.resolve(__dirname,"../../outputs/static-reference/monochrome-beauty-v1");
(async()=>{
  fs.mkdirSync(destination,{recursive:true});
  const browser=await chromium.launch({headless:true,executablePath:process.env.HPS_CHROME});
  try {
    const page=await browser.newPage({viewport:{width:2080,height:1200}});
    await page.goto(pathToFileURL(path.join(__dirname,"components.html")).href);
    await page.waitForFunction(()=>window.ComponentAtlas?.ready);
    await page.evaluate(()=>{
      const n=(tag,cls,value)=>{const e=document.createElement(tag);e.className=cls;if(value)e.textContent=value;return e;};
      const board=n("article","board component-reference");board.id="monochrome-study";
      board.style.cssText="width:1920px;height:1080px;padding:48px 64px;filter:grayscale(1);--ink:#222;--muted:#666;--accent:#444;--tint:#f4f4f4;--line:#ddd";
      const header=n("header","board-header");const title=n("div","");title.append(n("h1","","基础组件 · 黑白灰美感研究"),n("p","","改善比例、字阶、留白与层次；配色随后依据风格参考单独应用。"));header.append(title);board.append(header);
      const grid=n("div","study-grid");
      const groups=[
        ["01 标题组",[["T01","让重点被看见"],["T02","清楚的层次，舒适的阅读"]]],
        ["02 正文与解释",[["T04","准确的信息，需要清楚的表达。"],["T05","用留白、比例与层次帮助理解。"]]],
        ["03 普通卡片",[["C03","清楚的结构"]]],
        ["04 编号卡片",[["C04","建立重点"]]],
        ["05 箭头与关系",[["A01",undefined],["R01",undefined]]],
        ["06 标签与强调",[["N01","分类标签"],["T07","重要的信息"]]]
      ];
      for(const [label,items] of groups){const cell=n("section","study-cell");const preview=n("div","study-preview");items.forEach(([id,value])=>preview.append(window.ComponentAtlas.render(id,value)));cell.append(n("h2","",label),preview);grid.append(cell);}
      board.append(grid);board.style.margin="0";document.body.style.background="#fff";document.body.replaceChildren(board);
    });
    await page.addStyleTag({content:".study-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px 36px}.study-cell{border-top:1px solid #ddd;padding:18px 24px;height:355px}.study-cell h2{font-size:20px;font-weight:500;color:#555;margin:0}.study-preview{height:285px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:24px}#monochrome-study .study-preview .explain{max-width:410px}#monochrome-study .study-preview .body{max-width:440px}#monochrome-study .study-preview .title{font-size:44px}"});
    await page.evaluate(()=>document.fonts.ready);
    const overflow=await page.locator(".study-preview").evaluateAll(elements=>elements.flatMap(e=>{
      const box=e.getBoundingClientRect();return [...e.querySelectorAll(".component")].filter(c=>{const r=c.getBoundingClientRect();return r.left<box.left || r.right>box.right || r.top<box.top || r.bottom>box.bottom;}).map(c=>c.dataset.componentId);
    }));
    if(overflow.length) throw Error("STUDY_OVERFLOW: "+overflow.join(","));
    await page.locator("#monochrome-study").screenshot({path:path.join(destination,"component-reference.png")});
    console.log(JSON.stringify({reference:path.join(destination,"component-reference.png"),dimensions:[1920,1080],groups:6,overflow}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
