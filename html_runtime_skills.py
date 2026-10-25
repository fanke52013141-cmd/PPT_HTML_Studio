"""S06 trusted local fragments, exact identities and structured task routing.

No network, executable hooks, user document loading or dynamic registration.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from html_build_snapshot import SnapshotError, digest, fresh_hash, json_bytes, safe_file

REGISTRY = "config/html_runtime_skills.json"
PACKAGE = "config/html_runtime_skills/"
STAGE = "candidate_capacity_repair"
INPUT_CONTRACT = "candidate-layout-input/0.1.0"
OUTPUT_CONTRACT = "candidate-layout-decision/0.1.0"
STAGE_CONTRACTS = {
    STAGE: (INPUT_CONTRACT, OUTPUT_CONTRACT),
    "design_understanding": ("design-understanding-input/0.3.0", "design-understanding-output/0.3.0"),
    "design_reconstruction": ("design-reconstruction-input/0.2.0", "design-reconstruction-output/0.2.0"),
    "design_fidelity_review": ("design-review-input/0.3.0", "design-review-facts/0.1.0"),
    "design_fidelity_review_grounded": ("design-review-input/0.4.0", "design-review-facts/0.1.0"),
    "design_fidelity_review_local": ("design-review-input/0.2.0", "design-review-output/0.2.0"),
    "design_reference_localization": ("reference-localization-input/0.5.0", "reference-localization-output/0.5.0"),
}
MODES = {"legacy_prompt", "runtime_skill"}
MAX_FILE_BYTES = 16 * 1024


class RuntimeSkillError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _read(root, record):
    if (
        set(record) != {"path", "sha256"}
        or not isinstance(record["path"], str)
        or not record["path"].startswith(PACKAGE)
    ):
        raise RuntimeSkillError("RUNTIME_SKILL_PATH_NOT_ALLOWED")
    if not re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])):
        raise RuntimeSkillError("RUNTIME_SKILL_HASH_INVALID")
    try:
        path = safe_file(root, record["path"])
        if not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE_BYTES:
            raise RuntimeSkillError("RUNTIME_SKILL_FILE_MISSING_OR_TOO_LARGE")
        data = path.read_bytes()
        if digest(data) != record["sha256"]:
            raise RuntimeSkillError("RUNTIME_SKILL_HASH_MISMATCH")
        text = data.decode("utf-8")
        # References use registered placeholders only. Never follow embedded document links.
        if re.search(r"https?://|\]\s*\(|<\s*(?:script|iframe|a)\b", text, re.I):
            raise RuntimeSkillError("RUNTIME_SKILL_UNREGISTERED_REFERENCE")
        return text
    except (OSError, UnicodeError, SnapshotError) as exc:
        raise RuntimeSkillError("RUNTIME_SKILL_FILE_INVALID") from exc


@dataclass(frozen=True)
class RuntimeSkillSelection:
    root: Path
    mode: str
    fragment: str
    identity_json: str
    files_json: str

    @property
    def identity(self):
        return json.loads(self.identity_json)

    @property
    def files(self):
        return json.loads(self.files_json)

    def verify(self):
        try:
            for entry in self.files:
                if fresh_hash(safe_file(self.root, entry["path"])) != entry["sha256"]:
                    raise RuntimeSkillError("RUNTIME_SKILL_CHANGED_DURING_RUN")
        except (OSError, SnapshotError) as exc:
            raise RuntimeSkillError("RUNTIME_SKILL_CHANGED_DURING_RUN") from exc


def load_runtime_skill(repo_root, *, stage=STAGE, mode=None):
    root = Path(repo_root).resolve()
    try:
        registry_path = safe_file(root, REGISTRY)
        if registry_path.stat().st_size > MAX_FILE_BYTES:
            raise RuntimeSkillError("RUNTIME_SKILL_REGISTRY_BUDGET")
        data = registry_path.read_bytes()
        registry = json.loads(data)
        if (
            set(registry) != {"format", "version", "default_mode", "skills"}
            or registry["format"] != "hps.html.runtime_skill_registry"
            or registry["version"] != "0.1.0"
        ):
            raise RuntimeSkillError("RUNTIME_SKILL_REGISTRY_UNSUPPORTED")
        if registry["default_mode"] not in MODES or (
            mode is not None and mode not in MODES
        ):
            raise RuntimeSkillError("RUNTIME_SKILL_MODE_UNSUPPORTED")
        mode = mode or registry["default_mode"]
        if (
            stage not in STAGE_CONTRACTS
            or not isinstance(registry["skills"], list)
            or not 1 <= len(registry["skills"]) <= len(STAGE_CONTRACTS)
        ):
            raise RuntimeSkillError("RUNTIME_SKILL_STAGE_UNSUPPORTED")
        stages = [e.get("stage") for e in registry["skills"] if isinstance(e, dict)]
        if len(stages) != len(registry["skills"]) or len(set(stages)) != len(stages) or any(s not in STAGE_CONTRACTS for s in stages):
            raise RuntimeSkillError("RUNTIME_SKILL_STAGE_UNSUPPORTED")
        entries = [e for e in registry["skills"] if e["stage"] == stage]
        if len(entries) != 1:
            raise RuntimeSkillError("RUNTIME_SKILL_STAGE_UNSUPPORTED")
        entry = entries[0]
        if (
            set(entry)
            != {
                "id",
                "version",
                "stage",
                "input_contract",
                "output_contract",
                "body",
                "references",
            }
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", entry["id"])
            or not re.fullmatch(r"\d+\.\d+\.\d+", entry["version"])
        ):
            raise RuntimeSkillError("RUNTIME_SKILL_ENTRY_INVALID")
        if (entry["stage"], entry["input_contract"], entry["output_contract"]) != (
            stage,
            *STAGE_CONTRACTS[stage],
        ):
            raise RuntimeSkillError("RUNTIME_SKILL_CONTRACT_INCOMPATIBLE")
        if (
            not isinstance(entry["references"], dict)
            or len(entry["references"]) > 8
            or any(
                not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", k)
                for k in entry["references"]
            )
        ):
            raise RuntimeSkillError("RUNTIME_SKILL_REFERENCES_INVALID")
        body = _read(root, entry["body"])
        refs = {
            name: _read(root, record)
            for name, record in sorted(entry["references"].items())
        }
        markers = re.findall(r"\{\{reference:([a-z0-9-]+)\}\}", body)
        if len(markers) != len(set(markers)) or set(markers) != set(refs):
            raise RuntimeSkillError("RUNTIME_SKILL_REFERENCE_NOT_REGISTERED")
        for name, text in refs.items():
            if "{{" in text or "}}" in text:
                raise RuntimeSkillError("RUNTIME_SKILL_NESTED_REFERENCE")
            body = body.replace("{{reference:" + name + "}}", text)
        if "{{" in body or "}}" in body:
            raise RuntimeSkillError("RUNTIME_SKILL_REFERENCE_INVALID")
        files = [
            {"path": REGISTRY, "sha256": digest(data)},
            entry["body"],
            *entry["references"].values(),
        ]
        if len({r["path"] for r in files}) != len(files):
            raise RuntimeSkillError("RUNTIME_SKILL_DUPLICATE_PATH")
        identity = {
            "format": "hps.html.runtime_skill_selection",
            "version": "0.1.0",
            "stage": stage,
            "mode": mode,
            "registry_sha256": digest(data),
            "loaded": mode == "runtime_skill",
            "skills": [
                {
                    "id": entry["id"],
                    "version": entry["version"],
                    "content_sha256": digest(body.encode("utf-8")),
                    "body": entry["body"],
                    "references": entry["references"],
                }
            ]
            if mode == "runtime_skill"
            else [],
        }
        identity["selection_id"] = digest(json_bytes(identity))
        selection = RuntimeSkillSelection(
            root,
            mode,
            body if mode == "runtime_skill" else "",
            json_bytes(identity).decode("utf-8"),
            json_bytes(files).decode("utf-8"),
        )
        selection.verify()
        return selection
    except (OSError, KeyError, TypeError, json.JSONDecodeError, SnapshotError) as exc:
        raise RuntimeSkillError("RUNTIME_SKILL_REGISTRY_INVALID") from exc


def runtime_source_files(repo_root):
    records = {}
    registry = json.loads(safe_file(repo_root, REGISTRY).read_text(encoding="utf-8"))
    for entry in registry["skills"]:
        for record in load_runtime_skill(repo_root, stage=entry["stage"]).files:
            records[record["path"]] = record
    return list(records.values())


def route_task(facts):
    """Facts are caller annotations, not an NLP classifier or new production orchestrator."""
    if not isinstance(facts, dict) or facts.get("backend") != "html":
        return {"route": "not_applicable", "runtime_stage": None}
    intent, error = facts.get("intent"), facts.get("error")
    if facts.get("semantic_change") or intent == "replan":
        route = "replan"
    elif error in {"resource", "schema", "font", "provider"}:
        route = "diagnose"
    elif error == "revision_conflict":
        route = "reread"
    elif intent == "repair" and facts.get("saved") is False and error == "capacity":
        return {"route": "candidate_repair", "runtime_stage": STAGE}
    elif intent == "repair" and facts.get("saved") is True:
        route = "saved_repair"
    elif intent in {
        "produce",
        "evidence",
        "asset_reuse",
        "snapshot_verify",
        "qa_verify",
        "evaluate",
        "signature_check",
        "skill_verify",
        "audio_gate",
        "relation_check",
    }:
        route = intent
    else:
        route = "not_applicable"
    return {"route": route, "runtime_stage": None}
