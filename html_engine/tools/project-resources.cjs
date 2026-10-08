"use strict";
// Project resources are bytes, never executable code. Resolve only inside the run.
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const { PNG } = require("pngjs");
function loadProjectResources() {
  const filename = process.env.HPS_HTML_RESOURCES;
  if (!filename) return null;
  const manifestPath = fs.realpathSync(filename);
  const run = fs.realpathSync(path.resolve(path.dirname(manifestPath), "../.."));
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const assets = [], pack = {};
  for (const entry of manifest.assets || []) {
    const actual = fs.realpathSync(path.resolve(run, entry.file));
    if (!actual.startsWith(run + path.sep)) throw new Error("ASSET_PATH_ESCAPE");
    const bytes = fs.readFileSync(actual);
    if (bytes.length > 8 * 1024 * 1024) throw new Error("ASSET_BYTE_BUDGET");
    if (crypto.createHash("sha256").update(bytes).digest("hex") !== entry.sha256)
      throw new Error("ASSET_HASH_MISMATCH");
    if(bytes.length<24 || bytes.toString("hex",0,8)!=="89504e470d0a1a0a" || bytes.readUInt32BE(16)*bytes.readUInt32BE(20)>4194304) throw new Error("ASSET_PNG_DIMENSIONS");
    const png = PNG.sync.read(bytes);
    if (png.width * png.height > 4194304) throw new Error("ASSET_PIXEL_BUDGET");
    let minX=png.width,minY=png.height,maxX=-1,maxY=-1;
    for(let py=0;py<png.height;py++) for(let px=0;px<png.width;px++)
      if(png.data[(py*png.width+px)*4+3]>0){minX=Math.min(minX,px);minY=Math.min(minY,py);maxX=Math.max(maxX,px);maxY=Math.max(maxY,py);}
    if(maxX<0) throw new Error("ASSET_EMPTY");
    const actualBox=[minX,minY,maxX+1,maxY+1];
    if(JSON.stringify(actualBox)!==JSON.stringify(entry.alpha_bbox)) throw new Error("ASSET_ALPHA_BBOX_MISMATCH");
    if(assets.some(a=>a.id===entry.id)) throw new Error("ASSET_DUPLICATE");
    for(const a of entry.anchors || []) if(!Number.isInteger(a.x)||!Number.isInteger(a.y)||a.x<0||a.y<0||a.x>=png.width||a.y>=png.height) throw new Error("ASSET_ANCHOR_INVALID");
    const [x,y,r,b] = actualBox;
    const relative = `project/${entry.file}`;
    assets.push({id:entry.id, version:entry.version,
      file:{path:relative, mimeType:"image/png", sha256:entry.sha256},
      intrinsic:{width:png.width,height:png.height},
      alphaBounds:{x,y,width:r-x,height:b-y},
      anchors:entry.anchors.map(a=>({id:a.id,x:a.x/png.width,y:a.y/png.height}))});
    pack[relative] = bytes.toString("base64");
  }
  return { assets, pack };
}
module.exports = { loadProjectResources };
