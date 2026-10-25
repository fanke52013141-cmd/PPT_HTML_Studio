"""One deterministic diagnostic projection for production and saved-page repair."""
import copy
from artifact_fingerprint import sha256_json

CATALOG={
    "CONTENT_CAPACITY_EXCEEDED":("capacity","reconstruction","修复文字容量"),
    "TEMPORAL_OVERLAP":("geometry","reconstruction","检查逐帧遮挡"),
    "TEMPORAL_SAFE_ZONE":("geometry","reconstruction","检查安全区域"),
    "GEOMETRY_REJECTED":("geometry","reconstruction","检查布局"),
    "REFERENCE_LOCALIZATION_UNRESOLVED":("reference","evidence_review","打开定位复核"),
    "REFERENCE_SOURCE_STALE":("stale","diagnostics","重新读取当前来源"),
    "BUDGET_EXHAUSTED":("budget","stop","查看预算消耗"),
    "PAGE_BUDGET_EXHAUSTED":("budget","stop","查看整页预算"),
    "NO_DETERMINISTIC_CAPACITY_FIT":("no_fit","planning","缩减内容或调整注册结构"),
    "PROVIDER_OUTCOME_UNKNOWN":("unknown","stop","核对原请求回执"),
    "MANUAL_FIELD_PROTECTED":("protection","manual_review","核对人工保护字段"),
    "REPAIR_SOURCE_CHANGED":("stale","diagnostics","重新读取页面"),
    "REVIEW_INCOMPLETE":("incomplete","diagnostics","查看完整检查报告"),
    "REVIEW_INFRASTRUCTURE_ERROR":("infrastructure","diagnostics","检查浏览器运行环境"),
    "SCENE_PREPARE_FAILED":("infrastructure","diagnostics","查看原场景编译报告"),
    "CAPACITY_SOURCE_STALE":("stale","diagnostics","重新读取容量检查来源"),
    "LINKED_LAYOUT_SOURCE_STALE":("stale","diagnostics","重新读取关联布局来源"),
    "LINKED_LAYOUT_BUDGET":("budget","stop","查看关联布局预算"),
    "CAPACITY_SEARCH_BUDGET":("budget","stop","查看容量搜索预算"),
    "NO_LINKED_LAYOUT_WITHIN_POLICY":("no_fit","planning","调整注册结构或内容"),
    "GEOMETRY_REPAIR_REQUIRED":("geometry","reconstruction","检查关联布局与关系"),
    "GEOMETRY_PREFLIGHT_FAILED":("incomplete","diagnostics","查看完整逐帧检查"),
}
UNITS={"canvas_px","css_px","px","lines","characters","count","ms","seconds","ratio","calls"}
GEOMETRY_UNITS={k:"canvas_px" for k in ("x","y","width","height","overlapWidth","overlapHeight")}


def classify(code):
    if code.startswith(("ASSET_","RESOURCE_")):
        return "resource","assets","检查资源身份与可见边界"
    return CATALOG.get(code,("incomplete","diagnostics","查看原始诊断并停止自动修复"))


def diagnostics(scene,report,*,stage):
    rows=[]
    ids=sorted((n['id'] for n in scene.get('nodes',[])),key=lambda x:(-len(x),x))
    def append(code,issue,targets,measurements):
        kind,route,label=classify(code)
        measured=copy.deepcopy(measurements)
        units={k:GEOMETRY_UNITS[k] for k in measured if k in GEOMETRY_UNITS} if isinstance(measured,dict) else {}
        unknown=[m.get('unit') if isinstance(m,dict) else None for m in measured
                 if not isinstance(m,dict) or m.get('unit') not in UNITS] if isinstance(measured,list) else []
        rows.append({'kind':kind,'code':code,'targets':targets,'part':issue.get('part'),
            'measurements':measured,'measurement_units':units,'unknown_units':unknown,
            'route':route,'action_label':label,'source_stage':stage,
            'first_time_ms':issue.get('firstTimeMs',issue.get('timeMs')),
            'automatic_repair_eligible':kind in ('capacity','geometry') and not unknown})
    for issue in report.get('capacityIssues',[]):
        raw=str(issue.get('target',''))
        target=next((i for i in ids if raw==i or raw.startswith(i+'.')),None)
        append(issue.get('code','CONTENT_CAPACITY_EXCEEDED'),issue,[target] if target else [],issue.get('triggers',[]))
    geometry=report.get('geometry_preflight') or {}
    seen=set()
    for issue in list(report.get('issues',[]))+list(geometry.get('issues',[])):
        if not isinstance(issue,dict):issue={'code':'REVIEW_INCOMPLETE','message':str(issue)}
        key=sha256_json(issue)
        if key in seen:continue
        seen.add(key)
        append(issue.get('code','GEOMETRY_REJECTED'),issue,issue.get('targets',[]),issue.get('measured',{}))
    for target in report.get('unresolved_targets',[]):
        append('REFERENCE_LOCALIZATION_UNRESOLVED',{},[target],{})
    if report.get('code') and not any(r['code']==report['code'] for r in rows):
        append(str(report['code']),report,report.get('targets',[]),report.get('measured',{}))
    if not rows and report.get('passed') is not True:append('REVIEW_INCOMPLETE',{},[],{})
    return {'version':'reconstruction-diagnostics/0.2.0','stage':stage,'scene_sha256':sha256_json(scene),
        'engineering_passed':report.get('passed') is True,'issues':rows,
        'routes':sorted({r['route'] for r in rows}),'automatic_retry':False,'human_approval':'pending'}
