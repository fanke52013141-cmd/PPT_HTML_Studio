import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const json = url => JSON.parse(readFileSync(url));
const root = new URL('../', import.meta.url), output = new URL('../../static/editor_ui/', import.meta.url);
const manifest = json(new URL('manifest.json', output));
test('generated output matches every source and output fingerprint', () => {
  for (const [file, expected] of Object.entries(manifest.sources))
    assert.equal(createHash('sha256').update(readFileSync(new URL(file, root))).digest('hex'), expected, file);
  for (const [file, record] of Object.entries(manifest.files)) {
    const bytes = readFileSync(new URL(file, output));
    assert.equal(bytes.length, record.bytes);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), record.sha256, file);
  }
});
test('direct candidate versions and registry integrity match the archived research', () => {
  const lock = json(new URL('package-lock.json', root));
  const research = json(new URL('../docs/research/2026-10-17-open-source-scene-editor/sources.json', root));
  for (const record of research.sources.filter(source => source.dist_integrity)) {
    const installed = lock.packages[`node_modules/${record.id}`];
    assert.equal(installed.version, record.version);
    assert.equal(installed.integrity, record.dist_integrity);
    assert.equal(lock.packages[''].dependencies[record.id], record.version);
  }
});
test('product source closure fingerprints consumers and excludes timeline/React code', () => {
  const production = json(new URL('canvas-manifest.json', output));
  const repo = new URL('../', root);
  for (const [file, expected] of Object.entries(production.sources))
    assert.equal(createHash('sha256').update(readFileSync(new URL(file, repo))).digest('hex'), expected, file);
  for (const [file, expected] of Object.entries(production.files))
    assert.equal(createHash('sha256').update(readFileSync(new URL(file, repo))).digest('hex'), expected.sha256, file);
  const code = readFileSync(new URL('canvas.js', output), 'utf8');
  assert(!code.includes('timeline-editor')); assert(!code.includes('react.production.min.js'));
  assert(Object.keys(production.sources).includes('static/html_scene_editor.js'));
  const notices = readFileSync(new URL('CANVAS_THIRD_PARTY_NOTICES.txt', output), 'utf8');
  assert(!notices.includes('review pending')); assert(!notices.includes('@xzdarcy'));
});
test('timeline product has an independent source/license closure and never starts its engine', () => {
  const production = json(new URL('timeline-manifest.json', output)), repo = new URL('../', root);
  for (const [file, expected] of Object.entries(production.sources))
    assert.equal(createHash('sha256').update(readFileSync(new URL(file, repo))).digest('hex'), expected, file);
  for (const [file, expected] of Object.entries(production.files))
    assert.equal(createHash('sha256').update(readFileSync(new URL(file, repo))).digest('hex'), expected.sha256, file);
  const notices = readFileSync(new URL('TIMELINE_THIRD_PARTY_NOTICES.txt', output), 'utf8');
  assert(notices.includes('@xzdarcy/timeline-engine')); assert(!notices.includes('review pending'));
  const source = readFileSync(new URL('src/timeline.jsx', root), 'utf8');
  assert(!/\.play\(/.test(source)); assert(source.includes('effects={{}}'));
});
