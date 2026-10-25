// Explicit same-project asset selection. Production owns identity checks and writes.
(function(){
  'use strict';
  if(window.HtmlAssetReuse)return;
  const states=new WeakMap();
  const el=(tag,text='')=>Object.assign(document.createElement(tag),{textContent:text});
  function mount(section,context){
    const key=context.project.id+':'+context.slideId;
    let s=states.get(section);if(s?.key===key)return;
    s?.box.remove();
    const box=el('details'),summary=el('summary','复用当前项目已有素材（可选）');box.dataset.designOnly='';
    const load=el('button','读取可复用素材');load.type='button';
    const select=el('select'),none=el('option','不复用，按计划生成');none.value='';select.append(none);select.setAttribute('aria-label','已有素材');
    const slot=el('input');slot.value='subject';slot.setAttribute('aria-label','目标图片槽位');
    const message=el('p','选择素材并明确图片槽位后生成新设计。不会继承原页视觉批准；已确认设计的素材不能静默替换。');
    box.append(summary,load,select,slot,message);section.querySelector('.html-workspace-toolbar').after(box);
    s={key,box,select,slot,rows:[]};states.set(section,s);
    load.onclick=async()=>{load.disabled=true;
      try{const result=await API.get(`/api/projects/${encodeURIComponent(context.project.id)}/html-review/${encodeURIComponent(context.slideId)}/reusable-assets`);
        if(states.get(section)!==s)return;s.rows=result.assets;select.replaceChildren(none);
        for(const [i,a]of s.rows.entries()){const option=el('option',`${a.description} · 来源 ${a.source_pages.join('、')} · ${a.size.width}×${a.size.height}`);option.value=String(i);select.append(option);}
        message.textContent=`可复用 ${s.rows.length} 个已核验素材。请选择并确认目标图片槽位。`;
      }catch(error){if(states.get(section)===s)message.textContent=error.message;}finally{load.disabled=false;}
    };
  }
  function selection(section){const s=states.get(section);if(!s||s.select.value==='')return [];
    const a=s.rows[Number(s.select.value)];return a?[{slot:s.slot.value.trim(),id:a.id,version:a.version,sha256:a.sha256}]:[];}
  window.HtmlAssetReuse={mount,selection};
})();
