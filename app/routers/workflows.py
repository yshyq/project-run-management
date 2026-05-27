from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Workflow
from app.schemas import WorkflowCreate, WorkflowOut
from app.security import get_current_user, user_permissions


router = APIRouter(prefix="/workflows", tags=["项目支持流程"])


@router.get("", response_model=list[WorkflowOut])
def list_workflows(_: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.query(Workflow).order_by(Workflow.created_at.desc()).all()


@router.post("", response_model=WorkflowOut)
def create_workflow(
    payload: WorkflowCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if "workflow:manage" not in user_permissions(current_user):
        raise HTTPException(status_code=403, detail="缺少流程配置权限")
    if payload.is_default:
        db.query(Workflow).update({Workflow.is_default: False})
    workflow = Workflow(**payload.model_dump())
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowOut)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if "workflow:manage" not in user_permissions(current_user):
        raise HTTPException(status_code=403, detail="缺少流程配置权限")
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="流程不存在")
    if payload.is_default:
        db.query(Workflow).filter(Workflow.id != workflow_id).update({Workflow.is_default: False})
    for key, value in payload.model_dump().items():
        setattr(workflow, key, value)
    db.commit()
    db.refresh(workflow)
    return workflow
