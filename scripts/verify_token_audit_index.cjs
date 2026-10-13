"use strict";
const fs = require("node:fs"), path = require("node:path"), {pathToFileURL} = require("node:url");
const root = path.resolve(__dirname,"..");
const out = path.join(root,"outputs/token-flow-audit-20261014");
const playwright = require(path.join(root,"html_engine/node_modules/playwright"));
(async()=>{
  const browser = await playwright.chromium.launch({headless:true,
    executablePath:require(path.join(root,"html_engine/tools/browser-runtime.cjs")).resolveBrowser(playwright.chromium)});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1080}});
    const errors=[];
    page.on("pageerror",error=>errors.push(String(error)));
    await page.goto(pathToFileURL(path.join(out,"index.html")).href);
    await page.waitForFunction(()=>[...document.images].every(image=>image.complete && image.naturalWidth>0));
    await page.locator("details").first().locator("summary").click();
    await page.locator('input[type=range]').first().evaluate(input=>{input.value=75;input.dispatchEvent(new Event("input",{bubbles:true}));});
    const clip=await page.locator('.top').first().evaluate(image=>image.style.clipPath);
    if(clip!=="inset(0px 25% 0px 0px)" && clip!=="inset(0 25% 0 0)") throw new Error("Slider comparison failed: "+clip);
    await page.locator("details").first().locator("summary").click();
    await page.screenshot({path:path.join(out,"viewer.png")});
    const broken=[];
    for(const href of await page.locator("a[href]").evaluateAll(links=>links.map(link=>link.getAttribute("href")))) {
      if(!href.startsWith("http") && !fs.existsSync(path.resolve(out,href))) broken.push(href);
    }
    const report={images:await page.locator("img").count(),browserErrors:errors,brokenLinks:broken,sliderVerified:true};
    fs.writeFileSync(path.join(out,"viewer-check.json"),JSON.stringify(report,null,2));
    if(errors.length || broken.length) throw new Error(JSON.stringify(report));
    console.log(JSON.stringify(report));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
