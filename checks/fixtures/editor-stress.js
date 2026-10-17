// Only served by the isolated fixture; not application code or a production template.
const stage = document.getElementById('stage'), output = document.getElementById('result');
const nodes = Array.from({ length: 40 }, (_, i) => ({ id: `item-${i}`, type: 'text' }));
let canvas, commits = [], samples = [];
function mount() {
  canvas?.destroy(); stage.replaceChildren(); commits = []; samples = [];
  const scale = Number(document.getElementById('scale').value);
  stage.style.transform = `scale(${scale})`;
  for (const [i, node] of nodes.entries()) {
    delete node.presentation;
    const element = document.createElement('div'); element.dataset.objectId = node.id;
    element.textContent = node.id;
    Object.assign(element.style, { position: 'absolute', left: `${40 + i % 8 * 185}px`, top: `${40 + Math.floor(i / 8) * 145}px`,
      width: '130px', height: '70px', background: '#ffe5da', border: '1px solid #ef6330' });
    stage.append(element);
  }
  canvas = HtmlEditorCanvas.mountCanvas({ stage, nodes, authorSize: { width:1600, height:900 }, snap:false,
    onSelect() {}, onError(error) { document.getElementById('status').textContent = error.message; },
    onCommit: async operations => {
      commits.push(operations);
      for (const operation of operations) {
        const node = nodes.find(n => n.id === operation.targetId);
        node.presentation = operation.values;
      }
      output.textContent = JSON.stringify({ commits, samples, scale, dpr:devicePixelRatio });
      document.getElementById('status').textContent = `完成${commits.length}`;
      return true;
    } });
  document.getElementById('status').textContent = '就绪40';
}
// Input-to-next-frame latency, separate from server candidate validation latency.
document.addEventListener('pointerdown', event => {
  if (!event.target.closest('.hps-editor-target,.moveable-area')) return;
  const start = performance.now();
  requestAnimationFrame(() => samples.push(performance.now() - start));
}, true);
document.getElementById('scale').onchange = mount; document.getElementById('reset').onclick = mount;
mount();
