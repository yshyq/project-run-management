const API_BASE = "http://127.0.0.1:8765/api";

let token = localStorage.getItem("ps-token") || "";
let currentUser = null;
let departments = [];
let users = [];
let projects = [];
let requests = [];
let supports = [];
let workflows = [];

const views = {
  dashboard: document.querySelector("#dashboardView"),
  users: document.querySelector("#usersView"),
  projects: document.querySelector("#projectsView"),
  requests: document.querySelector("#requestsView"),
  supports: document.querySelector("#supportsView"),
  workflows: document.querySelector("#workflowsView")
};

const pageTitles = {
  dashboard: "总览",
  users: "用户部门",
  projects: "项目信息",
  requests: "权限申请",
  supports: "项目支持",
  workflows: "流程配置"
};

const permissionNames = {
  "system:admin": "系统管理",
  "support:create": "新建项目支持",
  "support:handle": "处理项目支持",
  "project:login": "查看登录信息",
  "project:server": "查看远程/服务器",
  "project:database": "查看数据库",
  "approval:permission": "审批权限",
  "workflow:manage": "配置流程",
  "report:view": "查看报表"
};

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof URLSearchParams) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(data.detail || "请求失败");
  }
  return response.json();
}

function collect(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function badge(text) {
  const label = permissionNames[text] || text || "-";
  return `<span class="badge">${label}</span>`;
}

function emptyState(text) {
  return `<div class="empty-state">${text}</div>`;
}

function userName(id) {
  return users.find((item) => item.id === id)?.name || "-";
}

function projectName(id) {
  return projects.find((item) => item.id === id)?.customer_name || "-";
}

function workflowName(id) {
  return workflows.find((item) => item.id === id)?.name || "-";
}

function switchView(name) {
  Object.entries(views).forEach(([key, element]) => element.classList.toggle("active", key === name));
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  document.querySelector("#pageTitle").textContent = pageTitles[name];
}

async function login(username, password) {
  localStorage.removeItem("ps-token");
  token = "";
  const body = new URLSearchParams({ username, password });
  const data = await api("/auth/login", { method: "POST", body });
  token = data.access_token;
  localStorage.setItem("ps-token", token);
  await boot();
}

async function boot() {
  if (!token) return;
  currentUser = await api("/auth/me");
  document.querySelector("#loginScreen").classList.add("hidden");
  document.querySelector("#appShell").classList.remove("hidden");
  await loadAll();
}

async function loadAll() {
  [departments, users, projects, requests, supports, workflows] = await Promise.all([
    api("/users/departments"),
    api("/users"),
    api("/projects"),
    api("/permission-requests"),
    api("/project-supports"),
    api("/workflows")
  ]);
  renderAll();
}

function renderAll() {
  document.querySelector("#currentUserMeta").innerHTML = `
    <strong>${currentUser.name}</strong>
    <div>${currentUser.department?.name || "未分配部门"} · ${currentUser.title || "-"}</div>
  `;
  document.querySelector("#userCount").textContent = users.length;
  document.querySelector("#departmentCount").textContent = departments.length;
  document.querySelector("#projectCount").textContent = projects.length;
  document.querySelector("#supportCount").textContent = supports.length;
  renderDepartments();
  renderUsers();
  renderProjects();
  renderRequests();
  renderSupports();
  renderWorkflows();
  fillSelects();
}

function renderDepartments() {
  document.querySelector("#departmentSummary").innerHTML = departments.map((item) => `
    <div class="compact-item">
      <strong>${item.name}</strong>
      <div class="muted">${(item.default_permissions || []).map(badge).join("")}</div>
    </div>
  `).join("") || emptyState("暂无部门");
}

function renderUsers() {
  document.querySelector("#userList").innerHTML = `
    <table>
      <thead><tr><th>姓名</th><th>用户名</th><th>企业微信</th><th>部门</th><th>职位</th><th>默认权限</th><th>状态</th></tr></thead>
      <tbody>
        ${users.map((item) => `
          <tr>
            <td>${item.name}<div class="muted">${item.mobile || "-"}</div></td>
            <td>${item.username}</td>
            <td>${item.wechat_user_id || "-"}</td>
            <td>${item.department?.name || "-"}</td>
            <td>${item.title || "-"}</td>
            <td>${(item.department?.default_permissions || []).map(badge).join("")}</td>
            <td>${item.is_active ? "启用" : "停用"}</td>
          </tr>
        `).join("") || `<tr><td colspan="7">${emptyState("暂无用户")}</td></tr>`}
      </tbody>
    </table>
  `;
}

function renderProjects() {
  document.querySelector("#projectList").innerHTML = projects.map((project) => {
    const projectRequests = requests.filter((item) => item.project_id === project.id);
    const projectSupports = supports.filter((item) => item.project_id === project.id);
    return `
      <section class="project-detail">
        <div class="panel-head">
          <h2>${project.customer_name}</h2>
          <span class="badge">${project.remote_method || "未配置远程方式"}</span>
        </div>
        <div class="project-sections">
          <section class="project-section">
            <h3>登录、远程、地址、账号密码</h3>
            <dl class="field-list">
              <div><dt>远程方式</dt><dd>${project.remote_method || "-"}</dd></div>
              <div><dt>服务器地址</dt><dd>${project.server_ip || "-"}</dd></div>
              <div><dt>服务器账号</dt><dd>${project.server_account || "-"}</dd></div>
              <div><dt>服务器密码</dt><dd>${project.server_password || "-"}</dd></div>
              <div><dt>登录地址</dt><dd>${project.login_url || "-"}</dd></div>
              <div><dt>登录账号</dt><dd>${project.login_account || "-"}</dd></div>
              <div><dt>登录密码</dt><dd>${project.login_password || "-"}</dd></div>
              <div><dt>数据库地址</dt><dd>${project.database_url || "-"}</dd></div>
              <div><dt>数据库账号</dt><dd>${project.database_account || "-"}</dd></div>
              <div><dt>数据库密码</dt><dd>${project.database_password || "-"}</dd></div>
              <div><dt>其他信息</dt><dd>${project.other_info || "-"}</dd></div>
            </dl>
          </section>
          <section class="project-section">
            <h3>此项目所有相关需求和支持记录</h3>
            <div class="record-group">
              <strong>权限需求</strong>
              ${projectRequests.map((item) => `
                <div class="record-item">
                  <span>${userName(item.requester_id)} · ${item.permission_scope}</span>
                  <span class="badge ${item.status}">${item.status}</span>
                  <div class="muted">${item.reason}</div>
                </div>
              `).join("") || emptyState("暂无权限需求")}
            </div>
            <div class="record-group">
              <strong>项目支持</strong>
              ${projectSupports.map((item) => `
                <div class="record-item">
                  <span>${item.title} · ${item.support_type}</span>
                  <span class="badge">${item.status}</span>
                  <div class="muted">${item.description}</div>
                </div>
              `).join("") || emptyState("暂无支持记录")}
            </div>
          </section>
        </div>
      </section>
    `;
  }).join("") || emptyState("暂无项目");
}

function renderRequests() {
  document.querySelector("#requestList").innerHTML = `
    <table>
      <thead><tr><th>申请人</th><th>项目</th><th>范围</th><th>原因</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        ${requests.map((item) => `
          <tr>
            <td>${userName(item.requester_id)}</td>
            <td>${projectName(item.project_id)}</td>
            <td>${item.permission_scope}</td>
            <td>${item.reason}</td>
            <td>${item.status}</td>
            <td>
              ${item.status === "pending" ? `
                <button class="request-action" data-approve="${item.id}">通过</button>
                <button class="request-action" data-reject="${item.id}">驳回</button>
              ` : "-"}
            </td>
          </tr>
        `).join("") || `<tr><td colspan="6">${emptyState("暂无权限申请")}</td></tr>`}
      </tbody>
    </table>
  `;
}

function renderSupports() {
  document.querySelector("#recentSupports").innerHTML = supports.slice(0, 5).map((item) => `
    <div class="timeline-item">
      <strong>${item.title}</strong>
      <div class="muted">${projectName(item.project_id)} · ${item.support_type} · ${item.status}</div>
    </div>
  `).join("") || emptyState("暂无项目支持");

  document.querySelector("#supportList").innerHTML = `
    <table>
      <thead><tr><th>标题</th><th>项目</th><th>类型</th><th>流程</th><th>步骤</th><th>状态</th><th>处理人</th></tr></thead>
      <tbody>
        ${supports.map((item) => `
          <tr>
            <td>${item.title}<div class="muted">${item.description}</div></td>
            <td>${projectName(item.project_id)}</td>
            <td>${item.support_type}</td>
            <td>${workflowName(item.workflow_id)}</td>
            <td>${item.current_step}</td>
            <td>${item.status}</td>
            <td>${item.assignee_id ? userName(item.assignee_id) : "-"}</td>
          </tr>
        `).join("") || `<tr><td colspan="7">${emptyState("暂无项目支持")}</td></tr>`}
      </tbody>
    </table>
  `;
}

function renderWorkflows() {
  document.querySelector("#workflowList").innerHTML = `
    <table>
      <thead><tr><th>名称</th><th>默认</th><th>步骤</th><th>说明</th></tr></thead>
      <tbody>
        ${workflows.map((item) => `
          <tr>
            <td>${item.name}</td>
            <td>${item.is_default ? "是" : "否"}</td>
            <td>${(item.steps || []).map((step) => badge(step.name || step.key)).join("")}</td>
            <td>${item.description || "-"}</td>
          </tr>
        `).join("") || `<tr><td colspan="4">${emptyState("暂无流程")}</td></tr>`}
      </tbody>
    </table>
  `;
}

function fillSelects() {
  const projectOptions = projects.map((item) => `<option value="${item.id}">${item.customer_name}</option>`).join("");
  const workflowOptions = workflows.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
  const departmentOptions = departments.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
  const userOptions = users.map((item) => `<option value="${item.id}">${item.name} / ${item.department?.name || "未分配"}</option>`).join("");
  const assigneeOptions = `<option value="">待分配</option>${userOptions}`;
  document.querySelector("#permissionProjectSelect").innerHTML = projectOptions;
  document.querySelector("#supportProjectSelect").innerHTML = projectOptions;
  document.querySelector("#supportWorkflowSelect").innerHTML = workflowOptions;
  document.querySelector("#supportRequesterSelect").innerHTML = userOptions;
  document.querySelector("#supportAssigneeSelect").innerHTML = assigneeOptions;
  if (currentUser) document.querySelector("#supportRequesterSelect").value = currentUser.id;
  document.querySelector("#userDepartmentSelect").innerHTML = departmentOptions;
  document.querySelector("#departmentConfigSelect").innerHTML = departmentOptions;
}

function openDialog(id) {
  document.querySelector(`#${id}`).showModal();
}

function closeDialog(id) {
  document.querySelector(`#${id}`).close();
}

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = collect(event.currentTarget);
  try {
    await login(data.username, data.password);
  } catch (error) {
    alert(`登录失败：${error.message}`);
  }
});

document.querySelector("#logoutBtn").addEventListener("click", () => {
  localStorage.removeItem("ps-token");
  location.reload();
});

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => closeDialog(button.dataset.close));
});

document.querySelector("#refreshBtn").addEventListener("click", loadAll);

document.querySelector("#newSupportBtn").addEventListener("click", () => openDialog("supportDialog"));
document.querySelector("#openPermissionDialogBtn").addEventListener("click", () => openDialog("permissionDialog"));
document.querySelector("#openWorkflowDialogBtn").addEventListener("click", () => openDialog("workflowDialog"));
document.querySelector("#openUserDialogBtn").addEventListener("click", () => openDialog("userDialog"));
document.querySelector("#openDepartmentDialogBtn").addEventListener("click", () => {
  const first = departments[0];
  if (first) {
    document.querySelector("#departmentConfigSelect").value = first.id;
    document.querySelector("#departmentPermissionsInput").value = (first.default_permissions || []).join(", ");
  }
  openDialog("departmentDialog");
});

document.querySelector("#departmentConfigSelect").addEventListener("change", (event) => {
  const dept = departments.find((item) => item.id === event.target.value);
  document.querySelector("#departmentPermissionsInput").value = (dept?.default_permissions || []).join(", ");
});

document.querySelector("#userForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/users", { method: "POST", body: JSON.stringify(collect(event.currentTarget)) });
    closeDialog("userDialog");
    event.currentTarget.reset();
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
});

document.querySelector("#departmentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = collect(event.currentTarget);
  const permissions = data.default_permissions.split(",").map((item) => item.trim()).filter(Boolean);
  try {
    await api(`/users/departments/${data.department_id}`, { method: "POST", body: JSON.stringify({ default_permissions: permissions }) });
    closeDialog("departmentDialog");
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
});

document.querySelector("#permissionForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/permission-requests", { method: "POST", body: JSON.stringify(collect(event.currentTarget)) });
    closeDialog("permissionDialog");
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
});

document.querySelector("#supportForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = collect(event.currentTarget);
    if (!data.assignee_id) delete data.assignee_id;
    await api("/project-supports", { method: "POST", body: JSON.stringify(data) });
    closeDialog("supportDialog");
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
});

document.querySelector("#workflowForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = collect(event.currentTarget);
  try {
    data.is_default = data.is_default === "true";
    data.steps = JSON.parse(data.steps);
    await api("/workflows", { method: "POST", body: JSON.stringify(data) });
    closeDialog("workflowDialog");
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
});

document.querySelector("#requestList").addEventListener("click", async (event) => {
  const approve = event.target.dataset.approve;
  const reject = event.target.dataset.reject;
  if (!approve && !reject) return;
  try {
    await api(`/permission-requests/${approve || reject}/${approve ? "approve" : "reject"}`, { method: "POST" });
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
});

boot().catch(() => {
  localStorage.removeItem("ps-token");
});
