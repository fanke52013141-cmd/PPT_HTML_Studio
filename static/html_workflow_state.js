// Display projections over existing current artifact facts, never approvals.
(function () {
  'use strict';
  const cache = new Map();
  const pending = new Map();
  const versions = new Map();
  function aggregate(states) {
    if (!states.length) return 'pending';
    if (states.every(value => value === 'completed')) return 'completed';
    if (states.includes('blocked')) return 'blocked';
    if (states.includes('pending_reconfirmation')) return 'pending_reconfirmation';
    if (states.includes('pending_review')) return 'pending_review';
    if (states.some(value => value !== 'pending')) return 'in_progress';
    return 'pending';
  }
  function state(value) {
    return ({ready:'completed',needs_review:'pending_review',stale:'pending_reconfirmation',
      invalid:'blocked',blocked:'blocked',in_progress:'in_progress',not_started:'pending'})[value] || 'pending';
  }
  function projectStates(project, response) {
    const stages = response?.workflow?.stages || [];
    const byId = Object.fromEntries(stages.map(stage => [stage.id,stage]));
    const visual = byId.design_and_assets || {};
    const ids = byId.content_planning?.facts?.slide_ids || Object.keys(response?.slides || {});
    const designStates = ids.map(id => {
      const design = visual.design_candidates?.[id];
      if (!design) return 'pending';
      if (design.stale) return 'pending_reconfirmation';
      if (design.status === 'accepted_for_reconstruction') return 'completed';
      return state(design.status);
    });
    const pageStates = ids.map(id => state(visual.slides?.[id]?.status));
    const audio = state(byId.audio?.status);
    const sync = state(byId.animation?.status);
    return {
      1: project.step_status?.['1'] === 'completed' ? 'completed' : state(byId.project_setup?.status)==='completed' ? 'in_progress' : 'pending',
      2: state(byId.content_planning?.status),
      3: aggregate(designStates), 5: aggregate(pageStates),
      6: audio === 'completed' ? sync : audio,
      9: byId.digital_human?.status === 'skipped' ? 'skipped' : state(byId.digital_human?.status),
      8: response?.currentVideo === true && byId.review_and_output?.targets?.mp4_video?.ready === true ? 'completed' :
        byId.review_and_output?.targets?.mp4_video?.ready ? 'ready_to_export' : 'pending'
    };
  }
  async function load(project, {force=false}={}) {
    if (!project || project.visual_backend !== 'html') return null;
    const id = project.id;
    if (!force && cache.has(id)) return cache.get(id);
    if (!force && pending.has(id)) return pending.get(id);
    const version=(versions.get(id)||0)+1;versions.set(id,version);
    const request = Promise.all([
      API.get(`/api/projects/${encodeURIComponent(id)}/html-visual/status`,{silent:true}),
      API.get(`/api/projects/${encodeURIComponent(id)}/videos`,{silent:true})
        .catch(()=>({videos:[]}))
    ]).then(([response,outputs]) => {
        response={...response,currentVideo:(outputs.videos||[]).some(item=>item.artifact_state==='current'&&!item.historical)};
        const value = {response,states:projectStates(project,response)};
        if(versions.get(id)===version)cache.set(id,value);
        return value;
      }).catch(error=>{if(versions.get(id)===version)cache.delete(id);throw error;})
      .finally(()=>{if(pending.get(id)===request)pending.delete(id);});
    pending.set(id,request);
    return request;
  }
  function get(id) { return cache.get(id) || null; }
  function invalidate(id) { cache.delete(id);versions.set(id,(versions.get(id)||0)+1);pending.delete(id); }
  window.HtmlWorkflowState = {load,get,invalidate,projectStates};
})();
