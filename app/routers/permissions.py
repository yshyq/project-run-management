from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PermissionRequest, RequestStatus, User, utc_now
from app.permissions import can_approve_permissions, scope_permissions
from app.schemas import PermissionRequestCreate, PermissionRequestOut
from app.security import get_current_user


router = APIRouter(prefix="/permission-requests", tags=["权限申请"])


@router.get("", response_model=list[PermissionRequestOut])
def list_permission_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    query = db.query(PermissionRequest).order_by(PermissionRequest.created_at.desc())
    if not can_approve_permissions(current_user) and not current_user.is_superuser:
        query = query.filter(PermissionRequest.requester_id == current_user.id)
    return query.all()


@router.post("", response_model=PermissionRequestOut)
def create_permission_request(
    payload: PermissionRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    permissions = scope_permissions(payload.permission_scope)
    if not permissions:
        raise HTTPException(status_code=400, detail="未知权限范围")
    request = PermissionRequest(
        requester_id=current_user.id,
        project_id=payload.project_id,
        permission_scope=payload.permission_scope,
        reason=payload.reason,
        approved_permissions=permissions,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.post("/{request_id}/approve", response_model=PermissionRequestOut)
def approve_permission_request(
    request_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not can_approve_permissions(current_user) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="只有运维负责人可以审批权限")
    request = db.get(PermissionRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="申请不存在")
    request.status = RequestStatus.approved
    request.approver_id = current_user.id
    request.decided_at = utc_now()
    db.commit()
    db.refresh(request)
    return request


@router.post("/{request_id}/reject", response_model=PermissionRequestOut)
def reject_permission_request(
    request_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not can_approve_permissions(current_user) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="只有运维负责人可以审批权限")
    request = db.get(PermissionRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="申请不存在")
    request.status = RequestStatus.rejected
    request.approver_id = current_user.id
    request.decided_at = utc_now()
    db.commit()
    db.refresh(request)
    return request
