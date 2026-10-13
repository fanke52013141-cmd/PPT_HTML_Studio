"use strict";
// Isolated old renderer bundle for a controlled geometry regression comparison.
const fs = require("node:fs"), path = require("node:path");
const root = path.resolve(__dirname, "..");
const out = path.join(root, "outputs/token-flow-audit-20261014");
const visual = path.join(root, "html_engine/visual");
const target = path.join(out, "baseline-player");
fs.mkdirSync(target, {recursive:true});
for (const file of ["data.js", "index.html"]) fs.copyFileSync(path.join(visual, "preview", file), path.join(target, file));
require(path.join(root, "html_engine/node_modules/esbuild")).build({
  entryPoints: [path.join(visual, "player.cjs")], outfile:path.join(target, "player.js"), bundle:true,
  platform:"browser", plugins:[{name:"preserved-renderer", setup(build) {
    build.onLoad({filter:/renderer\.cjs$/}, args => args.path === path.join(visual,"renderer.cjs")
      ? {contents:fs.readFileSync(path.join(out,"renderer-before.cjs"),"utf8"), loader:"js", resolveDir:visual} : null);
  }}],
}).catch(error=>{console.error(error);process.exitCode=1;});
