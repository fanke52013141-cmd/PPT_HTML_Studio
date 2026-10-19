"use strict";
// Production owner of registered relationship sizing. No DOM or instance content.
const ids = new Set(["summary-relationship-panel", "summary-relationship-compact", "summary-relationship-columns"]);
function relationshipCapacity(variant, box) {
  if (!variant || !ids.has(variant.id)) return null;
  const compact = variant.id !== "summary-relationship-panel";
  const columnsResult = variant.termPosition === "takeaway_column";
  const width = box.width - variant.paddingX * 2;
  const height = box.height - variant.paddingY * 2;
  const sum = variant.columns.reduce((a,b)=>a+b,0);
  const columns = variant.columns.map(f=>(width-variant.gap*2)*f/sum);
  const padding = compact ? 6 : 12;
  const parts = {};
  for (const part of ["heading","from","to","term","takeaway"]) {
    const available = part === "heading" ? columns[0]-(compact?12+42+10:18+58+14)
      : part === "takeaway" ? columns[2]-(columnsResult?22:0)
      : part === "term" ? (columnsResult?columns[2]:columns[1]-(compact?12:18))
      : (columns[1]-(compact?12:18)-16)/3.3-(compact?12:24);
    const partHeight = part === "from" || part === "to" ? height-(compact?12+20:32+24)
      : part === "term" ? (columnsResult?30:compact?24:32)
      : columnsResult && part === "takeaway" ? height-48 : height;
    parts[part] = {width:available,height:partHeight,maxLines:variant.textBudgets[part]};
  }
  return {width,height,columns,compact,columnsResult,parts,
    stateBox:{paddingY:padding,paddingX:padding,borderY:1},
    dependsOn:["presentation.height","presentation.width","presentation.variant","typography","font_bytes"]};
}
function constraints(scene, layout, variants) {
  return scene.nodes.filter(n=>n.type==="summary").flatMap(node=>{
    const v=variants.find(v=>v.id===node.presentation?.variant);
    const metrics=relationshipCapacity(v,layout.slots[node.slot].box);
    if(!metrics) return [];
    return [{targetId:node.id,variant:v.id,units:"logical_canvas_px",source:"production/relationship-capacity",
      parts:Object.fromEntries(Object.entries(metrics.parts).map(([part,limits])=>[part,{
        effective_limits:limits,tolerance:{width:1,height:1},
        ...(part==="from"||part==="to"?{box_model:metrics.stateBox}:{}),
        measured:null,measurement_status:"requires_original_dom"}])),depends_on:metrics.dependsOn}];
  });
}
function declaredLineChecks(scene, layout, variants) {
  return constraints(scene,layout,variants).flatMap(item=>{
    const node=scene.nodes.find(n=>n.id===item.targetId);
    return ["from","to"].flatMap(part=>{
      const style=node.presentation?.typography?.[part], fact=item.parts[part];
      if(!Number.isFinite(style?.fontSizePx)||!Number.isFinite(style?.lineHeight)) return [];
      const minimum=style.fontSizePx*style.lineHeight+2*fact.box_model.paddingY+2*fact.box_model.borderY;
      return [{criterion_id:"declared_line_box",targetId:node.id,part,
        status:minimum>fact.effective_limits.height+fact.tolerance.height?"failed":"preflight_passed",
        code:"DECLARED_LINE_BOX",minimum_outer_height:minimum,limit:fact.effective_limits.height,tolerance:1,
        verification_boundary:"Necessary declared CSS line-box condition only; not DOM/visual approval"}];
    });
  });
}
module.exports={relationshipCapacity,constraints,declaredLineChecks};
