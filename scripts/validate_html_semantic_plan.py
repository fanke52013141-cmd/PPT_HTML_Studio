"""Isolated A01 planning smoke test; not automatic course or visual acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Authoritative contract slide JSON")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout", type=int, default=90, help="Per-request seconds, 30..300; no timeout retry")
    parser.add_argument("--settings-db", type=Path, default=ROOT / "data/projects.db")
    args = parser.parse_args()
    if not 30 <= args.timeout <= 300:
        parser.error("timeout must be 30..300 seconds")
    contract = json.loads(args.input.read_text(encoding="utf-8"))
    if not args.live:
        print(json.dumps({"plan_version": "0.2.0", "slide_id": contract.get("slide_id"), "max_planning_rounds": 2, "http_budget": 4, "timeout": args.timeout, "live": False}))
        return 0
    if args.out.exists():
        raise ValueError("EVALUATION_DIRECTORY_EXISTS")
    from scripts.evaluate_html_runtime_skills import read_text_connection

    settings = read_text_connection(args.settings_db)  # read-only before DB imports
    with tempfile.TemporaryDirectory(prefix="hps-a01-") as temp:
        os.environ["PPT_STUDIO_DB_PATH"] = str(Path(temp) / "evaluation.db")
        os.environ["PPT_STUDIO_RUNS_DIR"] = str(Path(temp) / "runs")
        import json_llm_service as llm
        from project_model_binding_service import FrozenModel
        from html_visual_review_service import generate_scene_plan, HtmlReviewError
        from html_storyboard_planning import plan_evidence

        args.out.mkdir(parents=True)
        def write(name, value):
            (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        sources = {}
        for name in ("html_semantic_plan.py", "html_semantic_design.py", "html_planning_context.py", "html_storyboard_planning.py", "html_visual_review_service.py", "html_design_brief.py", "html_reference_package.py"):
            raw = (ROOT / name).read_bytes()
            sources[name] = hashlib.sha256(raw).hexdigest()
            (args.out / name).write_bytes(raw)
        write("input.json", contract)
        binding = FrozenModel(settings.get("llm_provider") or "openai_compatible", settings["llm_model"], settings["llm_base_url"], settings["llm_api_key"], "global_read_only", None, "a01-evaluation", max_tokens=8192)
        factory, attempts = llm.get_openai_client, []
        def wrapped_client(**kwargs):
            client = factory(**kwargs)
            original = client.chat.completions.create
            def create(**request):
                if len(attempts) >= 4:
                    raise ValueError("EVALUATION_HTTP_BUDGET_EXHAUSTED")
                record = {"attempt": len(attempts) + 1, "success": False, "usage": None, "provider_outcome": "unknown"}
                attempts.append(record)
                start = time.monotonic()
                try:
                    response = original(**request)
                    record["success"] = True
                    record["provider_outcome"] = "returned"
                    if response.usage:
                        record["usage"] = {k: getattr(response.usage, k, None) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
                    return response
                except Exception as exc:
                    record["error_type"] = type(exc).__name__
                    raise
                finally:
                    record["elapsed_seconds"] = round(time.monotonic() - start, 3)
                    write("http-attempts.json", attempts)
            client.chat.completions.create = create
            return client
        llm.get_openai_client = wrapped_client
        def generator(**kwargs):
            return llm.generate_json_with_configured_llm(**kwargs, model_binding=binding, temperature=0, request_timeout=args.timeout, max_tokens_default=8192, max_tokens_limit=8192)
        summary = {"model": settings["llm_model"], "source_sha256": sources, "request_config": {"temperature": 0, "max_tokens": 8192, "timeout": args.timeout}, "meaning": "pending_review", "runtime": "not_implemented", "cost": None, "manual_plan_edits": 0}
        try:
            plan = generate_scene_plan(contract, run_dir=args.out, repo_root=ROOT, json_generator=generator, plan_version="0.2.0")
            write("plan.json", plan)
            write("evidence.json", plan_evidence(plan))
            summary["structure"] = "passed"
        except HtmlReviewError as exc:
            summary.update(structure="failed", code=exc.code)
        except Exception as exc:
            summary.update(structure="failed", code=type(exc).__name__, cause_type=type(exc.__cause__).__name__ if exc.__cause__ else None)
        finally:
            llm.get_openai_client = factory
            summary["http_attempts"] = len(attempts)
            summary["source_unchanged"] = all(hashlib.sha256((ROOT / k).read_bytes()).hexdigest() == v for k, v in sources.items())
            if not summary["source_unchanged"]:
                summary["structure"] = "invalid_source_changed"
            write("summary.json", summary)
            module = sys.modules.get("database")
            if module:
                module.engine.dispose()
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary["structure"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
