const {chromium}=require('../../node_modules/playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
(async()=>{const browser=await chromium.launch({executablePath:process.env.HPS_CHROME});try{const page=await browser.newPage({viewport:{width:1600,height:1000},deviceScaleFactor:1});await page.goto(pathToFileURL(path.join(__dirname,'atlas.html')).href);await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(__dirname,'atlas.png')});}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
