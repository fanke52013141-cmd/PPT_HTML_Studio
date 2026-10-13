"""Explicit deterministic model fixtures; never represent live visual judgments."""
import json


def response_for(kwargs):
    prefix = kwargs.get("artifact_prefix", "")
    if prefix.startswith("design_understanding-"):
        data = json.loads(kwargs["user_prompt"])
        return {"status":"ready","objects":[{
            "targetId":n["id"],"owner":data["capabilities"][n["id"]]["owner"],
            "assetMode":data["capabilities"][n["id"]]["assetMode"],
            "variant":None,"icon":None,"appearance":"fixture observation only",
        } for n in data["objects"]],"issues":[]}
    if prefix.startswith("design_fidelity_review-"):
        return {"status":"pass","issues":[]}
    return None
