(function () {
  const app = document.querySelector("#app");
  const APP_TITLE = "乐意纺织报工系统";
  const STORAGE_USER_KEY = "currentUser";
  const STORAGE_DATA_KEY = "demoAdminData";
  const PROCESS_PAGE_SIZE = 10;
  let currentProcessPage = 1;
  let processApiAvailable = false;

  const roleOptions = [
    { value: "super_admin", label: "超级权限" },
    { value: "admin", label: "管理员" },
    { value: "employee", label: "员工" },
  ];
  const processUnitOptions = ["元/米", "元/条", "元/个", "元/千针", "元/卷", "元/天", "元/上午", "元/下午", "元/小时", "元/套", "元/车", "元/大包", "元/小包", "元/包"];

  const defaultData = {
    accounts: [
      {
        id: "u-super",
        account: "admin",
        password: "admin123",
        role: "super_admin",
        name: "超级管理员",
        status: "active",
        managerId: null,
      },
      {
        id: "u-manager",
        account: "manager",
        password: "manager123",
        role: "admin",
        name: "车间管理员",
        status: "active",
        managerId: "u-super",
      },
      {
        id: "u-employee",
        account: "employee",
        password: "employee123",
        role: "employee",
        name: "张师傅",
        status: "active",
        managerId: "u-manager",
      },
    ],
    processes: [
      { id: "p-cut", name: "裁剪", price: 1.2, unit: "元/米", status: "active" },
      { id: "p-sew", name: "缝制", price: 2.6, unit: "元/条", status: "active" },
      { id: "p-pack", name: "包装", price: 0.8, unit: "元/包", status: "disabled" },
    ],
  };

  const routes = {
    "/": renderLogin,
    "/login": renderLogin,
    "/employee": renderEmployeeWorkReport,
    "/admin": renderAccountManagement,
    "/admin/accounts": renderAccountManagement,
    "/admin/processes": renderProcessManagement,
    "/admin/query": renderAdminQueryPlaceholder,
  };

  window.addEventListener("hashchange", renderRoute);
  renderRoute();

  function getPath() {
    return window.location.hash.replace(/^#/, "") || "/";
  }

  function navigate(path) {
    window.location.hash = path;
  }

  function renderRoute() {
    const path = getPath();
    const renderer = routes[path] || renderNotFound;
    renderer();
  }

  function readData() {
    const localData = readStorageData(localStorage);
    if (localData) return localData;

    const legacySessionData = readStorageData(sessionStorage);
    if (legacySessionData) {
      writeData(legacySessionData);
      return legacySessionData;
    }

    return clone(defaultData);
  }

  function readStorageData(storage) {
    try {
      const parsed = JSON.parse(storage.getItem(STORAGE_DATA_KEY));
      if (parsed && Array.isArray(parsed.accounts) && Array.isArray(parsed.processes)) {
        return parsed;
      }
    } catch (error) {
      return null;
    }

    return null;
  }

  function writeData(data) {
    localStorage.setItem(STORAGE_DATA_KEY, JSON.stringify(data));
  }

  function getApiBaseUrl() {
    const host = window.location.hostname || "127.0.0.1";
    return `${window.location.protocol || "http:"}//${host}:8000`;
  }

  async function apiRequest(path, options = {}) {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `请求失败：${response.status}`);
    }

    if (response.status === 204) return null;
    return response.json();
  }

  async function loadSharedProcesses(localData) {
    try {
      const remoteProcesses = await apiRequest("/api/admin/processes");
      processApiAvailable = true;
      localData.processes = remoteProcesses;
      writeData(localData);
      return localData;
    } catch (error) {
      processApiAvailable = false;
      return localData;
    }
  }

  async function createSharedProcess(process) {
    if (!processApiAvailable) return false;

    await apiRequest("/api/admin/processes", {
      method: "POST",
      body: JSON.stringify(process),
    });
    return true;
  }

  async function updateSharedProcess(processId, patch) {
    if (!processApiAvailable) return false;

    await apiRequest(`/api/admin/processes/${encodeURIComponent(processId)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    return true;
  }

  async function deleteSharedProcess(processId) {
    if (!processApiAvailable) return false;

    await apiRequest(`/api/admin/processes/${encodeURIComponent(processId)}`, {
      method: "DELETE",
    });
    return true;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function getCurrentUser() {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_USER_KEY));
    } catch (error) {
      return null;
    }
  }

  function setCurrentUser(user) {
    sessionStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
  }

  function clearCurrentUser() {
    sessionStorage.removeItem(STORAGE_USER_KEY);
  }

  function requireEmployee() {
    const user = getCurrentUser();
    if (!user || user.role !== "employee") {
      navigate("/login");
      return null;
    }
    return user;
  }

  function requireAdmin() {
    const user = getCurrentUser();
    if (!user || !["super_admin", "admin"].includes(user.role)) {
      navigate("/login");
      return null;
    }
    return user;
  }

  function isSuperAdmin(user) {
    return user.role === "super_admin";
  }

  function getRoleLabel(role) {
    return roleOptions.find((item) => item.value === role)?.label || role;
  }

  function getStatusLabel(status) {
    return status === "active" ? "启用中" : "已停用";
  }

  function getVisibleAccounts(data, user) {
    if (isSuperAdmin(user)) return data.accounts;
    return data.accounts.filter((account) => account.id === user.id || account.managerId === user.id);
  }

  function renderLogin() {
    clearCurrentUser();
    app.innerHTML = `
      <main class="app-page login-layout">
        ${renderAppHeader()}
        <section class="mobile-shell">
          <form class="panel login-panel form-stack" id="loginForm" novalidate>
            <div class="field">
              <label for="account">账号</label>
              <input class="input" id="account" name="account" autocomplete="username" placeholder="请输入账号" />
            </div>
            <div class="field">
              <label for="password">密码</label>
              <div class="password-control">
                <input class="input password-input" id="password" name="password" type="password" autocomplete="current-password" placeholder="请输入密码" />
                <button class="password-toggle" id="passwordToggle" type="button" aria-label="显示密码">${getEyeIcon(false)}</button>
              </div>
            </div>
            <p class="error-message" id="loginError">账号、密码不正确，或账号已停用。</p>
            <button class="button button-primary button-large" type="submit">登录</button>
          </form>
          <p class="hint">演示账号：admin / admin123，manager / manager123，employee / employee123</p>
        </section>
      </main>
    `;

    document.querySelector("#loginForm").addEventListener("submit", handleLogin);
    document.querySelector("#passwordToggle").addEventListener("click", togglePasswordVisibility);
  }

  function togglePasswordVisibility() {
    const passwordInput = document.querySelector("#password");
    const toggleButton = document.querySelector("#passwordToggle");
    const shouldShow = passwordInput.type === "password";

    passwordInput.type = shouldShow ? "text" : "password";
    toggleButton.innerHTML = getEyeIcon(shouldShow);
    toggleButton.setAttribute("aria-label", shouldShow ? "隐藏密码" : "显示密码");
  }

  function getEyeIcon(isVisible) {
    if (isVisible) {
      return `
        <svg class="icon-eye" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M2.2 2.2 21.8 21.8" />
          <path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c5.5 0 9.3 5 10 7a12.8 12.8 0 0 1-3.2 4.2" />
          <path d="M14.1 14.1A3 3 0 0 1 9.9 9.9" />
          <path d="M6.6 6.7A12.6 12.6 0 0 0 2 12c.7 2 4.5 7 10 7 1.4 0 2.7-.3 3.8-.8" />
        </svg>
      `;
    }

    return `
      <svg class="icon-eye" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M2 12s3.8-7 10-7 10 7 10 7-3.8 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    `;
  }

  function handleLogin(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const account = String(form.get("account") || "").trim();
    const password = String(form.get("password") || "");
    const data = readData();
    const matchedUser = data.accounts.find((item) => item.account === account);
    const error = document.querySelector("#loginError");

    if (!matchedUser || matchedUser.password !== password || matchedUser.status !== "active") {
      error.classList.add("is-visible");
      return;
    }

    const user = {
      id: matchedUser.id,
      account: matchedUser.account,
      name: matchedUser.name,
      role: matchedUser.role,
    };

    setCurrentUser(user);
    navigate(user.role === "employee" ? "/employee" : "/admin/accounts");
  }

  function renderEmployeeWorkReport() {
    const user = requireEmployee();
    if (!user) return;

    app.innerHTML = `
      <main class="app-page employee-layout">
        ${renderAppHeader()}
        <section class="employee-shell">
          <header class="employee-header">
            <h1 class="page-title">员工报工</h1>
            <p class="page-subtitle">${escapeHtml(user.name)}，当前为报工页面占位，后续接入工序、数量和工资汇总。</p>
          </header>
          <section class="employee-summary" aria-label="工资汇总">
            <div class="summary-item">
              <p class="summary-label">今日金额</p>
              <p class="summary-value">¥0.00</p>
            </div>
            <div class="summary-item">
              <p class="summary-label">当月汇总</p>
              <p class="summary-value">¥0.00</p>
            </div>
          </section>
          <section class="panel placeholder-card">
            <h2>报工表单占位</h2>
            <p>这里将放置日期、工序、数量和提交按钮。员工账号登录后只进入此页面，不能进入后台。</p>
          </section>
          <div class="action-row">
            <button class="button button-success button-large" type="button">提交报工</button>
            <button class="button button-secondary button-large" id="logoutButton" type="button">退出登录</button>
          </div>
        </section>
      </main>
    `;

    bindLogout();
  }

  function renderAccountManagement() {
    const user = requireAdmin();
    if (!user) return;

    const data = readData();
    const visibleAccounts = getVisibleAccounts(data, user);
    const creatableRoles = isSuperAdmin(user)
      ? roleOptions
      : roleOptions.filter((role) => ["admin", "employee"].includes(role.value));

    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-management-grid">
            <section class="admin-section">
              <div class="section-heading account-create-heading">
                <div>
                  <h2 class="account-create-title">增加账号</h2>
                </div>
              </div>
              <form class="admin-form account-create-form" id="accountForm" novalidate>
                <div class="field">
                  <input class="input" id="newAccountName" name="account" aria-label="账号名称" placeholder="账号名称" />
                </div>
                <div class="field">
                  <input class="input" id="newAccountPassword" name="password" type="text" aria-label="密码" placeholder="密码" />
                </div>
                <div class="field">
                  <select class="input select is-placeholder" id="newAccountRole" name="role" aria-label="权限">
                    <option value="" disabled selected>权限</option>
                    ${creatableRoles.map((role) => `<option value="${role.value}">${role.label}</option>`).join("")}
                  </select>
                </div>
                <button class="button button-primary button-medium" type="submit">新增账号</button>
                <p class="error-message" id="accountError"></p>
              </form>
            </section>
            <section class="admin-section">
              <div class="section-heading account-list-heading">
                <div>
                  <h2 class="account-list-title">账号列表</h2>
                </div>
              </div>
              <div class="table-wrap account-table-wrap">
                <table class="data-table account-table">
                  <thead>
                    <tr>
                      <th>账号</th>
                      <th>密码</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${visibleAccounts.map((account) => renderAccountRow(account, data, user)).join("")}
                  </tbody>
                </table>
              </div>
            </section>
          </section>
          ${renderAdminFooter("/admin/processes", "工序管理")}
        </section>
      </main>
    `;

    bindAdminNavigation();
    bindSelectPlaceholder("#newAccountRole");
    document.querySelector("#accountForm").addEventListener("submit", (event) => handleCreateAccount(event, user));
    document.querySelectorAll("[data-action='delete-account']").forEach((button) => {
      button.addEventListener("click", () => handleDeleteAccount(button.dataset.id));
    });
    document.querySelectorAll("[data-action='change-password']").forEach((button) => {
      button.addEventListener("click", () => handleChangeAccountPassword(button.dataset.id));
    });
    document.querySelectorAll("[data-action='change-account-name']").forEach((button) => {
      button.addEventListener("click", () => handleChangeAccountName(button.dataset.id));
    });
    document.querySelectorAll("[data-action='toggle-account-status']").forEach((button) => {
      button.addEventListener("click", () => handleToggleAccountStatus(button.dataset.id));
    });
  }

  function renderAccountRow(account, data, user) {
    const statusClass = account.status === "active" ? "button-success" : "button-danger";
    const deleteHtml = isSuperAdmin(user)
      ? `<button class="button button-danger button-small account-delete-button" data-action="delete-account" data-id="${account.id}" type="button" ${account.id === user.id ? "disabled" : ""}>删除</button>`
      : "";

    return `
      <tr>
        <td class="account-name-cell">
          <strong>${escapeHtml(account.account)}</strong>
          <button class="button button-primary button-small account-inline-button account-edit-button" data-action="change-account-name" data-id="${account.id}" type="button">修改</button>
        </td>
        <td class="account-password-cell">
          <span class="account-password">${escapeHtml(account.password)}</span>
          <button class="button button-primary button-small account-inline-button account-edit-button" data-action="change-password" data-id="${account.id}" type="button">修改</button>
        </td>
        <td class="account-status-cell">
          <button class="button ${statusClass} button-small account-status-button" data-action="toggle-account-status" data-id="${account.id}" type="button" ${account.id === user.id ? "disabled" : ""}>${account.status === "active" ? "启用" : "停用"}</button>
        </td>
        <td class="account-action-cell">
          ${deleteHtml}
        </td>
      </tr>
    `;
  }

  function handleCreateAccount(event, user) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const accountName = String(form.get("account") || "").trim();
    const password = String(form.get("password") || "").trim();
    const role = String(form.get("role") || "");
    const error = document.querySelector("#accountError");
    const data = readData();

    if (!accountName || !password) {
      showInlineError(error, "账号名称和密码都需要填写。");
      return;
    }

    if (!role) {
      showInlineError(error, "请选择账号权限。");
      return;
    }

    if (!isSuperAdmin(user) && !["admin", "employee"].includes(role)) {
      showInlineError(error, "管理员只能新增管理员和员工账号。");
      return;
    }

    if (data.accounts.some((item) => item.account === accountName)) {
      showInlineError(error, "账号名称已存在，请换一个。");
      return;
    }

    data.accounts.push({
      id: `u-${Date.now()}`,
      account: accountName,
      password,
      role,
      name: accountName,
      status: "active",
      managerId: !isSuperAdmin(user) ? user.id : null,
    });
    writeData(data);
    renderAccountManagement();
  }

  function handleDeleteAccount(accountId) {
    const user = getCurrentUser();
    if (!user || accountId === user.id) return;
    if (!window.confirm("确定删除这个账号吗？删除后账号列表中不再显示。")) return;

    const data = readData();
    data.accounts = data.accounts.filter((account) => account.id !== accountId);
    writeData(data);
    renderAccountManagement();
  }

  function handleChangeAccountPassword(accountId) {
    const data = readData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const password = window.prompt("请输入新的账号密码", account.password);
    if (!password || !password.trim()) return;

    account.password = password.trim();
    writeData(data);
    renderAccountManagement();
  }

  function handleChangeAccountName(accountId) {
    const data = readData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const accountName = window.prompt("请输入新的账号名称", account.account);
    if (!accountName || !accountName.trim()) return;

    const nextName = accountName.trim();
    if (data.accounts.some((item) => item.id !== accountId && item.account === nextName)) {
      window.alert("账号名称已存在，请换一个。");
      return;
    }

    account.account = nextName;
    account.name = nextName;
    writeData(data);
    renderAccountManagement();
  }

  function handleToggleAccountStatus(accountId) {
    const user = getCurrentUser();
    if (!user || accountId === user.id) return;

    const data = readData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const nextStatus = account.status === "active" ? "disabled" : "active";
    const actionText = nextStatus === "active" ? "启用" : "停用";
    if (!window.confirm(`确定${actionText}这个账号吗？`)) return;

    account.status = nextStatus;
    writeData(data);
    renderAccountManagement();
  }

  async function renderProcessManagement() {
    const user = requireAdmin();
    if (!user) return;

    let data = readData();
    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-management-grid">
            <section class="admin-section empty-section">
              <h2>工序列表加载中</h2>
            </section>
          </section>
          ${renderAdminFooter("/admin/accounts", "账号管理")}
        </section>
      </main>
    `;
    bindAdminNavigation();

    data = await loadSharedProcesses(data);
    const canDeleteProcess = isSuperAdmin(user);
    const totalProcessPages = Math.max(1, Math.ceil(data.processes.length / PROCESS_PAGE_SIZE));
    currentProcessPage = Math.min(currentProcessPage, totalProcessPages);
    const processPageStart = (currentProcessPage - 1) * PROCESS_PAGE_SIZE;
    const visibleProcesses = data.processes.slice(processPageStart, processPageStart + PROCESS_PAGE_SIZE);

    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-management-grid">
            <section class="admin-section">
              <div class="section-heading process-create-heading">
                <div>
                  <h2 class="process-create-title">新增工序</h2>
                </div>
              </div>
              <form class="admin-form process-form" id="processForm" novalidate>
                <div class="field">
                  <input class="input" id="processName" name="name" aria-label="工序名称" placeholder="工序名称" />
                </div>
                <div class="field">
                  <input class="input number-input" id="processPrice" name="price" type="number" min="0" step="0.01" aria-label="当前单价" placeholder="当前单价" />
                </div>
                <div class="field">
                  <select class="input select is-placeholder" id="processUnit" name="unit" aria-label="单位选择">
                    <option value="" disabled selected>单位选择</option>
                    ${processUnitOptions.map((unit) => `<option value="${unit}">${unit}</option>`).join("")}
                  </select>
                </div>
                <button class="button button-primary button-medium" type="submit">新增工序</button>
                <p class="error-message" id="processError"></p>
              </form>
            </section>
            <section class="admin-section">
              <div class="section-heading process-list-heading">
                <div>
                  <h2 class="process-list-title">工序列表</h2>
                </div>
              </div>
              <div class="table-wrap account-table-wrap">
                <table class="data-table account-table process-table ${canDeleteProcess ? "process-table-with-actions" : ""}">
                  <thead>
                    <tr>
                      <th>工序名称</th>
                      <th>当前单价</th>
                      <th>状态</th>
                      ${canDeleteProcess ? "<th>操作</th>" : ""}
                    </tr>
                  </thead>
                  <tbody>
                    ${visibleProcesses.map((process) => renderProcessRow(process, canDeleteProcess)).join("")}
                  </tbody>
                </table>
              </div>
              ${renderProcessPagination(totalProcessPages)}
            </section>
          </section>
          ${renderAdminFooter("/admin/accounts", "账号管理")}
        </section>
      </main>
    `;

    bindAdminNavigation();
    bindSelectPlaceholder("#processUnit");
    document.querySelector("#processForm").addEventListener("submit", handleCreateProcess);
    document.querySelectorAll("[data-action='rename-process']").forEach((button) => {
      button.addEventListener("click", () => handleRenameProcess(button.dataset.id));
    });
    document.querySelectorAll("[data-action='change-price']").forEach((button) => {
      button.addEventListener("click", () => handleChangeProcessPrice(button.dataset.id));
    });
    document.querySelectorAll("[data-action='toggle-process-status']").forEach((button) => {
      button.addEventListener("click", () => handleToggleProcessStatus(button.dataset.id));
    });
    document.querySelectorAll("[data-action='delete-process']").forEach((button) => {
      button.addEventListener("click", () => handleDeleteProcess(button.dataset.id));
    });
    document.querySelectorAll("[data-page]").forEach((button) => {
      button.addEventListener("click", () => {
        currentProcessPage = Number(button.dataset.page);
        renderProcessManagement();
      });
    });
  }

  function renderProcessPagination(totalPages) {
    if (totalPages <= 1) return "";

    return `
      <div class="process-pagination" aria-label="工序列表分页">
        ${
          currentProcessPage > 1
            ? `<button class="button button-primary button-small process-page-button" data-page="${currentProcessPage - 1}" type="button">上一页</button>`
            : ""
        }
        ${
          currentProcessPage < totalPages
            ? `<button class="button button-primary button-small process-page-button" data-page="${currentProcessPage + 1}" type="button">下一页</button>`
            : ""
        }
      </div>
    `;
  }

  function renderProcessRow(process, canDeleteProcess) {
    const statusClass = process.status === "active" ? "button-success" : "button-danger";
    const unitLabel = process.unit ? ` / ${escapeHtml(process.unit.replace(/^元\//, ""))}` : "";
    return `
      <tr>
        <td class="account-name-cell">
          <strong>${escapeHtml(process.name)}</strong>
          <button class="button button-primary button-small account-inline-button account-edit-button" data-action="rename-process" data-id="${process.id}" type="button">修改</button>
        </td>
        <td class="account-password-cell">
          <span class="account-password process-price">¥${Number(process.price).toFixed(2)}${unitLabel}</span>
          <button class="button button-primary button-small account-inline-button account-edit-button" data-action="change-price" data-id="${process.id}" type="button">修改</button>
        </td>
        <td class="account-status-cell">
          <button class="button ${statusClass} button-small account-status-button" data-action="toggle-process-status" data-id="${process.id}" type="button">${process.status === "active" ? "启用" : "停用"}</button>
        </td>
        ${
          canDeleteProcess
            ? `<td class="account-action-cell">
                <button class="button button-danger button-small account-delete-button" data-action="delete-process" data-id="${process.id}" type="button">删除</button>
              </td>`
            : ""
        }
      </tr>
    `;
  }

  async function handleCreateProcess(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "").trim();
    const price = Number(form.get("price"));
    const unit = String(form.get("unit") || "");
    const error = document.querySelector("#processError");
    const data = readData();

    if (!name || Number.isNaN(price) || price < 0 || !unit) {
      showInlineError(error, "请填写工序名称、正确的当前单价并选择单位。");
      return;
    }

    if (data.processes.some((item) => item.name === name)) {
      showInlineError(error, "工序名称已存在，请换一个。");
      return;
    }

    const process = {
      id: `p-${Date.now()}`,
      name,
      price,
      unit,
      status: "active",
    };

    try {
      if (!(await createSharedProcess({ name, price, unit }))) {
        data.processes.push(process);
        writeData(data);
      }
      renderProcessManagement();
    } catch (saveError) {
      showInlineError(error, "工序名称已存在，或后端保存失败。");
    }
  }

  async function handleRenameProcess(processId) {
    const data = readData();
    const process = data.processes.find((item) => item.id === processId);
    if (!process) return;

    const name = window.prompt("请输入新的工序名称", process.name);
    if (!name || !name.trim()) return;

    const nextName = name.trim();

    try {
      if (!(await updateSharedProcess(processId, { name: nextName }))) {
        process.name = nextName;
        writeData(data);
      }
      renderProcessManagement();
    } catch (error) {
      window.alert("工序名称已存在，或后端保存失败。");
    }
  }

  async function handleChangeProcessPrice(processId) {
    const data = readData();
    const process = data.processes.find((item) => item.id === processId);
    if (!process) return;

    const value = window.prompt("请输入新的当前单价", String(process.price));
    if (value === null) return;

    const price = Number(value);
    if (Number.isNaN(price) || price < 0) {
      window.alert("请输入正确的单价。");
      return;
    }

    try {
      if (!(await updateSharedProcess(processId, { price }))) {
        process.price = price;
        writeData(data);
      }
      renderProcessManagement();
    } catch (error) {
      window.alert("后端保存失败，请稍后再试。");
    }
  }

  async function handleToggleProcessStatus(processId) {
    const data = readData();
    const process = data.processes.find((item) => item.id === processId);
    if (!process) return;

    const nextStatus = process.status === "active" ? "disabled" : "active";
    const actionText = nextStatus === "active" ? "启用" : "停用";
    if (!window.confirm(`确定${actionText}这个工序吗？`)) return;

    try {
      if (!(await updateSharedProcess(processId, { status: nextStatus }))) {
        process.status = nextStatus;
        writeData(data);
      }
      renderProcessManagement();
    } catch (error) {
      window.alert("后端保存失败，请稍后再试。");
    }
  }

  async function handleDeleteProcess(processId) {
    const user = getCurrentUser();
    if (!user || !isSuperAdmin(user)) return;
    if (!window.confirm("确定删除这个工序吗？删除后工序列表中不再显示。")) return;

    const data = readData();

    try {
      if (!(await deleteSharedProcess(processId))) {
        data.processes = data.processes.filter((process) => process.id !== processId);
        writeData(data);
      }
      renderProcessManagement();
    } catch (error) {
      window.alert("后端删除失败，请稍后再试。");
    }
  }

  function renderAdminQueryPlaceholder() {
    const user = requireAdmin();
    if (!user) return;

    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main">
            <section class="admin-section empty-section">
              <h2>数据查询页面待开发</h2>
              <p class="page-subtitle">账号管理页已提供跳转入口，下一步可接入按员工、日期、月份和工序查询。</p>
            </section>
          </section>
          ${renderAdminFooter("/admin/processes", "工序管理")}
        </section>
      </main>
    `;

    bindAdminNavigation();
  }

  function renderAdminFooter(secondaryPath, secondaryLabel) {
    return `
      <footer class="admin-footer">
        <nav class="admin-tabs" aria-label="后台导航">
          <button class="button button-primary button-small admin-nav-button" data-nav="/admin/query" type="button">数据查询</button>
          <button class="button button-primary button-small admin-nav-button" data-nav="${secondaryPath}" type="button">${secondaryLabel}</button>
          <button class="button button-success button-small admin-nav-button" id="logoutButton" type="button">退出</button>
        </nav>
      </footer>
    `;
  }

  function renderAppHeader() {
    return `
      <header class="app-header">
        <h1 class="app-title">${APP_TITLE}</h1>
      </header>
    `;
  }

  function bindAdminNavigation() {
    document.querySelectorAll("[data-nav]").forEach((button) => {
      button.addEventListener("click", () => navigate(button.dataset.nav));
    });
    bindLogout();
  }

  function bindSelectPlaceholder(selector) {
    const select = document.querySelector(selector);
    if (!select) return;

    const update = () => {
      select.classList.toggle("is-placeholder", !select.value);
    };

    select.addEventListener("change", update);
    update();
  }

  function bindLogout() {
    const logoutButton = document.querySelector("#logoutButton");
    if (!logoutButton) return;
    logoutButton.addEventListener("click", () => {
      clearCurrentUser();
      navigate("/login");
    });
  }

  function showInlineError(element, message) {
    element.textContent = message;
    element.classList.add("is-visible");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderNotFound() {
    app.innerHTML = `
      <main class="app-page login-layout">
        ${renderAppHeader()}
        <section class="mobile-shell panel placeholder-card">
          <h1 class="page-title">页面不存在</h1>
          <p class="page-subtitle">请返回登录页重新进入系统。</p>
          <div class="action-row">
            <button class="button button-primary button-large" id="backLogin" type="button">返回登录</button>
          </div>
        </section>
      </main>
    `;

    document.querySelector("#backLogin").addEventListener("click", () => navigate("/login"));
  }
})();
