from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    default_permissions: list[str]


class DepartmentUpdate(BaseModel):
    default_permissions: list[str]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    name: str
    mobile: str | None = None
    title: str | None = None
    is_active: bool
    is_superuser: bool
    department: DepartmentOut | None = None


class UserCreate(BaseModel):
    username: str
    name: str
    password: str
    department_id: UUID | None = None
    mobile: str | None = None
    title: str | None = None
    is_superuser: bool = False


class ProjectCreate(BaseModel):
    customer_name: str
    remote_method: str | None = None
    server_ip: str | None = None
    server_account: str | None = None
    server_password: str | None = None
    login_url: str | None = None
    login_account: str | None = None
    login_password: str | None = None
    database_url: str | None = None
    database_account: str | None = None
    database_password: str | None = None
    other_info: str | None = None


class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class PermissionRequestCreate(BaseModel):
    project_id: UUID
    permission_scope: str
    reason: str


class PermissionRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    project_id: UUID
    permission_scope: str
    reason: str
    status: str
    approver_id: UUID | None = None
    approved_permissions: list[str]
    created_at: datetime
    decided_at: datetime | None = None


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    is_default: bool = False
    steps: list[dict]


class WorkflowOut(WorkflowCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ProjectSupportCreate(BaseModel):
    project_id: UUID
    workflow_id: UUID
    support_type: str
    priority: str = "普通"
    title: str
    description: str
    assignee_id: UUID | None = None


class ProjectSupportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    requester_id: UUID
    workflow_id: UUID
    support_type: str
    priority: str
    title: str
    description: str
    current_step: str
    status: str
    assignee_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SupportAdvanceIn(BaseModel):
    next_step: str
    comment: str | None = None
    assignee_id: UUID | None = None
