# 项目运行管理系统

项目运行管理系统用于统一管理项目信息、权限申请、项目支持流程、用户部门和默认权限配置。

## 功能

- 登录认证：默认开发账号 `admin / admin123`
- 用户部门：支持手动新建用户，支持配置部门默认权限
- 项目信息：维护客户、远程方式、服务器、登录地址、账号密码、数据库和其他信息
- 项目关联记录：项目页集中展示该项目的权限需求和项目支持记录
- 权限申请：默认权限之外的信息需要申请，运维负责人审批后可访问
- 项目支持：支持申请人自动识别当前登录用户，支持处理人分配
- 流程配置：可配置项目支持流程，默认流程为“交付提需求 -> 研发开发 -> 运维发布”
- 后端骨架：FastAPI + SQLAlchemy + PostgreSQL 18
- 本地开发服务器：`dev_server.py` 可在无外部依赖时快速运行演示和测试

## 本地快速运行

```powershell
.\.venv\Scripts\python.exe dev_server.py
```

打开：

```text
http://127.0.0.1:8765
```

## 自动化测试

```powershell
.\.venv\Scripts\python.exe tests_e2e.py
```

测试覆盖：

- 登录
- 用户和部门
- 新建用户
- 部门权限配置
- 项目信息
- 权限申请与审批
- 项目支持创建与流转
- 流程配置
- 项目关联记录

## 正式后端

正式后端代码位于 `app/` 目录，目标技术栈：

- Python FastAPI
- SQLAlchemy 2
- PostgreSQL 18
- JWT 登录鉴权

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

准备 PostgreSQL：

```sql
CREATE USER project_support WITH PASSWORD 'project_support';
CREATE DATABASE project_support OWNER project_support;
```

启动正式后端：

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 注意

- `.env`、`.venv/`、`dev.sqlite3`、`__pycache__/` 不应提交到 GitHub。
- 当前 `dev_server.py` 使用本地 SQLite 作为开发演示，不代表正式生产部署方式。
