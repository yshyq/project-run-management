from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Department, User
from app.schemas import DepartmentOut, DepartmentUpdate, UserCreate, UserOut
from app.security import get_current_user, hash_password


router = APIRouter(prefix="/users", tags=["用户与部门"])


@router.get("", response_model=list[UserOut])
def list_users(_: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="只有管理员可以新增用户")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=payload.username,
        name=payload.name,
        password_hash=hash_password(payload.password),
        department_id=payload.department_id,
        mobile=payload.mobile,
        title=payload.title,
        is_superuser=payload.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(_: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.query(Department).order_by(Department.name.asc()).all()


@router.put("/departments/{department_id}", response_model=DepartmentOut)
def update_department_permissions(
    department_id: UUID,
    payload: DepartmentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="只有管理员可以配置部门默认权限")
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    department.default_permissions = payload.default_permissions
    db.commit()
    db.refresh(department)
    return department
