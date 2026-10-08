"""Account-scoped web task control; no artifact writes on navigation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from account_context import get_current_account_id
from database import Project, get_db
import generation_control as control
from agent_contract.models import GenerationKind as TaskKind, GenerationStopRequest as StopRequest

router = APIRouter()
def _authorize(db: Session, project_id: str) -> None:
    if not db.query(Project).filter(Project.id == project_id, Project.account_id == get_current_account_id()).first():
        raise HTTPException(status_code=404, detail="项目不存在")


@router.get("/api/projects/{project_id}/generation-control/{kind}")
def get_generation_control(project_id: str, kind: TaskKind, db: Session = Depends(get_db)):
    _authorize(db, project_id)
    return {"success": True, **control.status(project_id, kind)}


@router.post("/api/projects/{project_id}/generation-control/{kind}/stop")
def stop_generation(project_id: str, kind: TaskKind, payload: StopRequest, db: Session = Depends(get_db)):
    _authorize(db, project_id)
    return {"success": True, **control.request_stop(project_id, kind, payload.operation_id)}
