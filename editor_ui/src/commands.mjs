// Pure author-data adapters. Validation/save remain owned by the application.
function finite(value) {
  if (!Number.isFinite(value)) throw Error('坐标或时间必须为有限数值');
  return value;
}
export function authorDelta(dx, dy, stageRect, authorSize) {
  [stageRect.width, stageRect.height, authorSize.width, authorSize.height].forEach(finite);
  if (!(stageRect.width > 0 && stageRect.height > 0 && authorSize.width > 0 && authorSize.height > 0))
    throw Error('画布尺寸无效');
  return { x: finite(dx) * authorSize.width / stageRect.width,
    y: finite(dy) * authorSize.height / stageRect.height };
}
export function presentationOperation(node, delta, size) {
  if (!node || node.type === 'annotation') throw Error('该对象不能调整布局');
  const values = { offsetX: finite((node.presentation?.offsetX ?? 0) + finite(delta.x)),
    offsetY: finite((node.presentation?.offsetY ?? 0) + finite(delta.y)) };
  if (size) Object.assign(values, { width: finite(size.width), height: finite(size.height) });
  if (Math.abs(values.offsetX) > 400 || Math.abs(values.offsetY) > 400 ||
      (size && (size.width < 20 || size.width > 1600 || size.height < 20 || size.height > 800)))
    throw Error('超出公开布局范围；修改未应用');
  return { kind: 'set_presentation', targetId: node.id, values };
}
export function bindingEdit({ action, binding, window, startMs, endMs, effectiveStartMs }) {
  if (!binding?.beatId || !window || binding.beatId !== window.beatId)
    throw Error('需要原动作的有效语块绑定');
  finite(startMs); finite(endMs); finite(effectiveStartMs);
  finite(window.startMs); finite(window.endMs);
  if (startMs < window.startMs || endMs > window.endMs || endMs <= startMs)
    throw Error('动作不能越过当前语块；请使用原编辑器显式重绑');
  const durationMs = endMs - startMs;
  if (durationMs < 100 || durationMs > 10000) throw Error('动作时长超出公开范围');
  // Move relative to the effective start, preserving edge, IDs, hashes and metadata.
  return { action: { ...action, durationMs },
    binding: { ...binding, offsetMs: finite(binding.offsetMs ?? 0) + startMs - effectiveStartMs } };
}

export function applyPresentationOperations(scene, operations) {
  if (!Array.isArray(operations) || !operations.length || operations.length > 20)
    throw Error('一次布局事务需要1—20个对象');
  const result = structuredClone(scene), seen = new Set();
  for (const operation of operations) {
    const node = result.nodes.find(n => n.id === operation.targetId);
    if (operation.kind !== 'set_presentation' || !node || seen.has(node.id))
      throw Error('布局操作或对象身份无效');
    seen.add(node.id);
    const values = operation.values;
    if (!values || !Object.keys(values).length || Object.keys(values).some(k => !['offsetX', 'offsetY', 'width', 'height'].includes(k)))
      throw Error('只能修改公开布局字段');
    const combined = { ...node.presentation, ...values };
    presentationOperation({ ...node, presentation: combined }, { x: 0, y: 0 });
    for (const key of ['width', 'height']) if (combined[key] !== undefined &&
      (!Number.isFinite(combined[key]) || combined[key] < 20 || combined[key] > (key === 'width' ? 1600 : 800)))
      throw Error('尺寸超出公开范围');
    const changed = Object.fromEntries(Object.entries(values).filter(([key, value]) =>
      value !== (node.presentation?.[key] ?? (key.startsWith('offset') ? 0 : undefined))));
    if (Object.keys(changed).length) node.presentation = { ...node.presentation, ...changed };
  }
  if (JSON.stringify(result) === JSON.stringify(scene)) return result;
  if (!['0.5.0', '0.6.0', '0.7.0'].includes(result.version)) result.version = '0.5.0';
  return result;
}

export function timelineEdit(scene, binding, timing, id, startMs, endMs, resize = false) {
  const current = timing?.actions.find(a => a.id === id);
  const action = scene.motion.find(a => (a.actionId || `${a.targetId}:${a.type}`) === id);
  const link = binding?.actions[id];
  const window = timing?.beats.find(b => b.beatId === link?.beatId);
  if (!current?.editable || !action) throw Error('需要有效音频和原动作语块绑定');
  startMs = Math.round(finite(startMs)); endMs = Math.round(finite(endMs));
  for (const sibling of timing.actions.filter(a => a.targetId === current.targetId && a.id !== id)) {
    if ((sibling.effectiveStartMs < current.effectiveStartMs && startMs <= sibling.effectiveStartMs) ||
        (sibling.effectiveStartMs > current.effectiveStartMs && startMs >= sibling.effectiveStartMs))
      throw Error('不能改变同一对象的动作顺序');
  }
  const edit = bindingEdit({ action, binding: link, window, startMs, endMs, effectiveStartMs: current.effectiveStartMs });
  // Moving a clipped bar preserves its authored duration. Only resizing changes it.
  if (!resize) edit.action.durationMs = action.durationMs;
  const next = structuredClone(scene), links = structuredClone(binding);
  next.motion[next.motion.findIndex(a => (a.actionId || `${a.targetId}:${a.type}`) === id)] = edit.action;
  links.actions[id] = edit.binding;
  return { scene: next, binding: links };
}
