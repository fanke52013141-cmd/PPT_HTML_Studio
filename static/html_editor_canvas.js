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
  function createWorkView({host,before,onSelect,onCommit}) {
    const frame=document.createElement('iframe');frame.title='人工候选工作画布';frame.className='hse-preview';host.insertBefore(frame,before);
    let disposed=false,serial=0,canvas=null;
    const ready=new Promise(resolve=>{frame.onload=resolve;});
    frame.srcdoc=`<!doctype html><meta charset="utf-8"><style>body{margin:0}#viewport{width:100%}.runtime-controls{display:none}</style><div id="viewport"></div><div class="runtime-controls"><select id="scene"></select><select id="theme"></select><textarea id="definition"></textarea><button id="apply"></button><button id="play"></button><button id="end"></button><input id="seek"><span id="time"></span><input id="font" value="32"><span id="font-value"></span><input type="checkbox" id="reduced"><p id="status"></p></div><script src="/api/html-scene-editor/runtime/data.js"></script><script src="/api/html-scene-editor/runtime/player.js"></script><script src="/static/editor_ui/canvas.js"></script>`;
    return {
      async render(state,view,selection){
        const token=++serial;await ready;if(disposed||token!==serial)return '';
        canvas?.destroy();canvas=null;
        const resolved=state.views?.[view],player=frame.contentWindow.visualPlayer;
        if(!resolved?.scene){frame.hidden=true;return resolved?.unavailable||'当前画面不可用；可使用参数继续修复。';}
        frame.hidden=false;
        const ok=await player.diagnose(resolved.scene,resolved.resources);
        if(disposed||token!==serial)return '';
        if(!ok){frame.hidden=true;return '当前画面无法渲染；请使用参数修复并重新检查。';}
        player.seek(resolved.scene.durationMs);
        if(view!=='work'||!state.editable)return '只读对照，不会改变工作草稿。';
        canvas=create({frame,getDocument:()=>({scene:{...state.scene,nodes:state.scene.nodes.filter(n=>state.scope.includes(n.id))}}),getSelection:()=>selection,onSelect,onCommit,
          onError:error=>{const status=host.querySelector('[data-canvas-error]');if(status)status.textContent=error.message||String(error);}});
        canvas.setEnabled(true);
        return '工作草稿 · 诊断显示，不代表检查通过；选中对象拖动/缩放，修改自动存入草稿。';
      },
      select(ids){canvas?.select(ids);},
      destroy(){disposed=true;serial++;canvas?.destroy();frame.remove();}
    };
  }
  window.HtmlEditorCanvasBridge = { create, createWorkView };
})();
