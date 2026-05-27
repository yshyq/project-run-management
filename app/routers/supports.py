from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProjectSupport, SupportActionLog, SupportStatus, User, Workflow
from app.schemas import ProjectSupportCreate, ProjectSupportOut, SupportAdvanceIn
from app.security import get_current_user, user_permissions


router = APIRouter(prefix="/project-supports", tags=["项目支持"])


@router.get("", response_model=list[ProjectSupportOut])
def list_project_supports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    query = db.query(ProjectSupport).order_by(ProjectSupport.created_at.desc())
    if "support:handle" not in user_permissions(current_user) and not current_user.is_superuser:
        query = query.filter(ProjectSupport.requester_id == current_user.id)
    return query.all()


@router.post("", response_model=ProjectSupportOut)
def create_project_support(
    payload: ProjectSupportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if "support:create" not in user_permissions(current_user) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="缺少项目支持登记权限")
    workflow = db.get(Workflow, payload.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="流程不存在")
    first_step = workflow.steps[0].get("key") if workflow.steps else "delivery"
    support = ProjectSupport(**payload.model_dump(), requester_id=current_user.id, current_step=first_step)
    db.add(support)
    db.flush()
    db.add(
        SupportActionLog(
            support_id=support.id,
            actor_id=current_user.id,
            action="create",
            from_step=None,
            to_step=support.current_step,
            comment="创建项目支持",
        )
    )
    db.commit()
    db.refresh(support)
    return support


@router.post("/{support_id}/advance", response_model=ProjectSupportOut)
def advance_project_support(
    support_id: UUID,
    payload: SupportAdvanceIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    support = db.get(ProjectSupport, support_id)
    if not support:
        raise HTTPException(status_code=404, detail="项目支持单不存在")
    if "support:handle" not in user_permissions(current_user) and support.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="缺少项目支持流转权限")

    allowed_steps = {step.get("key") for step in support.workflow.steps}
    if payload.next_step not in allowed_steps:
        raise HTTPException(status_code=400, detail="目标步骤不在当前流程配置中")

    from_step = support.current_step
    support.current_step = payload.next_step
    if payload.assignee_id:
        support.assignee_id = payload.assignee_id
    if payload.next_step in {"development", "handle", "processing"}:
        support.status = SupportStatus.in_progress
    elif payload.next_step in {"acceptance", "review"}:
        support.status = SupportStatus.acceptance
    elif payload.next_step in {"release", "done", "finish", "archive"}:
        support.status = SupportStatus.done

    db.add(
        SupportActionLog(
            support_id=support.id,
            actor_id=current_user.id,
            action="advance",
            from_step=from_step,
            to_step=payload.next_step,
            comment=payload.comment,
        )
    )
    db.commit()
    db.refresh(support)
    return support


@router.post("/{support_id}/close", response_model=ProjectSupportOut)
def close_project_support(
    support_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    support = db.get(ProjectSupport, support_id)
    if not support:
        raise HTTPException(status_code=404, detail="项目支持单不存在")
    if "support:handle" not in user_permissions(current_user) and support.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="缺少项目支持关闭权限")
    support.status = SupportStatus.closed
    db.add(
        SupportActionLog(
            support_id=support.id,
            actor_id=current_user.id,
            action="close",
            from_step=support.current_step,
            to_step="closed",
            comment="关闭项目支持",
        )
    )
    db.commit()
    db.refresh(support)
    return support
