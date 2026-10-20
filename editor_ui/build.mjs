import { build } from 'esbuild';
import { readFile, writeFile, mkdir, stat, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { existsSync } from 'node:fs';

const root = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(root, '../static/editor_ui');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
await mkdir(output, { recursive: true });
await build({ entryPoints: [path.join(root, 'src/index.jsx')], bundle: true,
  outfile: path.join(output, 'editor.js'), format: 'iife', globalName: 'HtmlEditorUI',
  minify: true, target: ['chrome110'], legalComments: 'linked',
  define: { 'process.env.NODE_ENV': '"production"' } });
const canvasBuild = await build({ absWorkingDir: root, entryPoints: ['src/canvas-entry.js'], bundle: true,
  outfile: path.join(output, 'canvas.js'), format: 'iife', globalName: 'HtmlEditorCanvas',
  minify: true, target: ['chrome110'], legalComments: 'linked', metafile: true,
  define: { 'process.env.NODE_ENV': '"production"' } });
const timelineBuild = await build({ absWorkingDir: root, entryPoints: ['src/timeline-entry.js'], bundle: true,
  outfile: path.join(output, 'timeline.js'), format: 'iife', globalName: 'HtmlEditorTimeline',
  minify: true, target: ['chrome110'], legalComments: 'linked', metafile: true,
  define: { 'process.env.NODE_ENV': '"production"' } });
const lock = JSON.parse(await readFile(path.join(root, 'package-lock.json')));
const supplements = JSON.parse(await readFile(path.join(root, 'licenses/records.json'))).records;
const canvasPackages = new Set(Object.keys(canvasBuild.metafile.inputs).map(name =>
  name.match(/^node_modules\/((?:@[^/]+\/)?[^/]+)/)?.[1]).filter(Boolean));
const timelinePackages = new Set(Object.keys(timelineBuild.metafile.inputs).map(name =>
  name.match(/^node_modules\/((?:@[^/]+\/)?[^/]+)/)?.[1]).filter(Boolean));
// Published ESM may inline its dependencies, which then disappear from esbuild's
// input graph. Retain their declared locked runtime license closure as well.
for (const packages of [canvasPackages, timelinePackages]) {
  let grew = true;
  while (grew) {
    grew = false;
    for (const [relative, record] of Object.entries(lock.packages)) {
      const name = relative.split('node_modules/').at(-1);
      if (!packages.has(name)) continue;
      for (const dependency of Object.keys(record.dependencies || {})) if (!packages.has(dependency)) {
        packages.add(dependency); grew = true;
      }
    }
  }
}
let notices = '# Editor UI dependency notices\n\nGenerated from locked npm packages, including build dependencies.\n' +
  'Bundled copyright comments are also in editor.js.LEGAL.txt.\n\n';
let canvasNotices = '# Product canvas dependency notices\n\nBundled inputs plus locked declared runtime dependency closure, including dependencies inlined by upstream ESM.\n\n';
let timelineNotices = '# Product timeline dependency notices\n\nBundled inputs plus locked declared runtime dependency closure, including dependencies inlined by upstream ESM. timeline-engine metadata ISC and archived upstream MIT remain distinct evidence.\n\n';
const licenseSources = new Set(['licenses/records.json']);
for (const [relative, record] of Object.entries(lock.packages)) {
  if (!relative) continue;
  const folder = path.join(root, relative);
  if (record.optional && !existsSync(folder)) continue; // Other-platform esbuild binaries.
  const metadata = JSON.parse(await readFile(path.join(folder, 'package.json')));
  let notice = `## ${metadata.name}@${record.version}\n\nLicense: ${metadata.license || record.license || 'unspecified'}\n` +
    `Registry integrity: ${record.integrity}\n\n`;
  const licenseFiles = (await readdir(folder)).filter(name => /^(license|licence|copying|notice)(\.|$)/i.test(name));
  const supplement = supplements.find(r => r.package === metadata.name && r.version === record.version);
  if (!licenseFiles.length && supplement) {
    notice += `Source: ${supplement.source}\nEvidence: ${supplement.evidence_kind}\n`;
    for (const entry of [supplement, supplement.notice].filter(Boolean)) {
      const relativeLicense = `licenses/${entry.file}`;
      const bytes = await readFile(path.join(root, relativeLicense));
      if (hash(bytes) !== entry.sha256) throw Error(`License hash mismatch: ${metadata.name}`);
      notice += bytes.toString('utf8') + '\n\n'; licenseSources.add(relativeLicense);
    }
  } else if (!licenseFiles.length) {
    notice += 'Published package omits full license text; metadata recorded, upstream notice review pending.\n\n';
    if (canvasPackages.has(metadata.name) || timelinePackages.has(metadata.name)) throw Error(`Product license text missing: ${metadata.name}`);
  }
  for (const name of licenseFiles.sort()) notice += `${name}:\n\n${await readFile(path.join(folder, name), 'utf8')}\n\n`;
  notices += notice;
  if (canvasPackages.has(metadata.name)) canvasNotices += notice;
  if (timelinePackages.has(metadata.name)) timelineNotices += notice;
}
await writeFile(path.join(output, 'THIRD_PARTY_NOTICES.txt'), notices);
await writeFile(path.join(output, 'CANVAS_THIRD_PARTY_NOTICES.txt'), canvasNotices);
await writeFile(path.join(output, 'TIMELINE_THIRD_PARTY_NOTICES.txt'), timelineNotices);
const files = {};
for (const file of ['editor.js', 'editor.css', 'editor.js.LEGAL.txt', 'THIRD_PARTY_NOTICES.txt',
  'canvas.js', 'canvas.js.LEGAL.txt', 'CANVAS_THIRD_PARTY_NOTICES.txt',
  'timeline.js', 'timeline.css', 'timeline.js.LEGAL.txt', 'TIMELINE_THIRD_PARTY_NOTICES.txt']) {
  const bytes = await readFile(path.join(output, file));
  files[file] = { bytes: (await stat(path.join(output, file))).size,
    sha256: hash(bytes) };
}
const sources = {};
for (const file of ['package.json', 'package-lock.json', 'build.mjs',
  ...(await readdir(path.join(root, 'src'))).sort().map(name => `src/${name}`), ...[...licenseSources].sort()])
  sources[file] = hash(await readFile(path.join(root, file)));
await writeFile(path.join(output, 'manifest.json'), JSON.stringify({
  format: 'hps.editor_ui.build', version: '0.1.0', sources, files,
}, null, 2) + '\n');
const production = { format: 'hps.editor_canvas.build', version: '0.1.0', files: {}, sources: {} };
for (const file of ['canvas.js', 'canvas.js.LEGAL.txt', 'CANVAS_THIRD_PARTY_NOTICES.txt'])
  production.files[`static/editor_ui/${file}`] = files[file];
const ownSources = Object.keys(canvasBuild.metafile.inputs).filter(name => !name.startsWith('node_modules/'));
for (const file of ['package.json', 'package-lock.json', 'build.mjs', ...ownSources, ...[...licenseSources].sort()])
  production.sources[`editor_ui/${file}`] = hash(await readFile(path.join(root, file)));
for (const file of ['static/html_handoff_workbench.js', 'static/html_editor_canvas.js', 'static/html_scene_editor.js', 'static/html_scene_edit.css', 'static/index.html'])
  production.sources[file] = hash(await readFile(path.join(root, '..', file)));
await writeFile(path.join(output, 'canvas-manifest.json'), JSON.stringify(production, null, 2) + '\n');
const timeline = { format: 'hps.editor_timeline.build', version: '0.1.0', files: {}, sources: {} };
for (const file of ['timeline.js', 'timeline.css', 'timeline.js.LEGAL.txt', 'TIMELINE_THIRD_PARTY_NOTICES.txt'])
  timeline.files[`static/editor_ui/${file}`] = files[file];
const timelineSources = Object.keys(timelineBuild.metafile.inputs).filter(name => !name.startsWith('node_modules/'));
for (const file of ['package.json', 'package-lock.json', 'build.mjs', ...timelineSources, ...[...licenseSources].sort()])
  timeline.sources[`editor_ui/${file}`] = hash(await readFile(path.join(root, file)));
for (const file of ['static/html_editor_timeline_bridge.js', 'static/html_scene_editor.js', 'static/html_scene_edit.css', 'static/index.html'])
  timeline.sources[file] = hash(await readFile(path.join(root, '..', file)));
await writeFile(path.join(output, 'timeline-manifest.json'), JSON.stringify(timeline, null, 2) + '\n');
console.log(JSON.stringify(files));
