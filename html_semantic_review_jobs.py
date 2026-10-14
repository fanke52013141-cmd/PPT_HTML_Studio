"""A04 uses the existing persistent LocalJob store and cooperative boundaries."""
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import threading
from account_context import account_scope,get_current_account_id
from artifact_fingerprint import sha256_json
from pipeline_lifecycle import project_artifact_lock
import html_task_store as store
import html_semantic_review_service as service


class SemanticReviewJobs:
    def __init__(self,session_factory,deps,*,executor=None,freeze_models=None,reviewer=None):
        from project_model_binding_service import freeze_project_models
        self.session_factory,self.deps=session_factory,deps
        self.executor=executor or ThreadPoolExecutor(max_workers=1,thread_name_prefix="html-semantic-qa")
        self.freeze=freeze_models or freeze_project_models
        self.reviewer=reviewer or service.review
        self.lock=threading.Lock()

    def submit(self,db,project,slide,request,expected_input=None):
        from html_visual_store import HtmlVisualConflict
        with project_artifact_lock(project.run_dir):
            inputs=service.source(project.run_dir,slide,self.deps.repo_root)
            if inputs["revision"]!=request.expected_revision:
                raise HtmlVisualConflict(request.expected_revision,inputs["revision"])
            model=self.freeze(project,required=("text",)).text
            identity={"input_digest":inputs["input_digest"],"model_summary":model.summary()}
            if expected_input is not None and any(expected_input.get(k)!=v for k,v in identity.items()):
                raise store.HtmlTaskError("语义原任务输入或模型已变化，不能作为原请求继续",409)
            key=sha256_json({"input_digest":inputs["input_digest"],"model":model.summary()})
            with self.lock:
                from database import LocalJob
                for job in db.query(LocalJob).filter(LocalJob.project_id==project.id,LocalJob.job_type=="html_semantic_review").all():
                    payload=job.get_payload()
                    if payload.get("submission_key")!=key or job.status in store.ACTIVE_STATUSES:
                        continue
                    changed=False
                    for name,record in payload.get("production_stages",{}).items():
                        if record.get("state") not in ("intent","unknown"):
                            continue
                        index=int(name.split(":")[1])
                        path=service.folder(project.run_dir,slide)/key/f"beat-{index}.json"
                        if path.is_file():
                            receipt=service.verify_seal(service.read(path))
                            if receipt.get("state")=="returned" and receipt.get("request_key")==record["request_key"]:
                                payload["production_stages"][name]={"state":"returned","request_key":record["request_key"]};changed=True
                    if changed:
                        job.payload_json=store.json_dumps(payload);db.commit()
                task=store.submit_task(db,project_id=project.id,task_type="html_semantic_review",submission_key=key,payload={**identity,"slide_id":slide,"source_revision":inputs["revision"],"account_id":get_current_account_id()})
                if not task["reused"] or task.get("retried"):
                    self.executor.submit(self.run,task["id"],project.run_dir,slide,inputs,model,get_current_account_id(),task["attempt"])
                return task

    def resume(self,db,project,job):
        from html_semantic_qa_models import SemanticSubmitRequest
        payload=job.get_payload()["input"]
        return self.submit(db,project,payload["slide_id"],SemanticSubmitRequest(expected_revision=payload["source_revision"]),expected_input=payload)

    def run(self,job_id,run,slide,inputs,model,account,attempt):
        db=self.session_factory()
        try:
            with account_scope(account):
                store.mark_running(db,job_id,expected_attempt=attempt)
                def checkpoint():
                    db.expire_all();job=store._job(db,job_id,attempt)
                    if job.status!="running":
                        raise store.HtmlTaskError("语义审阅任务已停止",409)
                def progress(value):
                    store.record_progress(db,job_id,value,expected_attempt=attempt)
                def receipt_event(index,value):
                    job=store._job(db,job_id,attempt)
                    payload=job.get_payload()
                    payload.setdefault("production_stages",{})[f"semantic:{index}"]=value
                    store._transition(db,job,("running",),{"payload_json":store.json_dumps(payload)})
                result=self.reviewer(run,slide,inputs,model.summary(),deps=self.deps,generator=partial(self.deps.json_generator,model_binding=model),checkpoint=checkpoint,progress=progress,receipt_event=receipt_event)
                checkpoint();store.mark_succeeded(db,job_id,result,expected_attempt=attempt)
        except Exception as error:
            # Never persist provider exception bodies or credentials.
            store.mark_failed(db,job_id,getattr(error,"code","SEMANTIC_REVIEW_FAILED"),expected_attempt=attempt)
        finally:
            db.close()


_jobs=None
_lock=threading.Lock()

def configured_jobs():
    global _jobs
    with _lock:
        if _jobs is None:
            from database import SessionLocal
            from html_visual_review_routes import _service_deps
            _jobs=SemanticReviewJobs(SessionLocal,_service_deps())
        return _jobs
