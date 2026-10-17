"""Single model-owned observations; deterministic legacy review projections."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from html_design_policy import Requirement, ReferenceDetail, reference_observation


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Difference(Strict):
    requirement: Requirement
    severity: Literal['minor','major']
    suggestion: str = Field(min_length=1,max_length=600)
    variant_id: str | None = None
    reference_detail: ReferenceDetail | None = None


class ReviewFact(Strict):
    targetId: str
    dimension: Literal['geometry','content','typography','structure','semantic_relation','asset_identity','asset_rendering']
    certainty: Literal['confirmed','uncertain']
    evidence: str = Field(min_length=1,max_length=300)
    reference_alignment: Literal['left','center','right','uncertain'] | None = None
    differences: list[Difference] = Field(max_length=4)


class ReviewFacts(Strict):
    facts: list[ReviewFact] = Field(max_length=280)


def project_facts(response, scene, checklist, alignment):
    """No inferred reference facts. Compare reported reference to known current CSS."""
    if not isinstance(response,dict) or 'facts' not in response:
        raise ValueError('REVIEW_COVERAGE_INCOMPLETE: facts are required by this request')
    parsed = ReviewFacts.model_validate(response)
    expected = {(v['targetId'],v['dimension']) for v in checklist}
    actual = [(f.targetId,f.dimension) for f in parsed.facts]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('REVIEW_COVERAGE_INCOMPLETE: missing, duplicate or unknown facts')
    nodes = {n['id']:n for n in scene['nodes']}
    issues, coverage, sources = [], [], []
    for index, fact in enumerate(parsed.facts):
        if fact.certainty != 'confirmed' or not fact.evidence.strip() or fact.reference_alignment == 'uncertain':
            raise ValueError('REVIEW_COVERAGE_INCOMPLETE: uncertain or blank fact')
        if fact.reference_alignment is not None and fact.dimension != 'typography':
            raise ValueError('REVIEW_COVERAGE_INCOMPLETE: alignment belongs to typography')
        for difference in fact.differences:
            dim = {'semantic_text':'content','theme_conflict':'structure','registered_variant':'structure',
                   'unsupported_presentation':'structure'}.get(difference.requirement,difference.requirement)
            if dim != fact.dimension:
                raise ValueError('REVIEW_COVERAGE_INCOMPLETE: difference belongs to another fact dimension')
            issues.append({**difference.model_dump(),'targetId':fact.targetId,'evidence':fact.evidence})
            sources.append({'issue_index':len(issues)-1,'fact_index':index,'source':'reported_difference'})
        current = (alignment or {}).get(fact.targetId)
        if fact.dimension == 'typography' and current:
            if fact.reference_alignment in (None,'uncertain'):
                raise ValueError('REVIEW_COVERAGE_INCOMPLETE: missing reference text alignment')
            if fact.reference_alignment != current['align']:
                issues.append({'targetId':fact.targetId,'requirement':'typography','severity':'minor',
                    'evidence':fact.evidence,
                    'suggestion':f"参考对齐为{fact.reference_alignment}，当前注册合同为{current['align']}；通过受控文字对齐操作核对修正。"})
                sources.append({'issue_index':len(issues)-1,'fact_index':index,'source':'alignment_comparison'})
        linked = [s['issue_index'] for s in sources if s['fact_index']==index]
        blocking = any(not reference_observation(issues[i],nodes[fact.targetId]) for i in linked)
        coverage.append({'targetId':fact.targetId,'dimension':fact.dimension,
                         'status':'issue' if blocking else 'pass','evidence':fact.evidence,
                         'reference_alignment':fact.reference_alignment,'issue_indices':linked})
    return {'status':'changes_requested' if issues else 'pass','issues':issues,'coverage':coverage}, sources
