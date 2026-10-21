"""Explicit deterministic model fixtures; never represent live visual judgments."""
import json


def with_coverage(payload, response):
    """Explicit model double; not used by production or live evaluations."""
    rows = []
    for check in payload.get('review_checklist', []):
        indices = []
        for index, item in enumerate(response['issues']):
            dimension = {'semantic_text':'content','theme_conflict':'structure',
                'registered_variant':'structure','unsupported_presentation':'structure'}.get(item['requirement'],item['requirement'])
            if (item['targetId'],dimension) == (check['targetId'],check['dimension']):indices.append(index)
        rows.append({**check,'status':'issue' if indices else 'pass',
                     'evidence':'deterministic fixture observation','issue_indices':indices})
        if check['dimension']=='typography' and check['targetId'] in payload.get('text_alignment_contract',{}):
            rows[-1]['reference_alignment']=payload['text_alignment_contract'][check['targetId']]['align']
    if payload.get('review_output_contract') == 'design-review-facts/0.1.0':
        facts=[]
        for row in rows:
            items=[response['issues'][i] for i in row['issue_indices']]
            facts.append({'targetId':row['targetId'],'dimension':row['dimension'],'certainty':'confirmed',
                'evidence':items[0]['evidence'] if items else row['evidence'],
                'reference_alignment':row.get('reference_alignment'),
                'differences':[{k:v for k,v in item.items() if k in ('requirement','severity','suggestion','variant_id','reference_detail')} for item in items]})
        return {'facts':facts}
    return {**response,'coverage':rows}


def response_for(kwargs):
    prefix = kwargs.get("artifact_prefix", "")
    if prefix.startswith("design_understanding-"):
        data = json.loads(kwargs["user_prompt"])
        return {"status":"ready","objects":[{
            "targetId":n["id"],"owner":data["capabilities"][n["id"]]["owner"],
            "assetMode":data["capabilities"][n["id"]]["assetMode"],
            "variant":None,"icon":None,"appearance":"fixture observation only",
        } for n in data["objects"]],"issues":[], "feature_observations": [
            {'targetId': n['id'], 'feature': 'independent_illustration',
             'presence': 'present' if n['type'] == 'image' else 'absent',
             'evidence': 'Controlled observation fixture, not inferred model recognition'} for n in data['objects']]}
    if prefix.startswith("design_fidelity_review-"):
        return with_coverage(json.loads(kwargs['user_prompt']), {"status":"pass","issues":[]})
    return None
