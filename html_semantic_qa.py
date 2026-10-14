"""Pure A04 source, sampling, action, visibility and model evidence validation."""
from artifact_fingerprint import sha256_json
from html_audio_binder import bind_scene_to_audio
from html_semantic_qa_models import BeatVerdict


class SemanticQAError(ValueError):
    def __init__(self, code, message=None):
        self.code = code
        super().__init__(message or code)


def required(scene):
    return scene.get("version") in ("0.6.0", "0.7.0")


def prepare(scene, plan, binding, contract, timeline):
    from html_storyboard_planning import normalize_html_scene_plan, load_template_catalog
    from pathlib import Path
    if not required(scene) or plan.get("version") != "0.2.0":
        raise SemanticQAError("SEMANTIC_VERSION_REQUIRED")
    plan = normalize_html_scene_plan(plan, load_template_catalog(Path(__file__).parent), contract_slide=contract)
    if not 1 <= len(plan["beats"]) <= 40:
        raise SemanticQAError("SEMANTIC_BEAT_BUDGET")
    if scene.get("id") != plan.get("slide_id") or contract.get("slide_id") != scene.get("id"):
        raise SemanticQAError("SEMANTIC_PAGE_MISMATCH")
    nodes = {n["id"]: n for n in scene["nodes"]}
    planned = {o["id"]: o for o in plan["objects"]}
    if set(nodes) != set(planned) or any(nodes[k]["type"] != planned[k]["kind"] for k in nodes):
        raise SemanticQAError("SEMANTIC_OBJECT_MISMATCH")
    if set(scene.get("initialVisibleIds", [])) != {k for k,o in planned.items() if o["initialVisible"]}:
        raise SemanticQAError("SEMANTIC_INITIAL_STATE_MISMATCH")
    motions = {a["actionId"]: a for a in scene["motion"]}
    desired = {a["actionId"]:(b["id"], a) for b in plan["beats"] for a in b["actions"]}
    if set(motions) != set(desired):
        raise SemanticQAError("SEMANTIC_ACTION_MISMATCH")
    for identity,(beat,action) in desired.items():
        if (motions[identity]["targetId"],motions[identity]["type"]) != (action["objectId"],action["type"]) or binding["actions"].get(identity,{}).get("beatId") != beat:
            raise SemanticQAError("SEMANTIC_ACTION_MISMATCH")
    source = [{k:b[k] for k in ("id","spoken_text","spoken_text_sha256")} for b in plan["beats"]]
    if binding.get("sourceBeats") != source:
        raise SemanticQAError("SEMANTIC_SPOKEN_MISMATCH")
    bound = bind_scene_to_audio(scene, timeline, binding)
    windows = {}
    for s in timeline["segments"]:
        key=s.get("beat_id") or s.get("id")
        start,end=round(s["start"]*1000),round(s["end"]*1000)
        previous=windows.get(key,(start,end));windows[key]=(min(start,previous[0]),max(end,previous[1]))
    beats=[]
    for b in plan["beats"]:
        start,end=windows[b["id"]]
        if end-start < 2:
            raise SemanticQAError("SEMANTIC_WINDOW_TOO_SHORT")
        related = {t["objectId"] for t in b["targets"]} | set(scene.get("initialVisibleIds",[]))
        actions=[a for a in bound["motion"] if binding["actions"][a["actionId"]]["beatId"]==b["id"]]
        if any(a["startMs"] < start or a["startMs"]+a["durationMs"] > end for a in actions):
            raise SemanticQAError("SEMANTIC_ACTION_WINDOW")
        beats.append({"id":b["id"],"spoken_text":b["spoken_text"],"visualIntent":b["visualIntent"],"expectedState":b["expectedState"],"narration_only":b["narration_only"],"narrationOnlyReason":b.get("narrationOnlyReason"),"times":[start,(start+end)/2,end-1],"window":[start,end],"actions":actions,"objects":[{**nodes[k],"declaredRole":planned[k]["role"]} for k in nodes if k in related]})
    return {"bound_scene":bound,"beats":beats}


def check_frames(prepared, frames):
    if len(frames)!=len(prepared["beats"])*3:
        raise SemanticQAError("SEMANTIC_FRAME_COVERAGE")
    issues=[]
    for index,beat in enumerate(prepared["beats"]):
        group=frames[index*3:index*3+3]
        if [f.get("timeMs") for f in group] != beat["times"] or any(f.get("beatId") != beat["id"] or f.get("frameIndex") != i for i,f in enumerate(group)):
            raise SemanticQAError("SEMANTIC_FRAME_COVERAGE")
        for state in beat["expectedState"]:
            visible=group[-1].get("visible",{}).get(state["objectId"])
            if not isinstance(visible,(int,float)) or (state["visible"] and visible<=0.01):
                issues.append({"code":"SEMANTIC_TARGET_NOT_VISIBLE","beatId":beat["id"],"targetId":state["objectId"],"timeMs":group[-1]["timeMs"]})
    return issues


def validate_verdict(value, beat):
    value=BeatVerdict.model_validate(value).model_dump()
    ids={n["id"] for n in beat["objects"]}
    pairs=[]
    for evidence in value["evidence"]:
        if not evidence["observation"].strip() or (evidence["targetId"] is not None and evidence["targetId"] not in ids):
            raise SemanticQAError("SEMANTIC_EVIDENCE_UNKNOWN")
        pairs.append((evidence["frameIndex"],evidence["targetId"]))
    if len(set(pairs)) != len(pairs):
        raise SemanticQAError("SEMANTIC_EVIDENCE_DUPLICATE")
    return value


def semantic_state(results):
    if any(r["verdict"] in ("omitted","contradiction") for r in results):
        return "failed"
    return "passed" if results and all(r["verdict"]=="related" and r["confidence"]>=0.8 for r in results) else "needs_review"


def seal(value):
    return {**value,"sha256":sha256_json(value)}


def verify_seal(value):
    if not isinstance(value,dict) or value.get("sha256") != sha256_json({k:v for k,v in value.items() if k!="sha256"}):
        raise SemanticQAError("SEMANTIC_REPORT_INVALID")
    return value
