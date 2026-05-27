from app.models import PermissionRequest, RequestStatus, User
from app.security import user_permissions


SCOPE_TO_PERMISSIONS = {
    "login": ["project:login"],
    "server": ["project:server"],
    "database": ["project:database"],
    "all": ["project:login", "project:server", "project:database"],
}


def approved_project_permissions(user: User, project_id) -> set[str]:
    permissions = set()
    for request in user_permission_requests(user):
        if request.project_id == project_id and request.status == RequestStatus.approved:
            permissions.update(request.approved_permissions or [])
    return permissions


def user_permission_requests(user: User):
    return getattr(user, "permission_requests", [])


def scope_permissions(scope: str) -> list[str]:
    return SCOPE_TO_PERMISSIONS.get(scope, [])


def can_approve_permissions(user: User) -> bool:
    return "approval:permission" in user_permissions(user)
