"""Fault injection at response registration and author/task commit boundaries."""
import copy
import json
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from database import SessionLocal, Project
from html_workflow_jobs import HtmlWorkflowJobs
from html_visual_review_service import HtmlReviewDependencies
from html_production_recovery import reconcile_responses, receipt_path, read_receipt
import html_task_store as store
from checks.test_html_production_stages import restart, ROOT
from checks.test_html_production_stages import stage as stage
from checks.test_html_workflow_acceptance import write
from checks.test_html_object_decomposition import decomposition_plan, normalize
from checks.test_html_narration_semantics import CONTRACT_SLIDE as SEMANTIC_CONTRACT


def test_response_disk_receipt_recovers_failed_database_registration(stage, monkeypatch):
    persist = stage._persist
    def fail_registration(key, record):
        if record["state"] == "returned":
            raise RuntimeError("DB unavailable after response receipt")
        return persist(key, record)
    monkeypatch.setattr(stage, "_persist", fail_registration)
    calls = []
    fn = lambda **kw: calls.append(1) or {"result": "arrived"}
    with pytest.raises(RuntimeError):
        stage.wrap(fn, "json")(user_prompt="fixed")
    store.mark_failed(stage.db, stage.job_id, "registration crash", expected_attempt=1)
    assert reconcile_responses(stage.db, stage.job_id, stage.run) == 1
    assert reconcile_responses(stage.db, stage.job_id, stage.run) == 0
    recovered = restart(stage)
    assert recovered.wrap(fn, "json")(user_prompt="fixed") == {"result": "arrived"}
    assert len(calls) == 1


class Queryable:
    def __init__(self, state="succeeded", wrong_identity=False):
        self.sent, self.queried = [], []
        self.state, self.wrong_identity = state, wrong_identity

    def invoke_with_request_id(self, request_id, **kwargs):
        self.sent.append(request_id)
        raise TimeoutError("response lost")

    def lookup(self, request_id):
        self.queried.append(request_id)
        return {"request_id": "wrong" if self.wrong_identity else request_id,
                "state": self.state, "result": {"result": "provider completed"}}


@pytest.mark.parametrize("state", ["succeeded", "pending", "not_found"])
def test_provider_lookup_never_resubmits(stage, state):
    provider = Queryable(state)
    with pytest.raises(store.HtmlTaskError):
        stage.wrap(provider, "json")()
    store.mark_failed(stage.db, stage.job_id, "timeout", expected_attempt=1)
    count = reconcile_responses(stage.db, stage.job_id, stage.run, lookups={"json": provider.lookup})
    assert provider.queried == provider.sent and len(provider.sent) == 1
    if state == "succeeded":
        assert count == 1
        assert restart(stage).wrap(provider, "json")() == {"result": "provider completed"}
    else:
        assert count == 0
        with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
            restart(stage)


def test_provider_identity_mismatch_rejected(stage):
    provider = Queryable(wrong_identity=True)
    with pytest.raises(store.HtmlTaskError):
        stage.wrap(provider, "json")()
    store.mark_failed(stage.db, stage.job_id, "timeout", expected_attempt=1)
    with pytest.raises(store.HtmlTaskError, match="IDENTITY_MISMATCH"):
        reconcile_responses(stage.db, stage.job_id, stage.run, lookups={"json": provider.lookup})


def test_response_receipt_cannot_reconcile_cancelled_job(stage):
    stage.wrap(lambda **kw: {}, "json")()
    store.cancel_task(stage.db, stage.job_id)
    assert reconcile_responses(stage.db, stage.job_id, stage.run) == 0
    assert store._job(stage.db, stage.job_id).status == "cancelled"


def test_provider_lookup_budget_survives_recovery(stage):
    provider = Queryable("pending")
    with pytest.raises(store.HtmlTaskError):
        stage.wrap(provider, "json")()
    store.mark_failed(stage.db, stage.job_id, "timeout", expected_attempt=1)
    for _ in range(5):
        assert reconcile_responses(stage.db, stage.job_id, stage.run, lookups={"json": provider.lookup}) == 0
    assert len(provider.queried) == 3 and len(provider.sent) == 1


def test_native_toapis_id_persisted_before_poll_and_recovered_without_post(stage, monkeypatch):
    from functools import partial
    from types import SimpleNamespace
    from io import BytesIO
    from PIL import Image
    import ai_provider_service as transport
    import html_image_provider
    buf = BytesIO()
    Image.new("RGBA", (64, 64), (0, 0, 0, 255)).save(buf, format="PNG")
    calls = []
    ready = {"value": False}
    class Client:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, **kw):
            calls.append(("POST", url))
            return SimpleNamespace(status_code=200, json=lambda: {"id": "upstream-task-123"}, headers={})
        def get(self, url, **kw):
            calls.append(("GET", url))
            records = store._job(stage.db, stage.job_id).get_payload()["production_stages"]
            assert next(iter(records.values()))["upstream_task_id"] == "upstream-task-123"
            if not ready["value"]:
                raise ConnectionError("response lost after provider accepted")
            return SimpleNamespace(status_code=200, json=lambda: {"status": "completed", "result": {"data": [{"url": "https://example.test/result.png"}]}}, headers={})
    monkeypatch.setattr(transport.httpx, "Client", Client)
    monkeypatch.setattr(transport, "_governed_image_request", lambda base, operation, **kw: operation())
    monkeypatch.setattr(transport.time, "sleep", lambda *args: None)
    monkeypatch.setattr(transport, "extract_image_bytes_from_response", lambda response: buf.getvalue())
    binding = SimpleNamespace(require_ready=lambda: None, api_key="fixture", endpoint="https://example.test",
                              provider="toapis", model="gpt-image-2.5-flare-vip")
    generate = partial(html_image_provider.configured_image, model_binding=binding)
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        stage.wrap(generate, "image")("subject")
    store.mark_failed(stage.db, stage.job_id, "poll interrupted", expected_attempt=1)
    ready["value"] = True
    assert reconcile_responses(stage.db, stage.job_id, stage.run, lookups={
        "toapis": partial(html_image_provider.lookup_toapis_result, model_binding=binding),
    }) == 1
    assert restart(stage).wrap(generate, "image")("subject") == buf.getvalue()
    assert sum(method == "POST" for method, url in calls) == 1


@pytest.fixture
def author(tmp_path, monkeypatch, request):
    contract = copy.deepcopy(SEMANTIC_CONTRACT)
    plan = normalize(decomposition_plan(), contract)
    db = SessionLocal()
    project = Project(id="author-recovery-" + uuid.uuid4().hex, name="author recovery",
                      account_id="default", visual_backend="html", run_dir=str(tmp_path))
    db.add(project)
    db.commit()
    write(tmp_path / "planning/visual_contract.json", {"slides": [contract]})
    class Capture:
        def submit(self, *args):
            self.args = args
        def run(self):
            return self.args[0](*self.args[1:])
    executor = Capture()
    calls = []
    image = BytesIO()
    Image.new("RGB", (1280, 720), "white").save(image, format="PNG")
    jobs = HtmlWorkflowJobs(
        SessionLocal,
        HtmlReviewDependencies(ROOT, lambda **kw: calls.append(1) or copy.deepcopy(plan)),
        provider=lambda *_args, **_kwargs: image.getvalue(), executor=executor,
    )
    import html_production_service
    # This suite isolates write-ahead author receipt recovery. Scene quality
    # has its own real-render and engineering gates in the production tests.
    monkeypatch.setattr(html_production_service, "review_scene",
                        lambda *_args, **_kwargs: {"passed": True})
    task = jobs.submit(db, project, contract)
    executor.run()  # First job creates the design reference and stops for review.
    db.expire_all()
    design_task = store._job(db, task["id"])
    design_result = design_task.get_payload().get("result", {})
    assert design_result.get("stage") == "design_review"
    from html_design_candidates import current_design
    candidate = current_design(run_dir=tmp_path, contract=contract, repo_root=ROOT)["design"]
    task = jobs.submit(
        db, project, contract, options={"design_candidate_key": candidate["key"]},
        expected_model_summary=design_task.get_payload()["input"]["model_summary"],
    )
    def fail_terminal(*args, **kw):
        raise RuntimeError("author committed, task terminal commit failed")
    monkeypatch.setattr(store, "mark_succeeded", fail_terminal)
    if getattr(request, "param", "sealed") == "prepared":
        import html_production_recovery
        real_seal = html_production_recovery.seal_author_commit
        seal_calls = []
        def prepared_only(*args, **kw):
            seal_calls.append((args[2], kw.get("expected") is not None))
            if kw.get("expected") is not None:
                return real_seal(*args, **kw)
        monkeypatch.setattr(html_production_recovery, "seal_author_commit", prepared_only)
    else:
        seal_calls = []
    executor.run()  # The accepted design proceeds through author commit.
    db.expire_all()
    job = store._job(db, task["id"])
    assert job.status == "failed"
    seal = receipt_path(tmp_path, job.id, "author-1")
    assert seal.is_file(), (job.error, seal_calls,
                            [str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*.receipt.json")])
    yield db, project, jobs, contract, calls, task, seal
    db.close()


@pytest.mark.parametrize("author", ["prepared"], indirect=True)
def test_write_ahead_receipt_recovers_without_final_seal(author):
    db, project, jobs, contract, calls, task, seal = author
    assert read_receipt(seal)["state"] == "prepared"
    jobs.recover()
    assert store._job(db, task["id"]).status == "succeeded"
    assert len(calls) == 1


@pytest.mark.parametrize("mode", ["startup", "submit"])
def test_author_saved_task_recovers_without_regeneration(author, mode):
    db, project, jobs, contract, calls, task, seal = author
    from html_design_candidates import current_design

    candidate = current_design(run_dir=project.run_dir, contract=contract, repo_root=ROOT)["design"]
    task_input = store._job(db, task["id"]).get_payload()["input"]
    options = {"design_candidate_key": candidate["key"]}
    if mode == "startup":
        jobs.recover()
    else:
        recovered = jobs.submit(db, project, contract, options=options,
                                expected_model_summary=task_input["model_summary"])
        assert recovered["id"] == task["id"] and recovered["reconciled"]
    db.expire_all()
    job = store._job(db, task["id"])
    assert job.status == "succeeded" and job.error is None
    assert job.get_payload()["reconciliation"]["kind"] == "author_commit"
    receipt = read_receipt(seal)
    assert job.get_payload()["result"] == receipt["result"]
    assert len(calls) == 1
    assert jobs.submit(db, project, contract, options=options,
                       expected_model_summary=task_input["model_summary"])["id"] == task["id"]


@pytest.mark.parametrize("damage", ["binding", "revision", "receipt", "scene"])
def test_incomplete_or_newer_author_commit_never_claims_success(author, damage):
    db, project, jobs, contract, calls, task, seal = author
    root = Path(project.run_dir) / "planning/html_visual"
    from html_design_candidates import current_design

    candidate = current_design(run_dir=project.run_dir, contract=contract, repo_root=ROOT)["design"]
    task_input = store._job(db, task["id"]).get_payload()["input"]
    options = {"design_candidate_key": candidate["key"]}
    if damage == "binding":
        (root / f"binding-{contract['slide_id']}.json").unlink()
    elif damage == "revision":
        write(root / "revision.json", {"revision": 99})
    elif damage == "scene":
        (root / f"scene-{contract['slide_id']}.json").write_text("{}", encoding="utf-8")
    else:
        seal.write_text("{}", encoding="utf-8")
    jobs.recover()
    db.expire_all()
    assert store._job(db, task["id"]).status == "failed"
    with pytest.raises(store.HtmlTaskError, match="RECONCILIATION_BLOCKED"):
        jobs.submit(db, project, contract, options=options,
                    expected_model_summary=task_input["model_summary"])
    assert len(calls) == 1
