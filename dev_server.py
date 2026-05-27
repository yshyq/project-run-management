import json
import os
import sqlite3
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).parent
DB_PATH = ROOT / "dev.sqlite3"
TOKENS: dict[str, str] = {}


DEPARTMENT_PERMISSIONS = {
    "实施部": ["support:create", "project:login"],
    "客服部": ["support:create"],
    "运维部": ["support:create", "support:handle", "project:login", "project:server"],
    "运维负责人": ["support:create", "support:handle", "project:login", "project:server", "project:database", "approval:permission", "workflow:manage", "system:admin"],
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS departments (
              id TEXT PRIMARY KEY,
              name TEXT UNIQUE NOT NULL,
              wechat_department_id TEXT UNIQUE,
              default_permissions TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT UNIQUE NOT NULL,
              password TEXT NOT NULL,
              name TEXT NOT NULL,
              wechat_user_id TEXT UNIQUE,
              mobile TEXT,
              title TEXT,
              department_id TEXT,
              is_active INTEGER NOT NULL DEFAULT 1,
              is_superuser INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY,
              customer_name TEXT NOT NULL,
              remote_method TEXT,
              server_ip TEXT,
              server_account TEXT,
              server_password TEXT,
              login_url TEXT,
              login_account TEXT,
              login_password TEXT,
              database_url TEXT,
              database_account TEXT,
              database_password TEXT,
              other_info TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS permission_requests (
              id TEXT PRIMARY KEY,
              requester_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              permission_scope TEXT NOT NULL,
              reason TEXT NOT NULL,
              duration TEXT NOT NULL,
              status TEXT NOT NULL,
              approver_id TEXT,
              approved_permissions TEXT NOT NULL,
              created_at TEXT NOT NULL,
              decided_at TEXT
            );
            CREATE TABLE IF NOT EXISTS workflows (
              id TEXT PRIMARY KEY,
              name TEXT UNIQUE NOT NULL,
              description TEXT,
              is_default INTEGER NOT NULL DEFAULT 0,
              steps TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_supports (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              requester_id TEXT NOT NULL,
              workflow_id TEXT NOT NULL,
              support_type TEXT NOT NULL,
              priority TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              current_step TEXT NOT NULL,
              status TEXT NOT NULL,
              assignee_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        seed(db)


def new_id():
    return str(uuid.uuid4())


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def seed(db):
    for index, (name, permissions) in enumerate(DEPARTMENT_PERMISSIONS.items(), start=1):
        db.execute(
            "INSERT OR IGNORE INTO departments (id, name, wechat_department_id, default_permissions) VALUES (?, ?, ?, ?)",
            (new_id(), name, str(index), json.dumps(permissions, ensure_ascii=False)),
        )
    owner_dept = db.execute("SELECT id FROM departments WHERE name='运维负责人'").fetchone()["id"]
    db.execute(
        """
        INSERT OR IGNORE INTO users
        (id, username, password, name, wechat_user_id, mobile, title, department_id, is_active, is_superuser)
        VALUES (?, 'admin', 'admin123', '系统管理员', 'admin', '13800000000', '管理员', ?, 1, 1)
        """,
        (new_id(), owner_dept),
    )
    if not db.execute("SELECT 1 FROM projects LIMIT 1").fetchone():
        db.execute(
            """
            INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                "华东制造集团",
                "VPN + 堡垒机",
                "10.18.4.26",
                "ops_admin",
                "Svr@2026!",
                "https://mes.example.com/admin",
                "sys_admin",
                "Login@2026!",
                "10.18.4.32:3306/mes_prod",
                "mes_dba",
                "Db@2026!",
                "生产系统，服务更新需提前申请窗口。",
                now(),
            ),
        )
    default_steps = json.dumps(
        [
            {"key": "delivery_request", "name": "交付提需求"},
            {"key": "dev_build", "name": "研发开发"},
            {"key": "ops_release", "name": "运维发布"},
        ],
        ensure_ascii=False,
    )
    default_workflow = db.execute("SELECT id FROM workflows WHERE name='默认项目支持流程'").fetchone()
    if default_workflow:
        db.execute(
            "UPDATE workflows SET description=?, is_default=1, steps=? WHERE id=?",
            ("交付提需求 -- 研发开发 -- 运维发布。", default_steps, default_workflow["id"]),
        )
    else:
        db.execute(
            "INSERT INTO workflows VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), "默认项目支持流程", "交付提需求 -- 研发开发 -- 运维发布。", 1, default_steps, now()),
        )


def row_to_dict(row):
    data = dict(row)
    for key in ["default_permissions", "approved_permissions", "steps"]:
        if key in data and isinstance(data[key], str):
            data[key] = json.loads(data[key])
    for key in ["is_active", "is_superuser", "is_default"]:
        if key in data:
            data[key] = bool(data[key])
    return data


def user_with_department(db, row):
    data = row_to_dict(row)
    dept = db.execute("SELECT * FROM departments WHERE id=?", (data["department_id"],)).fetchone()
    data["department"] = row_to_dict(dept) if dept else None
    data.pop("password", None)
    return data


def current_user(handler, db):
    auth = handler.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    user_id = TOKENS.get(token)
    if not user_id:
        handler.send_json({"detail": "未登录"}, 401)
        return None
    row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        handler.send_json({"detail": "用户不存在"}, 401)
        return None
    return row


def permissions_for(user, db):
    if user["is_superuser"]:
        return {"system:admin", "approval:permission", "support:create", "support:handle", "workflow:manage", "project:login", "project:server", "project:database"}
    dept = db.execute("SELECT default_permissions FROM departments WHERE id=?", (user["department_id"],)).fetchone()
    return set(json.loads(dept["default_permissions"])) if dept else set()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        ctype = self.headers.get("Content-Type", "")
        from urllib.parse import parse_qs

        if "application/x-www-form-urlencoded" in ctype:
            return {key: values[0] for key, values in parse_qs(raw).items()}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {key: values[0] for key, values in parse_qs(raw).items()}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api"):
            self.serve_file(path)
            return
        with connect() as db:
            user = current_user(self, db) if path != "/api/health" else None
            if path != "/api/health" and user is None:
                return
            if path == "/api/health":
                self.send_json({"status": "ok"})
            elif path == "/api/auth/me":
                self.send_json(user_with_department(db, user))
            elif path == "/api/users/departments":
                self.send_json([row_to_dict(row) for row in db.execute("SELECT * FROM departments ORDER BY name")])
            elif path == "/api/users":
                self.send_json([user_with_department(db, row) for row in db.execute("SELECT * FROM users ORDER BY name")])
            elif path == "/api/projects":
                self.send_json([row_to_dict(row) for row in db.execute("SELECT * FROM projects ORDER BY created_at DESC")])
            elif path == "/api/permission-requests":
                self.send_json([row_to_dict(row) for row in db.execute("SELECT * FROM permission_requests ORDER BY created_at DESC")])
            elif path == "/api/workflows":
                self.send_json([row_to_dict(row) for row in db.execute("SELECT * FROM workflows ORDER BY created_at DESC")])
            elif path == "/api/project-supports":
                self.send_json([row_to_dict(row) for row in db.execute("SELECT * FROM project_supports ORDER BY created_at DESC")])
            else:
                self.send_json({"detail": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_json()
        with connect() as db:
            if path == "/api/auth/login":
                row = db.execute("SELECT * FROM users WHERE username=? AND password=?", (data.get("username"), data.get("password"))).fetchone()
                if not row:
                    self.send_json({"detail": "用户名或密码错误"}, 400)
                    return
                token = uuid.uuid4().hex
                TOKENS[token] = row["id"]
                self.send_json({"access_token": token, "token_type": "bearer"})
                return

            user = current_user(self, db)
            if user is None:
                return
            perms = permissions_for(user, db)

            if path == "/api/users":
                if "system:admin" not in perms:
                    self.send_json({"detail": "只有管理员可以新建用户"}, 403)
                    return
                if db.execute("SELECT 1 FROM users WHERE username=?", (data["username"],)).fetchone():
                    self.send_json({"detail": "用户名已存在"}, 400)
                    return
                user_id = new_id()
                db.execute(
                    """
                    INSERT INTO users
                    (id, username, password, name, wechat_user_id, mobile, title, department_id, is_active, is_superuser)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
                    """,
                    (
                        user_id,
                        data["username"],
                        data["password"],
                        data["name"],
                        data.get("wechat_user_id") or None,
                        data.get("mobile") or None,
                        data.get("title") or None,
                        data["department_id"],
                    ),
                )
                db.commit()
                self.send_json(user_with_department(db, db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()))
            elif path.startswith("/api/users/departments/"):
                if "system:admin" not in perms and "workflow:manage" not in perms:
                    self.send_json({"detail": "缺少部门权限配置权限"}, 403)
                    return
                department_id = path.split("/")[-1]
                db.execute(
                    "UPDATE departments SET default_permissions=? WHERE id=?",
                    (json.dumps(data.get("default_permissions", []), ensure_ascii=False), department_id),
                )
                db.commit()
                row = db.execute("SELECT * FROM departments WHERE id=?", (department_id,)).fetchone()
                self.send_json(row_to_dict(row))
            elif path == "/api/permission-requests":
                scope_map = {
                    "login": ["project:login"],
                    "server": ["project:server"],
                    "database": ["project:database"],
                    "all": ["project:login", "project:server", "project:database"],
                }
                request_id = new_id()
                db.execute(
                    "INSERT INTO permission_requests VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, ?, ?, NULL)",
                    (
                        request_id,
                        user["id"],
                        data["project_id"],
                        data["permission_scope"],
                        data["reason"],
                        "",
                        json.dumps(scope_map.get(data["permission_scope"], []), ensure_ascii=False),
                        now(),
                    ),
                )
                db.commit()
                self.send_json(row_to_dict(db.execute("SELECT * FROM permission_requests WHERE id=?", (request_id,)).fetchone()))
            elif path.endswith("/approve") or path.endswith("/reject"):
                if "approval:permission" not in perms:
                    self.send_json({"detail": "只有运维负责人可以审批权限"}, 403)
                    return
                request_id = path.split("/")[-2]
                status = "approved" if path.endswith("/approve") else "rejected"
                db.execute("UPDATE permission_requests SET status=?, approver_id=?, decided_at=? WHERE id=?", (status, user["id"], now(), request_id))
                db.commit()
                self.send_json(row_to_dict(db.execute("SELECT * FROM permission_requests WHERE id=?", (request_id,)).fetchone()))
            elif path == "/api/workflows":
                if "workflow:manage" not in perms:
                    self.send_json({"detail": "缺少流程配置权限"}, 403)
                    return
                workflow_id = new_id()
                if data.get("is_default"):
                    db.execute("UPDATE workflows SET is_default=0")
                db.execute(
                    "INSERT INTO workflows VALUES (?, ?, ?, ?, ?, ?)",
                    (workflow_id, data["name"], data.get("description"), int(bool(data.get("is_default"))), json.dumps(data["steps"], ensure_ascii=False), now()),
                )
                db.commit()
                self.send_json(row_to_dict(db.execute("SELECT * FROM workflows WHERE id=?", (workflow_id,)).fetchone()))
            elif path == "/api/project-supports":
                if "support:create" not in perms:
                    self.send_json({"detail": "缺少项目支持登记权限"}, 403)
                    return
                support_id = new_id()
                db.execute(
                    "INSERT INTO project_supports VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'delivery_request', 'open', ?, ?, ?)",
                    (
                        support_id,
                        data["project_id"],
                        data.get("requester_id") or user["id"],
                        data["workflow_id"],
                        data["support_type"],
                        data.get("priority", "普通"),
                        data["title"],
                        data["description"],
                        data.get("assignee_id") or None,
                        now(),
                        now(),
                    ),
                )
                db.commit()
                self.send_json(row_to_dict(db.execute("SELECT * FROM project_supports WHERE id=?", (support_id,)).fetchone()))
            elif path.endswith("/advance"):
                support_id = path.split("/")[-2]
                db.execute("UPDATE project_supports SET current_step=?, status=?, assignee_id=?, updated_at=? WHERE id=?", (data["next_step"], "in_progress", data.get("assignee_id"), now(), support_id))
                db.commit()
                self.send_json(row_to_dict(db.execute("SELECT * FROM project_supports WHERE id=?", (support_id,)).fetchone()))
            else:
                self.send_json({"detail": "Not found"}, 404)

    def serve_file(self, path):
        if path in {"", "/"}:
            path = "/index.html"
        file_path = (ROOT / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(ROOT.resolve())) or not file_path.exists():
            self.send_response(404)
            self.end_headers()
            return
        content_type = "text/html; charset=utf-8"
        if file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    init_db()
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"dev server running at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
