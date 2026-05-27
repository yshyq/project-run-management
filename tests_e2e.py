import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


PORT = "8765"
BASE = f"http://127.0.0.1:{PORT}/api"


def request(method, path, token=None, data=None):
    body = None
    headers = {}
    if data is not None:
        if isinstance(data, str):
            body = data.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def assert_ok(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")
    print(f"PASS {name}")


def wait_for_server():
    for _ in range(50):
        try:
            status, _ = request("GET", "/health")
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("server did not start")


def main():
    env = {**os.environ, "PORT": PORT}
    proc = subprocess.Popen([sys.executable, "dev_server.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    try:
        wait_for_server()

        form = urllib.parse.urlencode({"username": "admin", "password": "admin123"})
        status, login = request("POST", "/auth/login", data=form)
        assert_ok("login", status == 200 and login.get("access_token"), login)
        token = login["access_token"]

        status, me = request("GET", "/auth/me", token)
        assert_ok("me", status == 200 and me["username"] == "admin", me)

        status, deps = request("GET", "/users/departments", token)
        assert_ok("departments", status == 200 and len(deps) >= 1, deps)

        status, users = request("GET", "/users", token)
        assert_ok("users", status == 200 and len(users) >= 2, users)

        status, created_user = request(
            "POST",
            "/users",
            token,
            {
                "username": f"tester{int(time.time())}",
                "password": "123456",
                "name": "自动化用户",
                "wechat_user_id": f"tester_wx_{int(time.time())}",
                "mobile": "13900000000",
                "title": "测试人员",
                "department_id": deps[0]["id"],
            },
        )
        assert_ok("user create", status == 200 and created_user["name"] == "自动化用户", created_user)

        status, updated_dept = request(
            "POST",
            f"/users/departments/{deps[0]['id']}",
            token,
            {"default_permissions": ["support:create", "project:login", "report:view"]},
        )
        assert_ok("department permissions update", status == 200 and "report:view" in updated_dept["default_permissions"], updated_dept)

        status, projects = request("GET", "/projects", token)
        assert_ok("projects", status == 200 and len(projects) >= 1, projects)

        status, workflows = request("GET", "/workflows", token)
        assert_ok("workflows list", status == 200 and len(workflows) >= 1, workflows)

        status, workflow = request(
            "POST",
            "/workflows",
            token,
            {
                "name": f"自动化流程-{int(time.time())}",
                "description": "自动化测试创建",
                "is_default": False,
                "steps": [{"key": "submit", "name": "提交"}, {"key": "done", "name": "完成"}],
            },
        )
        assert_ok("workflow create", status == 200 and workflow["name"].startswith("自动化流程"), workflow)

        status, perm = request(
            "POST",
            "/permission-requests",
            token,
            {"project_id": projects[0]["id"], "permission_scope": "database", "reason": "自动化测试"},
        )
        assert_ok("permission request create", status == 200 and perm["status"] == "pending", perm)

        status, approved = request("POST", f"/permission-requests/{perm['id']}/approve", token)
        assert_ok("permission approve", status == 200 and approved["status"] == "approved", approved)

        status, support = request(
            "POST",
            "/project-supports",
            token,
            {
                "project_id": projects[0]["id"],
                "workflow_id": workflows[0]["id"],
                "requester_id": me["id"],
                "assignee_id": created_user["id"],
                "support_type": "项目支持",
                "priority": "高",
                "title": "自动化测试项目支持",
                "description": "验证创建项目支持",
            },
        )
        assert_ok("project support create", status == 200 and support["requester_id"] == me["id"] and support["assignee_id"] == created_user["id"], support)

        status, advanced = request("POST", f"/project-supports/{support['id']}/advance", token, {"next_step": "dev_build", "comment": "研发开发"})
        assert_ok("project support advance", status == 200 and advanced["current_step"] == "dev_build", advanced)

        status, supports = request("GET", "/project-supports", token)
        assert_ok("project supports list", status == 200 and len(supports) >= 1, supports)

        status, requests = request("GET", "/permission-requests", token)
        project_has_related_records = any(item["project_id"] == projects[0]["id"] for item in requests + supports)
        assert_ok("project related records data", status == 200 and project_has_related_records, {"requests": requests, "supports": supports})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
