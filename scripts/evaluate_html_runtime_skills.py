"""S06 paired evaluation. --live explicitly uses the existing text model, never server.

Read configuration via SQLite read-only before importing application DB modules;
all runtime imports then use an isolated experiment database/run root.
"""

from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read_text_connection(database):
    with sqlite3.connect(
        Path(database).resolve().as_uri() + "?mode=ro", uri=True
    ) as db:
        settings = dict(
            db.execute(
                "SELECT key,value FROM settings WHERE key IN ('llm_model','llm_provider','llm_base_url','llm_api_key')"
            )
        )
    if not all(settings.get(k) for k in ("llm_model", "llm_base_url", "llm_api_key")):
        raise ValueError("TEXT_MODEL_CONNECTION_MISSING")
    return settings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--settings-db", type=Path, default=ROOT / "data/projects.db")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    output = args.out.resolve()
    if output.exists():
        raise ValueError("EVALUATION_DIRECTORY_EXISTS")
    if not args.live:
        print(
            json.dumps(
                {
                    "mode": "dry_run",
                    "cases": ["condensation", "water-facts", "evaporation-process"],
                    "decisions_per_arm": 2,
                    "http_attempt_budget_per_arm": 6,
                    "max_tokens": 2048,
                    "out": str(output),
                },
                ensure_ascii=False,
            )
        )
        return 0
    settings = read_text_connection(args.settings_db)
    # Set before imports so migration/config fallbacks cannot touch the user's database.
    isolation = tempfile.TemporaryDirectory(prefix="hps-s06-eval-")
    os.environ["PPT_STUDIO_DB_PATH"] = str(Path(isolation.name) / "evaluation.db")
    os.environ["PPT_STUDIO_RUNS_DIR"] = str(Path(isolation.name) / "runs")
    try:
        from html_skill_evaluation import evaluate_pairs
        from html_build_snapshot import json_bytes, digest
        from project_model_binding_service import FrozenModel
        from pipeline_lifecycle import write_json_atomic
        import json_llm_service as llm

        identity = {
            "provider": settings.get("llm_provider") or "openai_compatible",
            "model": settings["llm_model"],
            "config_digest": digest(
                json_bytes(
                    {
                        "model": settings["llm_model"],
                        "endpoint": settings["llm_base_url"],
                        "temperature": 0,
                        "max_tokens": 2048,
                        "timeout": 90,
                    }
                )
            ),
        }
        binding = FrozenModel(
            identity["provider"],
            identity["model"],
            settings["llm_base_url"],
            settings["llm_api_key"],
            "global_read_only",
            None,
            identity["config_digest"],
            max_tokens=2048,
        )
        factory = llm.get_openai_client
        records, per_arm = [], {}
        current = {"arm": ""}

        def client_factory(**kwargs):
            client = factory(**kwargs)
            original = client.chat.completions.create

            def create(**request):
                arm = current["arm"]
                if per_arm.get(arm, 0) >= 6:
                    raise ValueError("EVALUATION_HTTP_BUDGET_EXHAUSTED")
                per_arm[arm] = per_arm.get(arm, 0) + 1
                record = {
                    "arm": arm,
                    "attempt": per_arm[arm],
                    "max_tokens": request.get("max_tokens"),
                    "temperature": request.get("temperature"),
                    "usage": None,
                    "success": False,
                    "message_sha256": hashlib.sha256(
                        json_bytes(request["messages"])
                    ).hexdigest(),
                }
                records.append(record)
                start = time.monotonic()
                try:
                    response = original(**request)
                    record["success"] = True
                    if response.usage is not None:
                        record["usage"] = {
                            k: getattr(response.usage, k, None)
                            for k in (
                                "prompt_tokens",
                                "completion_tokens",
                                "total_tokens",
                            )
                        }
                    return response
                finally:
                    record["elapsed_seconds"] = round(time.monotonic() - start, 3)
                    write_json_atomic(output / "http-attempts.json", records)

            client.chat.completions.create = create
            return client

        llm.get_openai_client = client_factory
        delegate = partial(
            llm.generate_json_with_configured_llm,
            model_binding=binding,
            temperature=0,
            request_timeout=90,
            max_tokens_default=2048,
            max_tokens_limit=2048,
        )

        def generator(**kwargs):
            current["arm"] = str(Path(kwargs["run_dir"]).relative_to(output)).replace(
                "\\", "/"
            )
            return delegate(**kwargs)

        result = evaluate_pairs(ROOT, output, generator, model_identity=identity)
        result["real_model"] = "executed" if records else "not_tested"
        result["http_attempts"] = len(records)
        result["usage"] = {
            k: sum(
                r["usage"][k]
                for r in records
                if r["usage"] and r["usage"][k] is not None
            )
            if any(r["usage"] and r["usage"][k] is not None for r in records)
            else None
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        for arm in result["arms"]:
            name = arm["case_id"] + "/" + arm["mode"]
            attempts = [r for r in records if r["arm"] == name]
            arm["http_attempts"] = len(attempts)
            arm["usage"] = [r["usage"] for r in attempts]
        result["candidate_default_eligible"] = (
            all(r["same_first_model_input"] for r in result["comparability"])
            and result["metrics"]["runtime_skill"]["engineering_passed"]
            == result["metrics"]["runtime_skill"]["cases"]
            and result["metrics"]["runtime_skill"]["manual_intervention_required"]
            <= result["metrics"]["legacy_prompt"]["manual_intervention_required"]
            and result["metrics"]["runtime_skill"]["adapter_calls"]
            <= result["metrics"]["legacy_prompt"]["adapter_calls"]
        )
        write_json_atomic(output / "results.json", result)
        print(
            json.dumps(
                {
                    "experiment_id": result["experiment_id"],
                    "model": identity["model"],
                    "metrics": result["metrics"],
                    "comparability": result["comparability"],
                    "http_attempts": len(records),
                    "candidate_default_eligible": result["candidate_default_eligible"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        database_module = sys.modules.get("database")
        if database_module is not None:
            database_module.engine.dispose()
        isolation.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Providers may embed request headers or URLs in errors; only report the category.
        print(
            json.dumps({"status": "failed", "error_type": type(exc).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1)
