"""Reconcile all original 69 criteria without promoting narrower engineering proof.

JUnit evidence verifies test execution. Real-model, human and release criteria
remain partial/not_run until their own required evidence is supplied.
"""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from artifact_fingerprint import sha256_file  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402

OWNERS={
 'T00':(['scripts/verify_reconstruction_v2_acceptance.py'],['checks/test_html_optimization_acceptance.py'],'真实跨课程dataset/留出页证据尚未完成'),
 'T01':(['html_reconstruction_diagnostics.py'],['checks/test_html_reconstruction_diagnostics.py'],'逐code/单位合同仍按各AC验收'),
 'T02':(['html_saved_layout_repair.py','html_capacity_repair.py'],['checks/test_html_saved_layout_repair.py','checks/test_html_candidate_capacity_solver.py'],'已保存/未保存适配及保护；全量INV-05须独立核对'),
 'T03':(['html_capacity_repair.py'],['checks/test_html_candidate_capacity_solver.py','checks/test_html_search_scheduling.py'],'累计搜索已实现；原全部极端夹具不能由少量成功案例替代'),
 'T04':(['html_linked_layout.py','html_geometry_repair.py'],['checks/test_html_linked_layout.py','checks/test_html_production_preflight.py'],'原全帧门禁与point路由；完整负例分母另核对'),
 'T05':(['html_production_service.py','html_design_reconstruction.py'],['checks/test_html_design_reconstruction.py','checks/test_html_production_recovery.py'],'生产检查点已接入；取消/过期/不覆盖证据分别留存'),
 'T06':(['html_reference_localization.py','html_review_evidence.py','html_reference_routes.py'],['checks/test_html_independent_review.py','checks/test_html_reference_api.py'],'工程/模拟响应不证明真实模型定位准确率'),
 'T07':(['html_design_agent.py'],['checks/test_html_design_agent.py'],'完整配对模型实验尚未完成'),
 'T08':(['html_design_feasibility.py','html_asset_reuse.py'],['checks/test_html_asset_reuse.py','checks/test_html_design_feasibility.py'],'已有工程路径；真实模型和视觉判断仍独立'),
 'T09':(['html_page_budget.py','html_reference_jobs.py','html_review_cache.py'],['checks/test_html_page_budget.py','checks/test_html_reference_api.py','checks/test_html_review_cache.py'],'预算/缓存/恢复可离线验证；完整指标须对应原要求'),
 'T10':([],[],'待真实模型及人工配对评测；不得用mock或离线报告签发通过'),
 'T11':(['html_build_snapshot.py'],['checks/test_html_build_snapshot.py'],'尚未发布；正式音视频与具体发布commit待验'),
}


def reconcile(plan, junit=(), criterion_verification=None):
    items=plan['acceptance']
    expected={f'AC-{i:03d}' for i in range(1,70)}
    if len(items)!=69 or {a['id'] for a in items}!=expected:
        raise ValueError('ORIGINAL_69_CRITERIA_INCOMPLETE')
    evidence=[];executed=set()
    for path in map(Path,junit):
        root=ET.parse(path).getroot()
        for case in root.iter('testcase'):
            if not any(case.find(k) is not None for k in ('failure','error','skipped')):
                executed.add(case.get('classname','').replace('.','/')+'.py')
        resolved=path.resolve()
        evidence.append({'path':resolved.relative_to(ROOT).as_posix() if resolved.is_relative_to(ROOT) else str(resolved),
                         'sha256':sha256_file(path)})
    rows=[]
    for item in items:
        sources,tests,gap=OWNERS[item['task_id']]
        existing=[p for p in sources if (ROOT/p).is_file()]
        verified=[p for p in tests if p in executed]
        # Presence and executed task-level tests are partial evidence only:
        # this deliberately never infers full criterion coverage from a filename.
        proof=next((r for r in (criterion_verification or {}).get('criteria',[]) if r['id']==item['id']),None)
        status='partial' if existing else 'not_run'
        if proof and proof['status'] in ('passed','failed'):status=proof['status']
        rows.append({'id':item['id'],'task_id':item['task_id'],'criterion':item['criterion'],
            'required_level':item['required_level'],'status':status,
            'criterion_verification':proof,
            'implementation':'implemented_scope' if existing else 'not_started_or_validation_only',
            'sources':[{'path':p,'sha256':sha256_file(ROOT/p)} for p in existing],
            'candidate_tests':[p for p in tests if (ROOT/p).is_file()],
            'executed_test_modules':verified,'evidence':evidence if verified else [],
            'remaining':gap if status!='passed' else '本条所需层级的独立检查已通过；不代替其他AC或整体验收。'})
    return {'format':'hps.reconstruction.acceptance-ledger/0.1.0','criteria':rows,
        'counts':{s:sum(r['status']==s for r in rows) for s in ('passed','partial','not_run','failed')},
        'milestones':{m:'pending' for m in plan['milestone_rules']},
        'policy':'Task-level source/test evidence is partial; only separately verified per-AC proof can pass required levels.'}


def write_markdown(result,path):
    text='# 图片转HTML原69项验收对账\n\n逐项列明实现、测试证据和缺口。partial不等于passed，真实模型、人审和发布门槛不由离线测试替代。\n\n'
    text+='| AC | 任务 | 原验收要求 | 要求层级 | 状态 | 已有实现/测试 | 剩余事项 |\n|---|---|---|---|---|---|---|\n'
    for row in result['criteria']:
        text+='| '+' | '.join(str(v).replace('|','／').replace('\n',' ') for v in (
            row['id'],row['task_id'],row['criterion'],row['required_level'],row['status'],
            ', '.join(s['path'] for s in row['sources'])+'；测试：'+', '.join(row['candidate_tests']),row['remaining']))+' |\n'
    Path(path).write_text(text,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json')
    parser.add_argument('--junit',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--criterion-evidence',type=Path)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text(encoding='utf-8'))
    proof=None
    if args.criterion_evidence:
        from html_acceptance_criteria import verify,read
        proof=verify(plan,read(ROOT/'config/html_acceptance_criteria.json'),read(args.criterion_evidence),ROOT)
    result=reconcile(plan,args.junit,proof)
    write_json_atomic(args.output,result);write_markdown(result,args.output.with_suffix('.md'))
    print(json.dumps({'criteria':len(result['criteria']),'counts':result['counts'],'milestones':result['milestones']}))


if __name__=='__main__':main()
