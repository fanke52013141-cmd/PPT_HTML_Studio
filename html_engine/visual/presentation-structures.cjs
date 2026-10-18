"use strict";

// Registered structures only; content, anchor geometry and time stay with the
// shared renderer. No course-specific values or free author CSS enter here.
function frameFigure(el, theme) {
  Object.assign(el.style, {border:`1px solid ${theme.colors.line}`,
    borderRadius:`${theme.shapes.cardRadius}px`, background:theme.colors.background});
  el.querySelector(".v-figure-halo").style.display = "none";
}

function dividedSummary(el, parts, slot, theme, variant, textNodes) {
  const {flow, from, to, arrow, term, takeaway} = parts;
  const width = slot.box.width - 2 * variant.paddingX - 2;
  const height = slot.box.height - 2 * variant.paddingY - 2;
  const columns = variant.columns.map(f => (width - variant.gap * 2) * f);
  Object.assign(el.style, {display:"grid", gridTemplateColumns:columns.map(v=>`${v}px`).join(" "),
    alignItems:"center", gap:`${variant.gap}px`, padding:`${variant.paddingY}px ${variant.paddingX}px`,
    border:`1px solid ${theme.colors.line}`, borderRadius:`${theme.shapes.cardRadius}px`,
    background:theme.colors.background});
  flow.removeChild(term);
  el.insertBefore(term, takeaway);
  Object.assign(flow.style, {display:"grid", gridTemplateColumns:"minmax(0,1fr) 48px minmax(0,1fr)",
    gap:"14px", width:"100%", minWidth:"0", alignItems:"center"});
  for (const state of [from,to]) Object.assign(state.style, {padding:"8px 12px", minWidth:"0",
    maxWidth:"100%", boxSizing:"border-box", textAlign:"center", fontSize:"26px",
    background:theme.colors.panel, border:`1px solid ${theme.colors.line}`});
  Object.assign(arrow.style, {width:"48px", height:"28px"});
  Object.assign(term.style, {display:"flex", alignItems:"center", justifyContent:"center",
    height:"100%", minWidth:"0", boxSizing:"border-box", textAlign:"center", fontSize:"28px",
    borderLeft:`1px solid ${theme.colors.line}`, borderRight:`1px solid ${theme.colors.line}`});
  Object.assign(takeaway.style, {marginLeft:"0", minWidth:"0", maxWidth:"100%",
    whiteSpace:"normal", textAlign:"center", fontSize:"24px", lineHeight:"1.3"});
  const stateWidth = (columns[0] - 76) / 2;
  for (const [part, child, partWidth, lines] of [["from",from,stateWidth,1],["to",to,stateWidth,1],
    ["term",term,columns[1],2],["takeaway",takeaway,columns[2],2]]) {
    textNodes.push([child,{...slot,maxLines:lines,box:{...slot.box,width:partWidth,height}},`${el.dataset.objectId}:${part}`]);
  }
  textNodes.push([el,{...slot,maxLines:4},`${el.dataset.objectId}:container`]);
}

function dashedAnnotation(ring, leader, svg, theme) {
  ring.setAttribute("stroke-dasharray", "6 5");
  leader.removeAttribute("pathLength");
  leader.style.strokeDasharray = "6 5";
  const head = document.createElementNS("http://www.w3.org/2000/svg", "path");
  for (const [key,value] of Object.entries({fill:"none",stroke:theme.colors.accent,
    "stroke-width":theme.shapes.strokeWidth,"stroke-linecap":"round","stroke-linejoin":"round"})) head.setAttribute(key,value);
  svg.append(head);
}

function drawDashedLeader(svg, start, end, progress) {
  const [,leader,head] = svg.children;
  const dx=end.x-start.x, dy=end.y-start.y, length=Math.hypot(dx,dy);
  const tip={x:start.x+dx*progress,y:start.y+dy*progress};
  leader.setAttribute("d",`M ${start.x} ${start.y} L ${tip.x} ${tip.y}`);
  leader.removeAttribute("stroke-dashoffset");
  if (length < 1 || progress < .95) {head.setAttribute("d","");return;}
  const ux=dx/length,uy=dy/length;
  head.setAttribute("d",`M ${tip.x-ux*9-uy*4} ${tip.y-uy*9+ux*4} L ${tip.x} ${tip.y} L ${tip.x-ux*9+uy*4} ${tip.y-uy*9-ux*4}`);
}

module.exports = {frameFigure, dividedSummary, dashedAnnotation, drawDashedLeader};
