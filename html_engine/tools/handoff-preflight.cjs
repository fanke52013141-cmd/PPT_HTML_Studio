"use strict";
// Bundled from production dependencies; no DOM renderer, network, or author writes.
const fs = require('node:fs');
const Ajv = require('ajv');
const {compile} = require('../visual/compiler.cjs');
const capacity = require('../visual/relationship-capacity.cjs');
const variants = require('../visual/presentation-variants.json').variants;
const baseCatalog = require('../visual/generated/catalog.json');
const {overlapPolicy} = require('./temporal-review.cjs');

function check(input) {
  const {task, result, scene} = input, ajv = new Ajv({strict:false,allErrors:true});
  const errors=[];
  for (const [name,schema,values] of [
    ['result_schema',task.result_schema,[result]], ['operation_schema',task.operation_schema,result.operations || []]
  ]) {
    const validate=ajv.compile(schema);
    for (const value of values) if(!validate(value)) errors.push({criterion_id:name,status:'failed',details:validate.errors});
  }
  if(errors.length) return {checks:errors,preflight_passed:false};
  const catalog=structuredClone(baseCatalog);
  catalog.assets=(task.context.assets || []).map(item=>item.asset);
  try {
    const compiled=compile(scene,catalog);
    const checks=[{criterion_id:'production_compile',status:'preflight_passed'},...capacity.declaredLineChecks(scene,compiled.layout,variants)];
    return {checks,preflight_passed:!checks.some(c=>c.status==='failed'),
      boxes:Object.fromEntries(scene.nodes.map(node=>[node.id,compiled.layout.slots[node.slot].box]))};
  } catch(error) {
    return {preflight_passed:false,checks:[{criterion_id:'production_compile',status:'failed',
      code:error.code,message:error.message,diagnostics:error.diagnostics}]};
  }
}
function facts(input) {
  const catalog=structuredClone(baseCatalog);
  catalog.assets=[...new Map([...catalog.assets,...input.assets].map(asset=>[asset.id+'@'+asset.version,asset])).values()];
  const result=compile(input.scene,catalog);
  return {layout:result.layout,capacity:capacity.constraints(input.scene,result.layout,variants),overlap:overlapPolicy(input.scene,input.spec,
    require('../visual/qa/overlap-policy.json'))};
}
if(require.main===module) {
  const input=JSON.parse(fs.readFileSync(0,'utf8'));
  process.stdout.write(JSON.stringify(input.mode==='facts'?facts(input):check(input)));
}
module.exports={check,facts};
