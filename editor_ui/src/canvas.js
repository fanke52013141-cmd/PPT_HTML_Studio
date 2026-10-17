import Moveable from 'moveable';
import Selecto from 'selecto';
import { authorDelta, presentationOperation } from './commands.mjs';

// The adapter lives in the player's iframe. Only helper boxes move during a gesture.
export function mountCanvas({ stage, nodes, authorSize, geometry = {}, slots = {}, snap = true, onSelect, onCommit, onError }) {
  if (stage.ownerDocument !== document) throw Error('画布适配器必须在播放器 iframe 内创建');
  const layer = document.createElement('div');
  layer.className = 'hps-editor-layer';
  Object.assign(layer.style, { position: 'absolute', inset: '0', pointerEvents: 'none', zIndex: '1000' });
  const style = document.createElement('style');
  style.textContent = '.hps-editor-layer .moveable-control,.hps-editor-layer .moveable-area:not(.moveable-avoid):not(.moveable-pass){pointer-events:auto}.hps-editor-target[data-hidden=true]{border:1px dashed #ee5d36;background:#ee5d3610}';
  layer.append(style); document.body.append(layer);
  const proxies = new Map(), writes = new Map();
  let disposed = false, gesture = null, selected = [], pending = false, raf = 0;
  const moveable = new Moveable(layer, { container: layer, draggable: true, resizable: true,
    renderDirections: ['e', 's', 'se'], origin: false, rotatable: false, scalable: false,
    warpable: false, useResizeObserver: true, snappable: snap, snapThreshold: 4, snapGap: false,
    snapDirections: { left: true, right: true, top: true, bottom: true, center: true, middle: true },
    elementSnapDirections: { left: true, right: true, top: true, bottom: true, center: true, middle: true } });
  const selecto = new Selecto({ container: layer, dragContainer: document.body,
    selectableTargets: ['.hps-editor-target'], selectByClick: true, selectFromInside: false,
    hitRate: 0, toggleContinueSelect: 'shift' });
  function select(elements, emit = true) {
    if (elements.length > 20) { selecto.setSelectedTargets(selected); onError(Error('群组编辑最多20个对象')); return; }
    const changed = elements.length !== selected.length || elements.some((e, i) => e !== selected[i]);
    selected = elements;
    moveable.target = elements.length === 1 ? elements[0] : elements;
    moveable.resizable = elements.length === 1;
    moveable.keepRatio = elements.length === 1 && nodes.find(n => n.id === elements[0].dataset.editorObject)?.type === 'image';
    moveable.elementGuidelines = [...proxies.values()].filter(e => !elements.includes(e));
    for (const proxy of proxies.values()) proxy.style.outline = elements.includes(proxy) ? '2px solid #ee5d36' : '';
    selecto.setSelectedTargets(elements);
    if (emit && changed) onSelect(elements.map(e => e.dataset.editorObject));
  }
  selecto.on('dragStart', e => {
    if (pending || moveable.isMoveableElement(e.inputEvent.target) ||
      (!e.inputEvent.shiftKey && selected.includes(e.inputEvent.target))) e.stop();
  });
  selecto.on('selectEnd', e => {
    select(e.selected);
    if (e.isDragStart && !pending) {
      e.inputEvent.preventDefault();
      moveable.waitToChangeTarget().then(() => { if (!disposed) moveable.dragStart(e.inputEvent); });
    }
  });
  function refresh() {
    if (disposed || gesture || pending) return;
    const live = new Set(), targets = [...stage.querySelectorAll('[data-object-id]')];
    for (const node of nodes) {
      if (node.type === 'annotation') continue;
      const target = targets.find(e => e.dataset.objectId === node.id);
      if (!target || Number(getComputedStyle(target).opacity) === 0) continue;
      const rect = target.getBoundingClientRect();
      let proxy = proxies.get(node.id);
      if (!proxy) {
        proxy = document.createElement('div'); proxy.className = 'hps-editor-target';
        proxy.dataset.editorObject = node.id; proxy.setAttribute('aria-label', `布局对象 ${node.id}`);
        layer.append(proxy); proxies.set(node.id, proxy);
      }
      live.add(node.id); proxy.dataset.hidden = String(target.dataset.editorHidden === 'true');
      Object.assign(proxy.style, { position: 'absolute', pointerEvents: 'auto',
        left: `${rect.left + window.scrollX}px`, top: `${rect.top + window.scrollY}px`,
        width: `${rect.width}px`, height: `${rect.height}px`, boxSizing: 'border-box', cursor: 'move' });
    }
    for (const [id, proxy] of proxies) if (!live.has(id)) { proxy.remove(); proxies.delete(id); }
    const box = stage.getBoundingClientRect(), x = box.left + window.scrollX, y = box.top + window.scrollY;
    const sx = box.width / authorSize.width, sy = box.height / authorSize.height;
    moveable.verticalGuidelines = [...new Set([0, authorSize.width, ...Object.values(slots).flatMap(s => [s.box.x, s.box.x + s.box.width])])].map(n => x + n * sx);
    moveable.horizontalGuidelines = [...new Set([0, authorSize.contentBottom ?? authorSize.height, ...Object.values(slots).flatMap(s => [s.box.y, s.box.y + s.box.height])])].map(n => y + n * sy);
    select(selected.map(e => proxies.get(e.dataset.editorObject)).filter(Boolean), false);
    moveable.updateRect();
  }
  function queue(target, values) {
    writes.set(target, values);
    if (!raf) raf = requestAnimationFrame(() => {
      raf = 0;
      for (const [element, styles] of writes) Object.assign(element.style, styles);
      writes.clear();
    });
  }
  function start(events, e) {
    if (pending || disposed) { e.stop(); return; }
    const rect = stage.getBoundingClientRect();
    gesture = { rect, clientX: e.clientX, clientY: e.clientY, moved: false,
      entries: new Map(events.map(event => [event.target, {
      node: nodes.find(n => n.id === event.target.dataset.editorObject),
      left: parseFloat(event.target.style.left), top: parseFloat(event.target.style.top),
      startSize: geometry[event.target.dataset.editorObject]?.box || {
        width: parseFloat(event.target.style.width) * authorSize.width / rect.width,
        height: parseFloat(event.target.style.height) * authorSize.height / rect.height },
      delta: { x: 0, y: 0 }, size: null,
    }])) };
  }
  function moved(e) {
    if (!gesture) return false;
    if (Math.hypot(e.clientX - gesture.clientX, e.clientY - gesture.clientY) > 0.25) gesture.moved = true;
    return gesture.moved;
  }
  function drag(e) {
    const entry = gesture?.entries.get(e.target);
    if (!entry || !moved(e)) return;
    entry.delta = authorDelta(e.beforeDist[0], e.beforeDist[1], gesture.rect, authorSize);
    queue(e.target, { left: `${entry.left + e.beforeDist[0]}px`, top: `${entry.top + e.beforeDist[1]}px` });
  }
  async function finish() {
    const completed = gesture; gesture = null;
    if (!completed) return;
    cancelAnimationFrame(raf); raf = 0; writes.clear(); pending = true;
    try {
      const operations = completed.moved ? [...completed.entries.values()].filter(e => e.delta.x || e.delta.y || e.size)
        .map(e => presentationOperation(e.node, e.delta, e.size)) : [];
      if (operations.length) await onCommit(operations);
    } catch (error) { onError(error); } // The owning editor rejects callbacks after close.
    finally { pending = false; refresh(); }
  }
  moveable.on('dragStart', e => start([e], e)).on('drag', drag).on('dragEnd', finish);
  moveable.on('dragGroupStart', e => start(e.events, e)).on('dragGroup', e => e.events.forEach(drag)).on('dragGroupEnd', finish);
  moveable.on('resizeStart', e => start([e], e)).on('resize', e => {
    const entry = gesture?.entries.get(e.target);
    if (!entry || !moved(e)) return;
    const delta = authorDelta(e.dist[0], e.dist[1], gesture.rect, authorSize);
    const size = { width: entry.startSize.width + delta.x, height: entry.startSize.height + delta.y };
    entry.size = Math.abs(delta.x) + Math.abs(delta.y) > 0.000001 ? size : null;
    queue(e.target, { width: `${e.width}px`, height: `${e.height}px` });
  }).on('resizeEnd', finish);
  const observer = new ResizeObserver(refresh); observer.observe(stage);
  window.addEventListener('scroll', refresh); refresh();
  return { refresh,
    select: ids => select(ids.map(id => proxies.get(id)).filter(Boolean), false),
    setSnap(value) { moveable.snappable = value; },
    destroy() {
      if (disposed) return;
      disposed = true; gesture = null; cancelAnimationFrame(raf); writes.clear();
      observer.disconnect(); window.removeEventListener('scroll', refresh);
      selecto.destroy(); moveable.destroy(); layer.remove();
    } };
}
