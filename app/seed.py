from sqlalchemy.orm import Session

from app.models import Department, Project, User, Workflow
from app.security import hash_password


DEFAULT_DEPARTMENT_PERMISSIONS = {
    "实施部": ["support:create", "project:login"],
    "客服部": ["support:create"],
    "运维部": ["support:create", "support:handle", "project:login", "project:server"],
    "研发部": ["support:create", "project:login"],
    "管理层": ["support:create", "project:login", "report:view"],
    "运维负责人": ["support:create", "support:handle", "project:login", "project:server", "project:database", "approval:permission", "workflow:manage"],
}


def ensure_seed_data(db: Session) -> None:
    departments = {}
    for name, permissions in DEFAULT_DEPARTMENT_PERMISSIONS.items():
        department = db.query(Department).filter(Department.name == name).first()
        if not department:
            department = Department(name=name, default_permissions=permissions)
            db.add(department)
            db.flush()
        departments[name] = department

    if not db.query(User).filter(User.username == "admin").first():
        db.add(
            User(
                username="admin",
                name="系统管理员",
                password_hash=hash_password("admin123"),
                department_id=departments["运维负责人"].id,
                is_superuser=True,
            )
        )

    if not db.query(Project).first():
        db.add(
            Project(
                customer_name="华东制造集团",
                remote_method="VPN + 堡垒机",
                server_ip="10.18.4.26",
                server_account="ops_admin",
                server_password="Svr@2026!",
                login_url="https://mes.example.com/admin",
                login_account="sys_admin",
                login_password="Login@2026!",
                database_url="10.18.4.32:3306/mes_prod",
                database_account="mes_dba",
                database_password="Db@2026!",
                other_info="生产系统，服务更新需提前申请窗口。",
            )
        )

    if not db.query(Workflow).filter(Workflow.name == "默认项目支持流程").first():
        db.add(
            Workflow(
                name="默认项目支持流程",
                description="项目支持可配置流程，可按业务调整步骤。",
                is_default=True,
                steps=[
                    {"key": "delivery", "name": "交付提需求", "role": "交付"},
                    {"key": "development", "name": "研发开发", "role": "研发"},
                    {"key": "release", "name": "运维发布", "role": "运维"},
                ],
            )
        )
    db.commit()
