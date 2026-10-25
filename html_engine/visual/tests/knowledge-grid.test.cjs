"use strict";
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {compile, validate} = require('../compiler.cjs');
const root = path.resolve(__dirname, '..');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'generated/catalog.json'), 'utf8'));
const fixture = JSON.parse(fs.readFileSync(path.join(root, '../../checks/fixtures/knowledge-grid-plan.json'), 'utf8'));
const nodes = Object.entries(fixture.plan.slots).map(([slot, {kind, ...content}]) => ({id:slot, slot, type:kind, ...content}));
const scene = {format:'hps.visual.scene', version:'0.5.0', id:'knowledge-grid', name:'Grid contract',
  themeRef:{id:'neutral-baseline', version:'0.2.0'}, layoutRef:{id:'knowledge-grid-v1', version:'0.2.0'},
  templateRef:{id:'knowledge-grid-v1', version:'0.1.0'}, durationMs:2000, nodes, beats:[], source:'Controlled contract fixture',
  motion:nodes.map(node => ({targetId:node.id, type:'enter', startMs:0, durationMs:500, offsetX:0, offsetY:0}))};
compile(scene, catalog);
const missing = structuredClone(scene);
missing.nodes = missing.nodes.filter(node => node.id !== 'card-4');
missing.motion = missing.motion.filter(action => action.targetId !== 'card-4');
assert.throws(() => compile(missing, catalog), /TEMPLATE_SLOT_REQUIRED/);
const theme = structuredClone(catalog.themes.find(t => t.id === 'neutral-baseline'));
while (theme.compatibleLayouts.length < 32) theme.compatibleLayouts.push('registered-' + theme.compatibleLayouts.length);
validate('theme', theme);
theme.compatibleLayouts.push('over-budget');
assert.throws(() => validate('theme', theme), /INVALID_VISUAL_DEFINITION/);
theme.compatibleLayouts.pop();
theme.compatibleLayouts[31] = theme.compatibleLayouts[0];
assert.throws(() => validate('theme', theme), /INVALID_VISUAL_DEFINITION/);
const wrong = structuredClone(scene);
wrong.layoutRef.id = 'unregistered-layout';
assert.throws(() => compile(wrong, catalog), /UNRESOLVED_REFERENCE/);
console.log('knowledge grid: registered compilation, required slots, bounded unique theme compatibility and exact layout resolution passed');
