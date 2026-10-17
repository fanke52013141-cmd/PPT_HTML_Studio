// Owns the editor-only canvas lifecycle; author drafts and history stay in HtmlSceneEditor.
(function () {
  'use strict';
  if (window.HtmlEditorCanvasBridge) return;
  function create({ frame, getDocument, getSelection, onSelect, onCommit, onError }) {
    let canvas = null, enabled = false, disposed = false, snap = true;
    function suspend() { canvas?.destroy(); canvas = null; }
    function refresh() {
      suspend();
      if (!enabled || disposed) return;
      const win = frame.contentWindow, player = win.visualPlayer, doc = getDocument();
      if (!win.HtmlEditorCanvas || !player?.layout) throw Error('布局组件未加载，请重新打开编辑器');
      const report = player.layout();
      const layout = win.VisualData.catalog.layouts.find(l => l.id === doc.scene.layoutRef.id && l.version === doc.scene.layoutRef.version);
      if (!layout) throw Error('布局定义不存在');
      canvas = win.HtmlEditorCanvas.mountCanvas({ stage: frame.contentDocument.querySelector('.visual-stage'),
        nodes: doc.scene.nodes, authorSize: layout.canvas, geometry: report.geometry, slots: layout.slots, snap,
        onSelect, onCommit, onError });
      canvas.select(getSelection());
    }
    return { refresh, suspend,
      setEnabled(value) {
        enabled = value;
        if (enabled) refresh();
        else { suspend(); const p = frame.contentWindow?.visualPlayer; if (p?.ready) p.seek(p.timeMs); }
      },
      select(ids) { canvas?.select(ids); },
      setSnap(value) { snap = value; canvas?.setSnap(value); },
      destroy() { disposed = true; enabled = false; suspend(); const p = frame.contentWindow?.visualPlayer; if (p?.ready) { p.pause(); p.seek(p.timeMs); } },
    };
  }
  window.HtmlEditorCanvasBridge = { create };
})();
