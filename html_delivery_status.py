"""Safe display projection of existing formal-export evidence."""


def delivery_evidence(metadata):
    evidence = metadata.get("export_evidence")
    if not isinstance(evidence, dict):
        return None
    return {"snapshot_id": evidence.get("snapshot_id"),
            "pages": [{"slide_id": page.get("slide_id"), "reused": bool(page.get("reused"))}
                      for page in evidence.get("pages", [])]}
