(function () {
  const app = document.querySelector("#app");
  const APP_TITLE = "乐意纺织报工系统";
  const PROCESS_PAGE_SIZE = 10;
  let accountApiAvailable = false;
  let latestAdminData = null;
  let currentProcessPage = 1;
  let processApiAvailable = false;
  let currentUser = null;
  let authReady = false;

  const roleOptions = [
    { value: "super_admin", label: "超级权限" },
    { value: "admin", label: "管理员" },
    { value: "employee", label: "员工" },
  ];
  const processUnitOptions = ["元/米", "元/条", "元/个", "元/千针", "元/卷", "元/天", "元/上午", "元/下午", "元/小时", "元/套", "元/车", "元/大包", "元/小包", "元/包"];

  const defaultData = {
    accounts: [],
    processes: [],
  };

  const routes = {
    "/": renderLogin,
    "/login": renderLogin,
    "/employee": renderEmployeeWorkReport,
    "/employee/query": renderEmployeeHistoryQuery,
    "/admin": renderAccountManagement,
    "/admin/accounts": renderAccountManagement,
    "/admin/processes": renderProcessManagement,
    "/admin/query": renderAdminQuery,
  };

  window.addEventListener("hashchange", renderRoute);
  initializeApp();

  async function initializeApp() {
    if (!["/", "/login"].includes(getPath())) {
      await refreshCurrentUser();
    }
    authReady = true;
    renderRoute();
  }

  function getPath() {
    return window.location.hash.replace(/^#/, "") || "/";
  }

  function navigate(path) {
    window.location.hash = path;
  }

  function renderRoute() {
    if (!authReady) {
      app.innerHTML = `
        <main class="app-page login-layout">
          ${renderAppHeader()}
          <section class="mobile-shell panel placeholder-card">
            <h1 class="page-title">加载中</h1>
          </section>
        </main>
      `;
      return;
    }
    const path = getPath();
    const renderer = routes[path] || renderNotFound;
    renderer();
  }

  function readData() {
    return clone(defaultData);
  }

  function getLatestAdminData() {
    return latestAdminData || readData();
  }

  function getApiBaseUrl() {
    const host = window.location.hostname || "127.0.0.1";
    return `${window.location.protocol || "http:"}//${host}:8000`;
  }

  async function apiRequest(path, options = {}) {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      credentials: "include",
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

  async function downloadFileRequest(path) {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      credentials: "include",
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `请求失败：${response.status}`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i);
    const filename = decodeURIComponent(filenameMatch?.[1] || filenameMatch?.[2] || "员工月度报工详情.docx");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function exportEmployeeMonthlyWord(month) {
    await downloadFileRequest(`/api/employee/work-reports/monthly-export?month=${encodeURIComponent(month)}`);
  }

  async function exportAdminMonthlyWord(accountId, month) {
    await downloadFileRequest(
      `/api/admin/work-reports/monthly-export?account_id=${encodeURIComponent(accountId)}&month=${encodeURIComponent(month)}`
    );
  }

  async function loadSharedProcesses(localData) {
    try {
      const remoteProcesses = await apiRequest("/api/admin/processes");
      processApiAvailable = true;
      localData.processes = remoteProcesses;
      return localData;
    } catch (error) {
      processApiAvailable = false;
      return localData;
    }
  }

  async function loadSharedAccounts(localData) {
    try {
      const remoteAccounts = await apiRequest("/api/admin/accounts");
      accountApiAvailable = true;
      localData.accounts = remoteAccounts;
      return localData;
    } catch (error) {
      accountApiAvailable = false;
      return localData;
    }
  }

  async function loginSharedAccount(account, password) {
    const user = await apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ account, password }),
    });
    accountApiAvailable = true;
    return user;
  }

  async function createSharedAccount(account) {
    await apiRequest("/api/admin/accounts", {
      method: "POST",
      body: JSON.stringify(account),
    });
    return true;
  }

  async function updateSharedAccount(accountId, patch) {
    await apiRequest(`/api/admin/accounts/${encodeURIComponent(accountId)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    return true;
  }

  async function deleteSharedAccount(accountId) {
    await apiRequest(`/api/admin/accounts/${encodeURIComponent(accountId)}`, {
      method: "DELETE",
    });
    return true;
  }

  async function createSharedProcess(process) {
    await apiRequest("/api/admin/processes", {
      method: "POST",
      body: JSON.stringify(process),
    });
    return true;
  }

  async function updateSharedProcess(processId, patch) {
    await apiRequest(`/api/admin/processes/${encodeURIComponent(processId)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    return true;
  }

  async function deleteSharedProcess(processId) {
    await apiRequest(`/api/admin/processes/${encodeURIComponent(processId)}`, {
      method: "DELETE",
    });
    return true;
  }

  async function loadEmployeeProcesses(accountId) {
    return apiRequest(`/api/accounts/${encodeURIComponent(accountId)}/processes`);
  }

  async function loadWorkReport(accountId, workDate) {
    return apiRequest(`/api/work-reports/${encodeURIComponent(accountId)}/${encodeURIComponent(workDate)}`);
  }

  async function saveWorkReport(accountId, workDate, rows) {
    return apiRequest(`/api/work-reports/${encodeURIComponent(accountId)}`, {
      method: "PUT",
      body: JSON.stringify({ work_date: workDate, rows }),
    });
  }

  async function loadWorkReportHistory(accountId) {
    return apiRequest(`/api/work-report-history/${encodeURIComponent(accountId)}`);
  }

  async function queryWorkReports(params = {}) {
    const query = new URLSearchParams();
    if (params.accountId) query.set("account_id", params.accountId);
    if (params.month) query.set("month", params.month);
    if (params.startDate) query.set("start_date", params.startDate);
    if (params.endDate) query.set("end_date", params.endDate);
    if (params.processId) query.set("process_id", params.processId);
    if (params.page) query.set("page", String(params.page));
    if (params.pageSize) query.set("page_size", String(params.pageSize));
    const suffix = query.toString();
    return apiRequest(`/api/work-reports/query${suffix ? `?${suffix}` : ""}`);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function getCurrentUser() {
    return currentUser;
  }

  function setCurrentUser(user) {
    currentUser = user;
  }

  function clearCurrentUser() {
    currentUser = null;
  }

  async function refreshCurrentUser() {
    try {
      currentUser = await apiRequest("/api/me");
    } catch (error) {
      currentUser = null;
    }
  }

  async function logoutCurrentUser() {
    try {
      await apiRequest("/api/auth/logout", { method: "POST" });
    } catch (error) {
      // 即使服务端已经没有登录态，也清理前端内存状态并回到登录页。
    }
    clearCurrentUser();
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
          <p class="hint">请输入已创建的账号和密码登录</p>
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

  async function handleLogin(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const account = String(form.get("account") || "").trim();
    const password = String(form.get("password") || "");
    const error = document.querySelector("#loginError");

    try {
      const user = await loginSharedAccount(account, password);
      setCurrentUser(user);
      navigate(user.role === "employee" ? "/employee" : "/admin/accounts");
    } catch (loginError) {
      error.classList.add("is-visible");
    }
  }

  async function renderEmployeeWorkReport(selectedDate) {
    const user = requireEmployee();
    if (!user) return;

    app.innerHTML = `
      <main class="app-page employee-layout">
        ${renderAppHeader()}
        <section class="employee-shell">
          <section class="panel placeholder-card">
            <h2>报工表加载中</h2>
          </section>
        </section>
      </main>
    `;

    const today = getLocalDateString(new Date());
    const workDate = selectedDate && selectedDate <= today ? selectedDate : today;
    let processes = [];
    let report = { rows: [] };
    let history = { rows: [] };
    let monthSummary = { summary: { totalWage: 0 } };

    try {
      processes = await loadEmployeeProcesses(user.id);
      report = await loadWorkReport(user.id, workDate);
      history = await loadWorkReportHistory(user.id);
      monthSummary = await queryWorkReports({
        accountId: user.id,
        month: workDate.slice(0, 7),
        page: 1,
        pageSize: 1,
      });
    } catch (error) {
      window.alert("报工数据加载失败，请确认后端服务已启动。");
    }

    const hasSavedReport = Boolean(report.rows && report.rows.length);
    const rows = normalizeReportRows(report.rows || []);
    const dailyWage = calculateDailyWage(rows);
    const savedDailyWage = Number(report.dailyWage) || (report.rows || []).reduce((sum, row) => sum + (Number(row.totalPrice) || 0), 0);
    const monthTotalWage = Number(monthSummary?.summary?.totalWage) || 0;
    const monthlyWageBase = Math.max(0, monthTotalWage - savedDailyWage);
    const monthlyWage = monthlyWageBase + dailyWage;

    app.innerHTML = `
      <main class="app-page employee-layout">
        ${renderAppHeader()}
        <section class="employee-shell">
          <section class="panel report-panel">
            <div class="report-date-row">
              <label for="workDate">日期</label>
              <input class="input report-date-input" id="workDate" type="date" value="${workDate}" max="${today}" />
            </div>
            ${hasSavedReport ? `<p class="report-lock-note">该日期已报工，记录不能再次提交或修改。</p>` : ""}
            <div class="report-table-wrap">
              <table class="report-table">
                <thead>
                  <tr>
                    <th>工序</th>
                    <th>单价</th>
                    <th>数量</th>
                    <th>总价</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody id="reportRows">
                  ${rows.map((row, index) => renderReportRow(row, index, processes, hasSavedReport)).join("")}
                </tbody>
                <tfoot>
                  <tr>
                    <td>当日工资</td>
                    <td colspan="4" id="dailyWage">¥${dailyWage.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>当月工资</td>
                    <td colspan="4" id="monthlyWage">¥${monthlyWage.toFixed(2)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </section>
          <div class="action-row">
            <button class="button button-success button-large" id="saveReportButton" type="button" ${hasSavedReport ? "disabled" : ""}>${hasSavedReport ? "已报工" : "提交报工"}</button>
            <button class="button button-primary button-large" id="employeeQueryButton" type="button">数据查询</button>
          </div>
          <div class="employee-logout-row">
            <button class="button button-secondary button-large" id="logoutButton" type="button">退出登录</button>
          </div>
        </section>
      </main>
    `;

    bindLogout();
    document.querySelector("#employeeQueryButton").addEventListener("click", () => navigate("/employee/query"));
    bindReportTable(processes, user.id, monthlyWageBase, hasSavedReport, history.rows || [], workDate);
  }

  async function renderEmployeeHistoryQuery() {
    const user = requireEmployee();
    if (!user) return;

    app.innerHTML = `
      <main class="app-page employee-layout">
        ${renderAppHeader()}
        <section class="employee-shell">
          <section class="panel placeholder-card">
            <h2>数据加载中</h2>
          </section>
        </section>
      </main>
    `;

    let initialPage = { rows: [], total: 0, summary: { totalWage: 0, totalQuantity: 0, workDays: 0 } };
    let processes = [];
    try {
      processes = await loadEmployeeProcesses(user.id);
      initialPage = await queryWorkReports({ accountId: user.id, page: 1, pageSize: 15 });
    } catch (error) {
      window.alert("历史数据加载失败，请确认后端服务已启动。");
    }

    const initialRows = normalizeHistoryRows(initialPage.rows || [], processes);
    const today = getLocalDateString(new Date());
    const currentMonth = today.slice(0, 7);

    app.innerHTML = `
      <main class="app-page employee-layout">
        ${renderAppHeader()}
        <section class="employee-shell">
          <section class="panel history-panel employee-query-panel">
            <div class="history-summary">
              <span class="history-account-name">${escapeHtml(user.name)}</span>
            </div>
            <div class="employee-query-actions">
              <form class="employee-query-form" id="monthSearchForm" novalidate>
                <label for="historyStartMonth">按月份查询</label>
                <div class="date-query-control month-query-control">
                  <span class="date-query-prefix">起</span>
                  <span class="date-query-value" data-date-display="historyStartMonth"></span>
                  <input class="input employee-query-input date-query-input" id="historyStartMonth" name="historyStartMonth" type="month" value="${currentMonth}" />
                </div>
                <div class="date-query-control month-query-control">
                  <span class="date-query-prefix">止</span>
                  <span class="date-query-value" data-date-display="historyEndMonth"></span>
                  <input class="input employee-query-input date-query-input" id="historyEndMonth" name="historyEndMonth" type="month" value="${currentMonth}" />
                </div>
                <button class="button button-primary button-medium employee-query-button" type="submit">搜索</button>
                <button class="button button-secondary button-medium employee-query-button month-export-button" id="exportMonthWordButton" type="button">导出本月 Word</button>
              </form>
              <form class="employee-query-form process-query-form" id="processSearchForm" novalidate>
                <label for="historyProcess">按工序查询</label>
                <select class="input employee-query-input select is-placeholder" id="historyProcess" name="historyProcess">
                  <option value="" disabled selected>工序</option>
                  ${processes.map((process) => `<option value="${escapeHtml(process.id)}">${escapeHtml(process.name)}</option>`).join("")}
                </select>
                <div class="date-query-control process-start-date-control">
                  <span class="date-query-prefix">起</span>
                  <span class="date-query-value" data-date-display="processStartDate"></span>
                  <input class="input employee-query-input date-query-input" id="processStartDate" name="processStartDate" type="date" value="${currentMonth}-01" />
                </div>
                <div class="date-query-control process-end-date-control">
                  <span class="date-query-prefix">止</span>
                  <span class="date-query-value" data-date-display="processEndDate"></span>
                  <input class="input employee-query-input date-query-input" id="processEndDate" name="processEndDate" type="date" value="${today}" />
                </div>
                <button class="button button-success button-medium employee-query-button" type="submit">搜索</button>
              </form>
            </div>
            <div id="historyResult">
              ${renderDefaultDailyDetailResult(initialRows, 1, initialPage.total || initialRows.length)}
            </div>
          </section>
          <div class="action-row">
            <button class="button button-primary button-large" id="backReportButton" type="button">返回报工</button>
          </div>
          <div class="employee-logout-row">
            <button class="button button-secondary button-large" id="logoutButton" type="button">退出登录</button>
          </div>
        </section>
      </main>
    `;

    document.querySelector("#backReportButton").addEventListener("click", () => navigate("/employee"));
    bindSelectPlaceholder("#historyProcess");
    bindDateDisplayControls();
    bindEmployeeHistoryQuery(user, processes, today, initialPage.total || initialRows.length);
    bindLogout();
  }

  function normalizeHistoryRows(rows, processes) {
    return rows.map((row) => {
      const process = processes.find((item) => item.id === row.processId || item.name === row.processName);
      return {
        workDate: row.workDate || row.work_date || "",
        processId: row.processId || row.process_id || process?.id || "",
        processName: row.processName || row.process_name || process?.name || "",
        quantity: Number(row.quantity) || 0,
        unitPrice: Number(row.unitPrice ?? row.unit_price) || 0,
        totalPrice: Number(row.totalPrice ?? row.total_price) || 0,
        dateTotalPrice: Number(row.dateTotalPrice ?? row.date_total_price) || 0,
        confirmStatus: row.confirmStatus || row.confirm_status || "未确认",
      };
    });
  }

  function normalizeAdminHistoryRows(items, processes) {
    return items.flatMap((item) => {
      const rows = normalizeHistoryRows(item.history.rows || [], processes);
      return rows.map((row) => ({
        ...row,
        accountId: item.account.id,
        accountName: item.account.account,
        employeeName: item.account.name || item.account.account,
      }));
    });
  }

  function bindEmployeeHistoryQuery(user, processes, today, initialTotal) {
    const result = document.querySelector("#historyResult");
    const PAGE_SIZE_DEFAULT = 15;
    const PAGE_SIZE_DATE = 10;

    async function showDefault(page) {
      try {
        const response = await queryWorkReports({
          accountId: user.id,
          page,
          pageSize: PAGE_SIZE_DEFAULT,
        });
        const rows = normalizeHistoryRows(response.rows || [], processes);
        result.innerHTML = renderDefaultDailyDetailResult(rows, page, response.total || 0);
      } catch (error) {
        window.alert("数据查询失败，请稍后再试。");
      }
    }

    async function showDateDetail(startDate, endDate, page) {
      try {
        const response = await queryWorkReports({
          accountId: user.id,
          startDate,
          endDate,
          page,
          pageSize: PAGE_SIZE_DATE,
        });
        const rows = normalizeHistoryRows(response.rows || [], processes);
        result.innerHTML = renderDateDetailResult(
          rows,
          startDate,
          endDate,
          page,
          response.total || 0,
          Number(response?.summary?.totalWage) || 0,
        );
      } catch (error) {
        window.alert("数据查询失败，请稍后再试。");
      }
    }

    document.querySelector("#monthSearchForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const startMonth = document.querySelector("#historyStartMonth").value;
      const endMonth = document.querySelector("#historyEndMonth").value;
      if (!startMonth || !endMonth) {
        window.alert("请选择开始月份和结束月份。");
        return;
      }

      if (startMonth > endMonth) {
        window.alert("开始月份不能晚于结束月份。");
        return;
      }

      try {
        const months = getMonthRangeKeys(startMonth, endMonth).reverse();
        const summaries = await Promise.all(
          months.map(async (month) => {
            const response = await queryWorkReports({ accountId: user.id, month, page: 1, pageSize: 1 });
            const summary = response?.summary || {};
            return {
              month,
              wage: Number(summary.totalWage) || 0,
              workDays: Number(summary.workDays) || 0,
            };
          })
        );
        result.innerHTML = renderMonthRangeSummaryResultFromSummaries(summaries, startMonth, endMonth);
      } catch (error) {
        window.alert("月份汇总查询失败，请稍后再试。");
      }
    });

    document.querySelector("#exportMonthWordButton").addEventListener("click", async () => {
      const exportMonth = document.querySelector("#historyStartMonth").value;
      if (!exportMonth) {
        window.alert("请选择开始月份。");
        return;
      }

      try {
        await exportEmployeeMonthlyWord(exportMonth);
      } catch (error) {
        window.alert(error.message || "Word 导出失败，请稍后再试。");
      }
    });

    document.querySelector("#processSearchForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const processId = document.querySelector("#historyProcess").value;
      const startDate = document.querySelector("#processStartDate").value;
      const endDate = document.querySelector("#processEndDate").value;
      const process = processes.find((item) => item.id === processId);

      if (!processId || !startDate || !endDate) {
        window.alert("请选择工序和时间范围。");
        return;
      }

      if (startDate > endDate) {
        window.alert("开始日期不能晚于结束日期。");
        return;
      }

      try {
        const response = await queryWorkReports({
          accountId: user.id,
          processId,
          startDate,
          endDate,
          page: 1,
          pageSize: 1000,
        });
        const rows = normalizeHistoryRows(response.rows || [], processes);
        const summary = response?.summary || {};
        result.innerHTML = renderProcessSearchResultFromServer(rows, process, startDate, endDate, summary);
      } catch (error) {
        window.alert("工序查询失败，请稍后再试。");
      }
    });

    document.querySelector("#historyResult").addEventListener("click", (event) => {
      if (event.target.matches("[data-action='date-page']")) {
        const startDate = event.target.dataset.startDate;
        const endDate = event.target.dataset.endDate;
        const page = Number(event.target.dataset.page) || 1;
        showDateDetail(startDate, endDate, page);
        return;
      }

      if (event.target.matches("[data-action='default-page']")) {
        const page = Number(event.target.dataset.page) || 1;
        showDefault(page);
        return;
      }

      if (!event.target.matches("[data-action='show-default-history']")) return;
      showDefault(1);
    });
  }

  function renderDefaultDailyDetailResult(pageRows, currentPage, totalRows) {
    const safePageSize = 15;
    const totalPages = Math.max(1, Math.ceil((totalRows || pageRows.length) / safePageSize));
    const safePage = Math.min(Math.max(1, currentPage), totalPages);
    const dailyWageMap = getDailyWageMap(pageRows);

    return `
      <div class="report-table-wrap">
        <table class="history-table history-default-detail-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>工序</th>
              <th>数量</th>
              <th>工资</th>
            </tr>
          </thead>
          <tbody>
            ${
              pageRows.length
                ? pageRows.map((row, index) => renderDefaultDailyDetailRow(row, pageRows[index - 1], pageRows[index + 1], dailyWageMap)).join("")
                : `<tr><td colspan="4" class="history-empty">暂无报工记录</td></tr>`
            }
          </tbody>
        </table>
      </div>
      ${renderDefaultPagination(totalRows || pageRows.length, safePage, totalPages)}
    `;
  }

  function getDailyWageMap(rows) {
    const wageMap = new Map();
    rows.forEach((row) => {
      const dateTotal = Number(row.dateTotalPrice);
      if (Number.isFinite(dateTotal) && dateTotal > 0) {
        wageMap.set(row.workDate, dateTotal);
      } else if (!wageMap.has(row.workDate) || !Number.isFinite(wageMap.get(row.workDate))) {
        wageMap.set(row.workDate, (wageMap.get(row.workDate) || 0) + row.totalPrice);
      }
    });
    return wageMap;
  }

  function renderDefaultDailyDetailRow(row, previousRow, nextRow, dailyWageMap) {
    const shouldShowDate = !previousRow || previousRow.workDate !== row.workDate;
    const shouldShowDailyTotal = !nextRow || nextRow.workDate !== row.workDate;
    const dailyTotal = dailyWageMap.get(row.workDate) || 0;

    return `
      <tr>
        <td>${shouldShowDate ? escapeHtml(formatMonthDay(row.workDate)) : ""}</td>
        <td>${escapeHtml(row.processName)}</td>
        <td>${row.quantity.toFixed(2)}</td>
        <td>¥${row.totalPrice.toFixed(2)}</td>
      </tr>
      ${
        shouldShowDailyTotal
          ? `<tr class="history-day-total-row"><td colspan="4"><span>当天总工资：<strong>¥${dailyTotal.toFixed(2)}</strong></span></td></tr>`
          : ""
      }
    `;
  }

  function renderDefaultPagination(totalRows, currentPage, totalPages) {
    if (totalPages <= 1) return "";

    return `
      <div class="history-pagination">
        <button class="button button-secondary button-small" data-action="default-page" data-page="${currentPage - 1}" type="button" ${currentPage === 1 ? "disabled" : ""}>上一页</button>
        <span>${currentPage} / ${totalPages}，共 ${totalRows} 条</span>
        <button class="button button-secondary button-small" data-action="default-page" data-page="${currentPage + 1}" type="button" ${currentPage === totalPages ? "disabled" : ""}>下一页</button>
      </div>
    `;
  }

  function renderMonthlySummaryTable(historyRows, today) {
    const summaries = getLast12MonthKeys(today).map((month) => {
      const rows = historyRows.filter((row) => row.workDate.slice(0, 7) === month);
      const workDays = new Set(rows.map((row) => row.workDate).filter(Boolean));
      return {
        month,
        wage: rows.reduce((sum, row) => sum + row.totalPrice, 0),
        workDays: workDays.size,
      };
    });

    return `
      <div class="report-table-wrap">
        <table class="history-table monthly-summary-table">
          <thead>
            <tr>
              <th>月份</th>
              <th>工资</th>
              <th>上班天数</th>
            </tr>
          </thead>
          <tbody>
            ${summaries.map((summary) => renderMonthlySummaryRow(summary)).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderMonthlySummaryRow(summary) {
    return `
      <tr>
        <td>${escapeHtml(summary.month)}</td>
        <td>¥${summary.wage.toFixed(2)}</td>
        <td>${summary.workDays}</td>
      </tr>
    `;
  }

  function renderMonthRangeSummaryResultFromSummaries(summaries, startMonth, endMonth) {
    const totalWage = summaries.reduce((sum, summary) => sum + summary.wage, 0);

    return `
      ${renderHistoryResultTitle(`${startMonth} 至 ${endMonth} 月工资汇总`)}
      <div class="history-result-toolbar">
        <span>总工资：¥${totalWage.toFixed(2)}</span>
        <button class="button button-secondary button-small" data-action="show-default-history" type="button">默认详情</button>
      </div>
      <div class="report-table-wrap">
        <table class="history-table monthly-summary-table">
          <thead>
            <tr>
              <th>月份</th>
              <th>工资</th>
              <th>上班天数</th>
            </tr>
          </thead>
          <tbody>
            ${summaries.map((summary) => renderMonthlySummaryRow(summary)).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function getMonthRangeKeys(startMonth, endMonth) {
    const months = [];
    const [startYear, startMonthIndex] = startMonth.split("-").map(Number);
    const [endYear, endMonthIndex] = endMonth.split("-").map(Number);
    const current = new Date(startYear, startMonthIndex - 1, 1);
    const end = new Date(endYear, endMonthIndex - 1, 1);

    while (current <= end) {
      months.push(`${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}`);
      current.setMonth(current.getMonth() + 1);
    }

    return months;
  }

  function getDateRangeRows(historyRows, startDate, endDate) {
    return historyRows
      .filter((row) => row.workDate >= startDate && row.workDate <= endDate)
      .sort((left, right) => right.workDate.localeCompare(left.workDate));
  }

  function getLatestWorkDate(rows) {
    return rows.reduce((latestDate, row) => {
      if (!row.workDate) return latestDate;
      return !latestDate || row.workDate > latestDate ? row.workDate : latestDate;
    }, "");
  }

  function renderDateDetailResult(pageRows, startDate, endDate, page = 1, totalRows = null, totalWage = null) {
    const pageSize = 10;
    const effectiveTotal = totalRows == null ? pageRows.length : totalRows;
    const totalPages = Math.max(1, Math.ceil(effectiveTotal / pageSize));
    const currentPage = Math.min(Math.max(1, page), totalPages);
    const effectiveWage =
      totalWage == null ? pageRows.reduce((sum, row) => sum + row.totalPrice, 0) : totalWage;
    return `
      ${renderHistoryResultTitle(`${startDate} 至 ${endDate} 工资详情`)}
      <div class="history-result-toolbar">
        <span>总工资：¥${effectiveWage.toFixed(2)}</span>
        <button class="button button-secondary button-small" data-action="show-default-history" type="button">默认详情</button>
      </div>
      <div class="report-table-wrap">
        <table class="history-table history-date-detail-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>工序</th>
              <th>数量</th>
              <th>单价</th>
              <th>工资</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            ${
              pageRows && pageRows.length
                ? pageRows.map((row) => renderDateRangeDetailRow(row)).join("")
                : `<tr><td colspan="6" class="history-empty">${escapeHtml(startDate)} 至 ${escapeHtml(endDate)} 暂无报工记录</td></tr>`
            }
          </tbody>
        </table>
      </div>
      ${renderDatePagination(effectiveTotal, currentPage, totalPages, startDate, endDate)}
    `;
  }

  function renderDateRangeDetailRow(row) {
    return `
      <tr>
        <td>${escapeHtml(row.workDate)}</td>
        <td>${escapeHtml(row.processName)}</td>
        <td>${row.quantity.toFixed(2)}</td>
        <td>¥${row.unitPrice.toFixed(2)}</td>
        <td>¥${row.totalPrice.toFixed(2)}</td>
        <td><span class="status-tag status-pending">${escapeHtml(row.confirmStatus)}</span></td>
      </tr>
    `;
  }

  function renderDatePagination(totalRows, currentPage, totalPages, startDate, endDate) {
    if (totalPages <= 1) return "";

    return `
      <div class="history-pagination">
        <button class="button button-secondary button-small" data-action="date-page" data-start-date="${escapeHtml(startDate)}" data-end-date="${escapeHtml(endDate)}" data-page="${currentPage - 1}" type="button" ${currentPage === 1 ? "disabled" : ""}>上一页</button>
        <span>${currentPage} / ${totalPages}，共 ${totalRows} 条</span>
        <button class="button button-secondary button-small" data-action="date-page" data-start-date="${escapeHtml(startDate)}" data-end-date="${escapeHtml(endDate)}" data-page="${currentPage + 1}" type="button" ${currentPage === totalPages ? "disabled" : ""}>下一页</button>
      </div>
    `;
  }

  function renderProcessSearchResultFromServer(rows, process, startDate, endDate, summary) {
    const totalQuantity = Number(summary?.totalQuantity) || rows.reduce((sum, row) => sum + row.quantity, 0);
    const totalWage = Number(summary?.totalWage) || rows.reduce((sum, row) => sum + row.totalPrice, 0);
    const workDays = Number(summary?.workDays) || new Set(rows.map((row) => row.workDate).filter(Boolean)).size;

    return `
      ${renderProcessHistoryTitle(`${process ? process.name : "工序"} 统计`, `${startDate} 至 ${endDate}`)}
      <div class="history-stat-grid">
        <div><span>总数量</span><strong>${totalQuantity.toFixed(2)}</strong></div>
        <div><span>总工资</span><strong>¥${totalWage.toFixed(2)}</strong></div>
        <div><span>报工天数</span><strong>${workDays}</strong></div>
      </div>
      <div class="history-result-toolbar">
        <span>明细记录</span>
        <button class="button button-secondary button-small" data-action="show-default-history" type="button">默认详情</button>
      </div>
      <div class="report-table-wrap">
        <table class="history-table history-detail-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>数量</th>
              <th>单价</th>
              <th>工资</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            ${
              rows.length
                ? rows.map((row) => renderHistoryDetailRow(row, true)).join("")
                : `<tr><td colspan="5" class="history-empty">这个时间段暂无该工序记录</td></tr>`
            }
          </tbody>
        </table>
      </div>
    `;
  }

  function renderHistoryResultTitle(title) {
    return `<div class="history-result-title">${escapeHtml(title)}</div>`;
  }

  function renderProcessHistoryTitle(title, dateRange) {
    return `
      <div class="history-result-title process-history-title">
        <span>${escapeHtml(title)}</span>
        <span>${escapeHtml(dateRange)}</span>
      </div>
    `;
  }

  function renderHistoryDetailRow(row, showDate) {
    return `
      <tr>
        <td>${escapeHtml(showDate ? row.workDate : row.processName)}</td>
        <td>${row.quantity.toFixed(2)}</td>
        <td>¥${row.unitPrice.toFixed(2)}</td>
        <td>¥${row.totalPrice.toFixed(2)}</td>
        <td><span class="status-tag status-pending">${escapeHtml(row.confirmStatus)}</span></td>
      </tr>
    `;
  }

  function getLocalDateString(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function getDateOffsetString(date, offsetDays) {
    const nextDate = new Date(date);
    nextDate.setDate(nextDate.getDate() + offsetDays);
    return getLocalDateString(nextDate);
  }

  function getLast12MonthKeys(today) {
    const [year, month] = today.slice(0, 7).split("-").map(Number);
    return Array.from({ length: 12 }, (_, index) => {
      const date = new Date(year, month - 1 - index, 1);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    });
  }

  function normalizeReportRows(savedRows) {
    const filledRows = savedRows.map((row) => ({
      processId: row.processId || "",
      processName: row.processName || "",
      unitPrice: Number(row.unitPrice) || 0,
      quantity: row.quantity ? String(row.quantity) : "",
    }));

    return ensureReportRowRules(filledRows);
  }

  function ensureReportRowRules(rows) {
    const nextRows = rows.slice();
    const blankCount = nextRows.filter((row) => !row.processId && !row.quantity).length;

    for (let index = blankCount; index < 2; index += 1) {
      nextRows.push({ processId: "", processName: "", unitPrice: 0, quantity: "" });
    }

    while (nextRows.length < 5) {
      nextRows.push({ processId: "", processName: "", unitPrice: 0, quantity: "" });
    }

    return nextRows;
  }

  function renderReportRow(row, index, processes, readonly = false) {
    const selectedProcess = processes.find((process) => process.id === row.processId);
    const processName = selectedProcess ? selectedProcess.name : row.processName || "";
    const unitPrice = selectedProcess ? Number(selectedProcess.price) : Number(row.unitPrice) || 0;
    const quantity = Number(row.quantity) || 0;
    const totalPrice = unitPrice * quantity;

    return `
      <tr data-report-row="${index}">
        <td>
          <div class="report-process-control">
            <input class="report-input report-process-input" data-field="processName" value="${escapeHtml(processName)}" placeholder="工序" autocomplete="off" inputmode="none" readonly aria-label="工序" />
            <button class="report-process-picker" data-action="open-process-options" type="button" aria-label="显示工序选项" ${readonly ? "disabled" : ""}></button>
            <input data-field="processId" type="hidden" value="${escapeHtml(row.processId)}" />
            <div class="report-process-menu" data-process-menu>
              ${processes.map((process) => `<button class="report-process-option" data-action="select-process-option" data-process-name="${escapeHtml(process.name)}" type="button">${escapeHtml(process.name)}</button>`).join("")}
            </div>
          </div>
        </td>
        <td>
          <input class="report-input report-price-input" data-field="unitPrice" value="${unitPrice ? `¥${unitPrice.toFixed(2)}` : ""}" readonly aria-label="单价" />
        </td>
        <td>
          <input class="report-input report-quantity-input" data-field="quantity" type="number" min="0" step="0.01" value="${escapeHtml(row.quantity)}" aria-label="数量" ${readonly ? "readonly" : ""} />
        </td>
        <td>
          <input class="report-input report-total-input" data-field="totalPrice" value="${totalPrice ? `¥${totalPrice.toFixed(2)}` : ""}" readonly aria-label="总价" />
        </td>
        <td>
          <button class="report-delete-button" data-action="delete-report-row" type="button" aria-label="删除本行" ${readonly ? "disabled" : ""}>删除</button>
        </td>
      </tr>
    `;
  }

  function readReportRowsFromDom(processes) {
    return Array.from(document.querySelectorAll("[data-report-row]")).map((rowElement) => {
      const processInput = rowElement.querySelector("[data-field='processName']");
      const quantity = rowElement.querySelector("[data-field='quantity']").value;
      const processName = processInput.value.trim();
      const process = processes.find((item) => item.name === processName);
      return {
        processId: process ? process.id : "",
        processName,
        unitPrice: process ? Number(process.price) : 0,
        quantity,
      };
    });
  }

  function calculateDailyWage(rows) {
    return rows.reduce((sum, row) => sum + (Number(row.unitPrice) || 0) * (Number(row.quantity) || 0), 0);
  }

  function calculateMonthlyWageBase(historyRows, selectedDate) {
    const selectedMonth = selectedDate.slice(0, 7);
    return historyRows
      .filter((row) => row.workDate && row.workDate.slice(0, 7) === selectedMonth && row.workDate !== selectedDate)
      .reduce((sum, row) => sum + (Number(row.totalPrice) || 0), 0);
  }

  function getDuplicateReportProcessName(rows) {
    const seenProcessIds = new Set();
    for (const row of rows) {
      if (!row.processId) continue;
      if (seenProcessIds.has(row.processId)) return row.processName || "同一工序";
      seenProcessIds.add(row.processId);
    }

    return "";
  }

  function refreshReportTable(processes, monthlyWageBase) {
    const rows = ensureReportRowRules(readReportRowsFromDom(processes));
    document.querySelector("#reportRows").innerHTML = rows.map((row, index) => renderReportRow(row, index, processes)).join("");
    refreshReportSummary(processes, monthlyWageBase);
    bindReportRowEvents(processes, monthlyWageBase);
  }

  function appendReportBlankRowsIfNeeded(processes, monthlyWageBase) {
    const rows = readReportRowsFromDom(processes);
    const blankCount = rows.filter((row) => !row.processName && !row.quantity).length;
    if (blankCount >= 2) return;

    const reportRows = document.querySelector("#reportRows");
    const startIndex = rows.length;
    const rowsToAdd = Array.from({ length: 2 - blankCount }, () => ({
      processId: "",
      processName: "",
      unitPrice: 0,
      quantity: "",
    }));

    reportRows.insertAdjacentHTML(
      "beforeend",
      rowsToAdd.map((row, index) => renderReportRow(row, startIndex + index, processes)).join("")
    );
    bindReportRowEvents(processes, monthlyWageBase);
  }

  function refreshSingleReportRow(rowElement, processes, monthlyWageBase) {
    const processName = rowElement.querySelector("[data-field='processName']").value.trim();
    const process = processes.find((item) => item.name === processName);
    const quantity = Number(rowElement.querySelector("[data-field='quantity']").value) || 0;
    const unitPrice = process ? Number(process.price) : 0;
    const totalPrice = unitPrice * quantity;

    rowElement.querySelector("[data-field='processId']").value = process ? process.id : "";
    rowElement.querySelector("[data-field='unitPrice']").value = unitPrice ? `¥${unitPrice.toFixed(2)}` : "";
    rowElement.querySelector("[data-field='totalPrice']").value = totalPrice ? `¥${totalPrice.toFixed(2)}` : "";
    refreshReportSummary(processes, monthlyWageBase);
  }

  function closeProcessMenus() {
    document.querySelectorAll(".report-process-control.is-open").forEach((control) => {
      control.classList.remove("is-open");
    });
  }

  function filterProcessMenu(rowElement) {
    rowElement.querySelectorAll(".report-process-option").forEach((option) => {
      option.hidden = false;
    });
  }

  function refreshReportSummary(processes, monthlyWageBase) {
    const rows = readReportRowsFromDom(processes);
    const dailyWage = calculateDailyWage(rows);
    document.querySelector("#dailyWage").textContent = `¥${dailyWage.toFixed(2)}`;
    document.querySelector("#monthlyWage").textContent = `¥${(monthlyWageBase + dailyWage).toFixed(2)}`;
  }

  function bindReportRowEvents(processes, monthlyWageBase) {
    document.querySelectorAll(".report-quantity-input").forEach((input) => {
      if (input.dataset.reportBound) return;
      input.dataset.reportBound = "true";
      input.addEventListener("change", () => {
        refreshSingleReportRow(input.closest("[data-report-row]"), processes, monthlyWageBase);
        appendReportBlankRowsIfNeeded(processes, monthlyWageBase);
      });
      input.addEventListener("input", () => {
        refreshSingleReportRow(input.closest("[data-report-row]"), processes, monthlyWageBase);
        appendReportBlankRowsIfNeeded(processes, monthlyWageBase);
      });
    });
    document.querySelectorAll(".report-process-input").forEach((input) => {
      if (input.dataset.reportBound) return;
      input.dataset.reportBound = "true";
      input.addEventListener("click", () => {
        const rowElement = input.closest("[data-report-row]");
        const control = rowElement?.querySelector(".report-process-control");
        if (!control) return;

        const shouldOpen = !control.classList.contains("is-open");
        closeProcessMenus();
        filterProcessMenu(rowElement);
        control.classList.toggle("is-open", shouldOpen);
      });
    });
    document.querySelectorAll("[data-action='delete-report-row']").forEach((button) => {
      if (button.dataset.reportBound) return;
      button.dataset.reportBound = "true";
      button.addEventListener("click", () => {
        const rowElement = button.closest("[data-report-row]");
        if (!rowElement) return;
        rowElement.remove();
        refreshReportTable(processes, monthlyWageBase);
      });
    });
    document.querySelectorAll("[data-action='open-process-options']").forEach((button) => {
      if (button.dataset.reportBound) return;
      button.dataset.reportBound = "true";
      button.addEventListener("click", () => {
        const rowElement = button.closest("[data-report-row]");
        const control = rowElement?.querySelector(".report-process-control");
        const processInput = rowElement?.querySelector("[data-field='processName']");
        if (!control || !processInput) return;

        const shouldOpen = !control.classList.contains("is-open");
        closeProcessMenus();
        processInput.blur();
        filterProcessMenu(rowElement);
        control.classList.toggle("is-open", shouldOpen);
      });
    });
    document.querySelectorAll("[data-action='select-process-option']").forEach((button) => {
      if (button.dataset.reportBound) return;
      button.dataset.reportBound = "true";
      button.addEventListener("click", () => {
        const rowElement = button.closest("[data-report-row]");
        const processInput = rowElement.querySelector("[data-field='processName']");
        processInput.value = button.dataset.processName;
        refreshSingleReportRow(rowElement, processes, monthlyWageBase);
        appendReportBlankRowsIfNeeded(processes, monthlyWageBase);
        closeProcessMenus();
      });
    });
  }

  function getPreviousReportedDate(historyRows, currentDate) {
    const reportDates = Array.from(
      new Set(
        historyRows
          .map((row) => row.workDate || row.work_date || "")
          .filter((workDate) => workDate && workDate < currentDate)
      )
    ).sort((left, right) => right.localeCompare(left));

    return reportDates[0] || "";
  }

  function getNextReportedDate(historyRows, currentDate) {
    const reportDates = Array.from(
      new Set(
        historyRows
          .map((row) => row.workDate || row.work_date || "")
          .filter((workDate) => workDate && workDate > currentDate)
      )
    ).sort((left, right) => left.localeCompare(right));

    return reportDates[0] || "";
  }

  function bindReportSwipe(historyRows, workDate) {
    const tableWrap = document.querySelector(".report-table-wrap");
    if (!tableWrap) return;

    let startX = null;
    let startY = null;

    tableWrap.addEventListener(
      "touchstart",
      (event) => {
        const touch = event.touches[0];
        if (!touch) return;
        startX = touch.clientX;
        startY = touch.clientY;
      },
      { passive: true }
    );

    tableWrap.addEventListener(
      "touchend",
      (event) => {
        const touch = event.changedTouches[0];
        if (!touch || startX === null || startY === null) return;

        const deltaX = touch.clientX - startX;
        const deltaY = touch.clientY - startY;
        startX = null;
        startY = null;

        if (Math.abs(deltaX) < 70 || Math.abs(deltaY) > 60 || Math.abs(deltaX) < Math.abs(deltaY) * 1.4) return;

        const targetDate = deltaX > 0 ? getPreviousReportedDate(historyRows, workDate) : getNextReportedDate(historyRows, workDate);
        if (targetDate) {
          renderEmployeeWorkReport(targetDate);
        }
      },
      { passive: true }
    );
  }

  function bindReportTable(processes, accountId, monthlyWageBase, hasSavedReport, historyRows, workDate) {
    bindReportSwipe(historyRows, workDate);
    if (!hasSavedReport) {
      bindReportRowEvents(processes, monthlyWageBase);
    }
    document.querySelector("#workDate").addEventListener("change", (event) => {
      const selectedDate = event.target.value;
      const today = getLocalDateString(new Date());
      if (selectedDate > today) {
        window.alert("不能提前报工，只能选择今天或过去日期。");
        renderEmployeeWorkReport(today);
        return;
      }
      renderEmployeeWorkReport(selectedDate);
    });
    document.querySelector("#saveReportButton").addEventListener("click", async () => {
      const workDate = document.querySelector("#workDate").value;
      const today = getLocalDateString(new Date());
      if (workDate > today) {
        window.alert("不能提前报工，只能选择今天或过去日期。");
        return;
      }
      if (hasSavedReport) {
        window.alert("该日期已报工，记录不能再次提交或修改。");
        return;
      }

      const validRows = readReportRowsFromDom(processes).filter((row) => row.processId && Number(row.quantity) > 0);
      if (!validRows.length) {
        window.alert("请至少填写一条报工记录。");
        return;
      }

      const duplicateProcessName = getDuplicateReportProcessName(validRows);
      if (duplicateProcessName) {
        window.alert(`同一天同一个工序只能报一次：${duplicateProcessName}`);
        return;
      }

      const rows = validRows.map((row) => ({ process_id: row.processId, quantity: Number(row.quantity) }));

      try {
        await saveWorkReport(accountId, workDate, rows);
        window.alert("报工已保存。");
        renderEmployeeWorkReport(workDate);
      } catch (error) {
        window.alert(error.message || "报工保存失败，请稍后再试。");
      }
    });
  }

  async function renderAccountManagement() {
    const user = requireAdmin();
    if (!user) return;

    let data = readData();
    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-management-grid">
            <section class="admin-section empty-section">
              <h2>账号列表加载中</h2>
            </section>
          </section>
          ${renderAdminFooter("/admin/processes", "工序管理")}
        </section>
      </main>
    `;
    bindAdminNavigation();

    data = await loadSharedAccounts(data);
    data = await loadSharedProcesses(data);
    latestAdminData = data;
    const visibleAccounts = getVisibleAccounts(data, user);
    const processesForAccountConfig = data.processes.filter((process) => process.status === "active");
    const canCreateAccount = !isSuperAdmin(user);
    const creatableRoles = roleOptions.filter((role) => role.value === "employee");

    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-management-grid">
            ${
              canCreateAccount
                ? `<section class="admin-section">
                    <div class="section-heading account-create-heading">
                      <div>
                        <h2 class="account-create-title">新增账号</h2>
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
                      <div class="field account-process-field">
                        <div class="account-process-checklist" id="newAccountProcesses" role="group" aria-label="可报工工序">
                          <p class="account-process-title">工序配置</p>
                          ${
                            processesForAccountConfig.length
                              ? processesForAccountConfig.map((process) => renderProcessCheckbox(process)).join("")
                              : `<p class="account-process-empty">暂无工序，请先新增工序</p>`
                          }
                        </div>
                      </div>
                      <button class="button button-primary button-medium" type="submit">新增账号</button>
                      <p class="error-message" id="accountError"></p>
                    </form>
                  </section>`
                : ""
            }
            <section class="admin-section">
              <div class="section-heading account-list-heading">
                <div>
                  <h2 class="account-list-title">账号列表</h2>
                </div>
              </div>
              <div class="table-wrap account-table-wrap">
                <table class="data-table account-table account-management-table">
                  <thead>
                    <tr>
                      <th>账号</th>
                      <th>密码管理</th>
                      <th>工序</th>
                      <th>权限</th>
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
    if (canCreateAccount) {
      bindSelectPlaceholder("#newAccountRole");
      document.querySelector("#accountForm").addEventListener("submit", (event) => handleCreateAccount(event, user));
    }
    document.querySelectorAll("[data-action='delete-account']").forEach((button) => {
      button.addEventListener("click", () => handleDeleteAccount(button.dataset.id));
    });
    document.querySelectorAll("[data-action='change-password']").forEach((button) => {
      button.addEventListener("click", () => handleChangeAccountPassword(button.dataset.id));
    });
    document.querySelectorAll("[data-action='manage-account-processes']").forEach((button) => {
      button.addEventListener("click", () => openAccountProcessEditor(button.dataset.id));
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
    const canManageAccount = !isSuperAdmin(user) && (account.id === user.id || account.managerId === user.id);
    const canDeleteAccount = !isSuperAdmin(user) && account.role === "employee" && account.managerId === user.id;
    const deleteHtml = canDeleteAccount
      ? `<button class="button button-danger button-small account-delete-button" data-action="delete-account" data-id="${account.id}" type="button" ${account.id === user.id ? "disabled" : ""}>删除</button>`
      : "";
    const editNameHtml = canManageAccount
      ? `<button class="button button-primary button-small account-inline-button account-edit-button" data-action="change-account-name" data-id="${account.id}" type="button">修改</button>`
      : "";
    const editPasswordHtml = canManageAccount
      ? `<button class="button button-primary button-small account-inline-button account-edit-button" data-action="change-password" data-id="${account.id}" type="button">修改</button>`
      : "";
    const processButtonHtml = canManageAccount && account.role === "employee"
      ? `<button class="button button-primary button-small account-process-button" data-action="manage-account-processes" data-id="${account.id}" type="button">工序</button>`
      : "";
    const statusButtonHtml = canManageAccount
      ? `<button class="button ${statusClass} button-small account-status-button" data-action="toggle-account-status" data-id="${account.id}" type="button" ${account.id === user.id ? "disabled" : ""}>${account.status === "active" ? "启用" : "停用"}</button>`
      : `<span class="status-tag ${account.status === "active" ? "status-active" : "status-disabled"}">${account.status === "active" ? "启用" : "停用"}</span>`;
    const passwordText = isSuperAdmin(user) ? account.passwordDisplay || "已加密，无法查看" : "已加密保存";

    return `
      <tr>
        <td class="account-name-cell">
          <strong>${escapeHtml(account.account)}</strong>
          ${editNameHtml}
        </td>
        <td class="account-password-cell">
          <span class="account-password">${escapeHtml(passwordText)}</span>
          ${editPasswordHtml}
        </td>
        <td class="account-process-cell">
          ${processButtonHtml}
        </td>
        <td class="account-role-cell">
          <button class="button button-secondary button-small account-role-button" type="button" disabled>${escapeHtml(getRoleLabel(account.role))}</button>
        </td>
        <td class="account-status-cell">
          ${statusButtonHtml}
        </td>
        <td class="account-action-cell">
          ${deleteHtml}
        </td>
      </tr>
    `;
  }

  function openAccountProcessEditor(accountId) {
    const data = getLatestAdminData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const activeProcesses = data.processes.filter((process) => process.status === "active");
    const selectedProcessIds = new Set(account.processIds || []);
    const existingModal = document.querySelector("#accountProcessModal");
    if (existingModal) existingModal.remove();

    app.insertAdjacentHTML(
      "beforeend",
      `
        <div class="account-process-modal" id="accountProcessModal" role="dialog" aria-modal="true" aria-label="账号工序配置">
          <div class="account-process-dialog">
            <div class="account-process-dialog-heading">
              <strong>${escapeHtml(account.account)}</strong>
              <button class="account-process-close" data-action="close-account-processes" type="button" aria-label="关闭">×</button>
            </div>
            <div class="account-process-dialog-list" role="group" aria-label="账号可报工工序">
              <p class="account-process-title">工序配置</p>
              ${
                activeProcesses.length
                  ? activeProcesses.map((process) => renderAccountProcessEditorOption(process, selectedProcessIds.has(process.id))).join("")
                  : `<p class="account-process-empty">暂无启用工序</p>`
              }
            </div>
            <p class="error-message" id="accountProcessError"></p>
            <div class="account-process-dialog-actions">
              <button class="button button-secondary button-medium" data-action="close-account-processes" type="button">取消</button>
              <button class="button button-primary button-medium" data-action="save-account-processes" data-id="${account.id}" type="button">保存</button>
            </div>
          </div>
        </div>
      `
    );

    document.querySelectorAll("[data-action='close-account-processes']").forEach((button) => {
      button.addEventListener("click", closeAccountProcessEditor);
    });
    document.querySelector("[data-action='save-account-processes']").addEventListener("click", () => handleSaveAccountProcesses(account.id));
  }

  function renderAccountProcessEditorOption(process, isChecked) {
    const processName = String(process.name || "");
    const spanClass = getProcessOptionSpanClass(processName);
    return `
      <label class="account-process-option ${spanClass}">
        <input class="account-process-checkbox" type="checkbox" name="editProcessIds" value="${escapeHtml(process.id)}" ${isChecked ? "checked" : ""} />
        <span>${escapeHtml(processName)}</span>
      </label>
    `;
  }

  function closeAccountProcessEditor() {
    document.querySelector("#accountProcessModal")?.remove();
  }

  async function handleSaveAccountProcesses(accountId) {
    const error = document.querySelector("#accountProcessError");
    const processIds = Array.from(document.querySelectorAll("input[name='editProcessIds']:checked")).map((input) => input.value);

    if (!processIds.length) {
      showInlineError(error, "请至少保留一个可报工工序。");
      return;
    }

    try {
      await updateSharedAccount(accountId, { process_ids: processIds });
      closeAccountProcessEditor();
      renderAccountManagement();
    } catch (saveError) {
      showInlineError(error, "工序配置保存失败，请稍后再试。");
    }
  }

  function renderProcessCheckbox(process) {
    const processName = String(process.name || "");
    const spanClass = getProcessOptionSpanClass(processName);
    return `
      <label class="account-process-option ${spanClass}">
        <input class="account-process-checkbox" type="checkbox" name="processIds" value="${escapeHtml(process.id)}" />
        <span>${escapeHtml(processName)}</span>
      </label>
    `;
  }

  function getProcessOptionSpanClass(processName) {
    if (processName.length >= 8) return "is-extra-wide";
    if (processName.length > 4) return "is-wide";
    return "";
  }

  async function handleCreateAccount(event, user) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const accountName = String(form.get("account") || "").trim();
    const password = String(form.get("password") || "").trim();
    const role = String(form.get("role") || "");
    const processIds = Array.from(document.querySelectorAll("input[name='processIds']:checked")).map((input) => input.value);
    const error = document.querySelector("#accountError");
    const data = getLatestAdminData();

    if (!accountName || !password) {
      showInlineError(error, "账号名称和密码都需要填写。");
      return;
    }

    if (!role) {
      showInlineError(error, "请选择账号权限。");
      return;
    }

    if (!processIds.length) {
      showInlineError(error, "请给账号配置至少一个可报工工序。");
      return;
    }

    if (!isSuperAdmin(user) && role !== "employee") {
      showInlineError(error, "管理员只能新增员工账号。");
      return;
    }

    if (data.accounts.some((item) => item.account === accountName)) {
      showInlineError(error, "账号名称已存在，请换一个。");
      return;
    }

    const account = {
      id: `u-${Date.now()}`,
      account: accountName,
      role,
      name: accountName,
      status: "active",
      managerId: !isSuperAdmin(user) ? user.id : null,
      processIds,
    };

    try {
      await createSharedAccount({
        account: accountName,
        password,
        role,
        name: accountName,
        status: "active",
        manager_id: account.managerId,
        process_ids: processIds,
      });
      renderAccountManagement();
    } catch (saveError) {
      showInlineError(error, "账号名称已存在，或后端保存失败。");
    }
  }

  async function handleDeleteAccount(accountId) {
    const user = getCurrentUser();
    if (!user || accountId === user.id) return;
    if (!window.confirm("确定删除这个账号吗？删除后账号列表中不再显示。")) return;

    const data = getLatestAdminData();

    try {
      await deleteSharedAccount(accountId);
      renderAccountManagement();
    } catch (error) {
      window.alert("后端删除失败，请稍后再试。");
    }
  }

  async function handleChangeAccountPassword(accountId) {
    const data = getLatestAdminData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const password = window.prompt("请输入新的账号密码");
    if (!password || !password.trim()) return;

    const nextPassword = password.trim();

    try {
      await updateSharedAccount(accountId, { password: nextPassword });
      renderAccountManagement();
    } catch (error) {
      window.alert("后端保存失败，请稍后再试。");
    }
  }

  async function handleChangeAccountName(accountId) {
    const data = getLatestAdminData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const accountName = window.prompt("请输入新的账号名称", account.account);
    if (!accountName || !accountName.trim()) return;

    const nextName = accountName.trim();
    if (data.accounts.some((item) => item.id !== accountId && item.account === nextName)) {
      window.alert("账号名称已存在，请换一个。");
      return;
    }

    try {
      await updateSharedAccount(accountId, { account: nextName, name: nextName });
      renderAccountManagement();
    } catch (error) {
      window.alert("账号名称已存在，或后端保存失败。");
    }
  }

  async function handleToggleAccountStatus(accountId) {
    const user = getCurrentUser();
    if (!user || accountId === user.id) return;

    const data = getLatestAdminData();
    const account = data.accounts.find((item) => item.id === accountId);
    if (!account) return;

    const nextStatus = account.status === "active" ? "disabled" : "active";
    const actionText = nextStatus === "active" ? "启用" : "停用";
    if (!window.confirm(`确定${actionText}这个账号吗？`)) return;

    try {
      await updateSharedAccount(accountId, { status: nextStatus });
      renderAccountManagement();
    } catch (error) {
      window.alert("后端保存失败，请稍后再试。");
    }
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
    latestAdminData = data;
    const canManageProcesses = !isSuperAdmin(user);
    const totalProcessPages = Math.max(1, Math.ceil(data.processes.length / PROCESS_PAGE_SIZE));
    currentProcessPage = Math.min(currentProcessPage, totalProcessPages);
    const processPageStart = (currentProcessPage - 1) * PROCESS_PAGE_SIZE;
    const visibleProcesses = data.processes.slice(processPageStart, processPageStart + PROCESS_PAGE_SIZE);

    app.innerHTML = `
      <main class="app-page admin-layout">
          ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-management-grid">
            ${
              canManageProcesses
                ? `<section class="admin-section">
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
                  </section>`
                : ""
            }
            <section class="admin-section">
              <div class="section-heading process-list-heading">
                <div>
                  <h2 class="process-list-title">工序列表</h2>
                </div>
              </div>
              <div class="table-wrap account-table-wrap">
                <table class="data-table account-table process-table ${canManageProcesses ? "process-table-with-actions" : ""}">
                  <thead>
                    <tr>
                      <th>工序名称</th>
                      <th>当前单价</th>
                      <th>状态</th>
                      ${canManageProcesses ? "<th>操作</th>" : ""}
                    </tr>
                  </thead>
                  <tbody>
                    ${visibleProcesses.map((process) => renderProcessRow(process, canManageProcesses)).join("")}
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
    if (canManageProcesses) {
      bindSelectPlaceholder("#processUnit");
      document.querySelector("#processForm").addEventListener("submit", handleCreateProcess);
    }
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

  function renderProcessRow(process, canManageProcess) {
    const statusClass = process.status === "active" ? "button-success" : "button-danger";
    const unitLabel = process.unit ? ` / ${escapeHtml(process.unit.replace(/^元\//, ""))}` : "";
    return `
      <tr>
        <td class="account-name-cell">
          <strong>${escapeHtml(process.name)}</strong>
          ${canManageProcess ? `<button class="button button-primary button-small account-inline-button account-edit-button" data-action="rename-process" data-id="${process.id}" type="button">修改</button>` : ""}
        </td>
        <td class="account-password-cell">
          <span class="account-password process-price">¥${Number(process.price).toFixed(2)}${unitLabel}</span>
          ${canManageProcess ? `<button class="button button-primary button-small account-inline-button account-edit-button" data-action="change-price" data-id="${process.id}" type="button">修改</button>` : ""}
        </td>
        <td class="account-status-cell">
          ${
            canManageProcess
              ? `<button class="button ${statusClass} button-small account-status-button" data-action="toggle-process-status" data-id="${process.id}" type="button">${process.status === "active" ? "启用" : "停用"}</button>`
              : `<span class="status-tag ${process.status === "active" ? "status-active" : "status-disabled"}">${process.status === "active" ? "启用" : "停用"}</span>`
          }
        </td>
        ${
          canManageProcess
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
    const data = getLatestAdminData();

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
      await createSharedProcess({ name, price, unit });
      renderProcessManagement();
    } catch (saveError) {
      showInlineError(error, "工序名称已存在，或后端保存失败。");
    }
  }

  async function handleRenameProcess(processId) {
    const data = getLatestAdminData();
    const process = data.processes.find((item) => item.id === processId);
    if (!process) return;

    const name = window.prompt("请输入新的工序名称", process.name);
    if (!name || !name.trim()) return;

    const nextName = name.trim();

    try {
      await updateSharedProcess(processId, { name: nextName });
      renderProcessManagement();
    } catch (error) {
      window.alert("工序名称已存在，或后端保存失败。");
    }
  }

  async function handleChangeProcessPrice(processId) {
    const data = getLatestAdminData();
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
      await updateSharedProcess(processId, { price });
      renderProcessManagement();
    } catch (error) {
      window.alert("后端保存失败，请稍后再试。");
    }
  }

  async function handleToggleProcessStatus(processId) {
    const data = getLatestAdminData();
    const process = data.processes.find((item) => item.id === processId);
    if (!process) return;

    const nextStatus = process.status === "active" ? "disabled" : "active";
    const actionText = nextStatus === "active" ? "启用" : "停用";
    if (!window.confirm(`确定${actionText}这个工序吗？`)) return;

    try {
      await updateSharedProcess(processId, { status: nextStatus });
      renderProcessManagement();
    } catch (error) {
      window.alert("后端保存失败，请稍后再试。");
    }
  }

  async function handleDeleteProcess(processId) {
    const user = getCurrentUser();
    if (!user || isSuperAdmin(user)) return;
    if (!window.confirm("确定删除这个工序吗？删除后工序列表中不再显示。")) return;

    const data = getLatestAdminData();

    try {
      await deleteSharedProcess(processId);
      renderProcessManagement();
    } catch (error) {
      window.alert("后端删除失败，请稍后再试。");
    }
  }

  async function renderAdminQuery() {
    const user = requireAdmin();
    if (!user) return;

    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main">
            <section class="admin-section empty-section">
              <h2>数据查询加载中</h2>
            </section>
          </section>
          ${renderAdminFooter("/admin/processes", "工序管理")}
        </section>
      </main>
    `;

    bindAdminNavigation();

    let data = readData();
    data = await loadSharedAccounts(data);
    data = await loadSharedProcesses(data);
    latestAdminData = data;

    const visibleEmployees = getVisibleAccounts(data, user).filter((account) => account.role === "employee");

    let latestWorkDate = getLocalDateString(new Date());
    let defaultRows = [];
    let defaultTotal = 0;
    let defaultSummary = { totalWage: 0, totalQuantity: 0, workDays: 0 };
    try {
      const latestResponse = await queryWorkReports({ page: 1, pageSize: 1 });
      const latestRow = (latestResponse.rows || [])[0];
      if (latestRow && latestRow.workDate) {
        latestWorkDate = latestRow.workDate;
      }
      const defaultResponse = await queryWorkReports({
        startDate: latestWorkDate,
        endDate: latestWorkDate,
        page: 1,
        pageSize: 1000,
      });
      defaultRows = normalizeAdminHistoryRowsFromServer(defaultResponse.rows || [], data.processes, visibleEmployees);
      defaultTotal = defaultResponse.total || defaultRows.length;
      defaultSummary = defaultResponse.summary || defaultSummary;
    } catch (error) {
      defaultRows = [];
    }

    const adminExportMonth = latestWorkDate.slice(0, 7);

    app.innerHTML = `
      <main class="app-page admin-layout">
        ${renderAppHeader()}
        <section class="admin-shell">
          <section class="admin-main admin-query-main">
            <section class="admin-section admin-query-section">
              <div class="section-heading admin-query-heading">
                <div>
                  <h2 class="admin-query-title">数据查询</h2>
                </div>
              </div>
              <form class="admin-query-form" id="adminQueryForm" novalidate>
                <div class="field">
                  <label for="adminQueryEmployee">员工</label>
                  <select class="input select" id="adminQueryEmployee" name="employeeId">
                    <option value="">全部员工</option>
                    ${visibleEmployees
                      .map((account) => `<option value="${escapeHtml(account.id)}">${escapeHtml(account.account)}</option>`)
                      .join("")}
                  </select>
                </div>
                <div class="field">
                  <label for="adminQueryStartDate">开始日期</label>
                  <input class="input" id="adminQueryStartDate" name="startDate" type="date" value="${escapeHtml(latestWorkDate)}" />
                </div>
                <div class="field">
                  <label for="adminQueryEndDate">结束日期</label>
                  <input class="input" id="adminQueryEndDate" name="endDate" type="date" value="${escapeHtml(latestWorkDate)}" />
                </div>
                <div class="field">
                  <label for="adminQueryProcess">工序</label>
                  <select class="input select" id="adminQueryProcess" name="processId">
                    ${renderAdminQueryProcessOptions(data.processes, visibleEmployees, "")}
                  </select>
                </div>
                <button class="button button-primary button-medium admin-query-submit" type="submit">查询</button>
              </form>
              <div class="admin-export-row">
                <div class="field admin-export-field">
                  <label for="adminExportMonth">导出月份</label>
                  <input class="input" id="adminExportMonth" name="exportMonth" type="month" value="${escapeHtml(adminExportMonth)}" />
                </div>
                <button class="button button-secondary button-medium admin-export-button" id="adminExportWordButton" type="button">导出 Word</button>
              </div>
            </section>
            <section class="admin-section admin-query-section">
              <div id="adminQueryResult">
                ${renderAdminQueryResult(defaultRows, `${latestWorkDate} 至 ${latestWorkDate}`, 1, "", defaultSummary)}
              </div>
            </section>
          </section>
          ${renderAdminFooter("/admin/processes", "工序管理")}
        </section>
      </main>
    `;

    bindAdminNavigation();
    bindAdminQueryForm(data.processes, visibleEmployees, latestWorkDate, defaultSummary);
  }

  function bindAdminQueryForm(processes, employees, latestWorkDate, initialSummary) {
    const form = document.querySelector("#adminQueryForm");
    const result = document.querySelector("#adminQueryResult");
    if (!form || !result) return;
    const employeeSelect = document.querySelector("#adminQueryEmployee");
    const processSelect = document.querySelector("#adminQueryProcess");
    const PAGE_SIZE = 15;

    let currentFilters = {
      employeeId: "",
      startDate: latestWorkDate,
      endDate: latestWorkDate,
      processId: "",
    };
    let currentTitle = `${latestWorkDate} 至 ${latestWorkDate}`;
    let currentProcessId = "";

    async function fetchAndRender(page) {
      try {
        const response = await queryWorkReports({
          accountId: currentFilters.employeeId || undefined,
          startDate: currentFilters.startDate,
          endDate: currentFilters.endDate,
          processId: currentFilters.processId || undefined,
          page,
          pageSize: PAGE_SIZE,
        });
        const rows = normalizeAdminHistoryRowsFromServer(response.rows || [], processes, employees);
        result.innerHTML = renderAdminQueryResult(
          rows,
          currentTitle,
          page,
          currentProcessId,
          response.summary || {},
          response.total || rows.length,
        );
      } catch (error) {
        window.alert("查询失败，请稍后再试。");
      }
    }

    if (employeeSelect && processSelect) {
      employeeSelect.addEventListener("change", () => {
        const currentProcessId = processSelect.value;
        const employeeId = employeeSelect.value;
        const availableProcesses = getAdminQueryProcesses(processes, employees, employeeId);
        const nextProcessId = availableProcesses.some((process) => process.id === currentProcessId) ? currentProcessId : "";
        processSelect.innerHTML = renderAdminQueryProcessOptions(processes, employees, employeeId, nextProcessId);
      });
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const employeeId = String(formData.get("employeeId") || "");
      const startDate = String(formData.get("startDate") || "");
      const endDate = String(formData.get("endDate") || "");
      const processId = String(formData.get("processId") || "");

      if (!startDate || !endDate) {
        window.alert("请选择开始日期和结束日期。");
        return;
      }

      if (startDate > endDate) {
        window.alert("开始日期不能晚于结束日期。");
        return;
      }

      currentFilters = { employeeId, startDate, endDate, processId };
      currentTitle = `${startDate} 至 ${endDate}`;
      currentProcessId = processId;
      fetchAndRender(1);
    });

    result.addEventListener("click", (event) => {
      const pageButton = event.target.closest("[data-action='admin-query-page']");
      if (!pageButton) return;
      fetchAndRender(Number(pageButton.dataset.page) || 1);
    });

    const exportButton = document.querySelector("#adminExportWordButton");
    if (exportButton) {
      exportButton.addEventListener("click", async () => {
        const employeeId = employeeSelect ? employeeSelect.value : "";
        const exportMonth = document.querySelector("#adminExportMonth")?.value || "";
        if (!employeeId) {
          window.alert("请选择要导出的员工。");
          return;
        }
        if (!exportMonth) {
          window.alert("请选择导出月份。");
          return;
        }

        try {
          await exportAdminMonthlyWord(employeeId, exportMonth);
        } catch (error) {
          window.alert(error.message || "Word 导出失败，请稍后再试。");
        }
      });
    }
  }

  function normalizeAdminHistoryRowsFromServer(rows, processes, employees) {
    return (rows || []).map((row) => {
      const process = processes.find((item) => item.id === row.processId || item.name === row.processName);
      const employee = employees.find((account) => account.id === row.accountId);
      return {
        workDate: row.workDate || row.work_date || "",
        processId: row.processId || row.process_id || process?.id || "",
        processName: row.processName || row.process_name || process?.name || "",
        quantity: Number(row.quantity) || 0,
        unitPrice: Number(row.unitPrice ?? row.unit_price) || 0,
        totalPrice: Number(row.totalPrice ?? row.total_price) || 0,
        dateTotalPrice: Number(row.dateTotalPrice ?? row.date_total_price) || 0,
        confirmStatus: row.confirmStatus || row.confirm_status || "未确认",
        accountId: row.accountId || row.account_id || employee?.id || "",
        accountName: row.accountLogin || employee?.account || "",
        employeeName: row.accountName || employee?.name || employee?.account || "",
      };
    });
  }

  function getAdminQueryProcesses(processes, employees, employeeId) {
    return window.AdminQueryHelpers.getProcessesForAdminQueryEmployee(processes, employees, employeeId);
  }

  function renderAdminQueryProcessOptions(processes, employees, employeeId, selectedProcessId = "") {
    const visibleProcesses = getAdminQueryProcesses(processes, employees, employeeId);
    return `
      <option value="">全部工序</option>
      ${visibleProcesses
        .map(
          (process) =>
            `<option value="${escapeHtml(process.id)}" ${process.id === selectedProcessId ? "selected" : ""}>${escapeHtml(process.name)}</option>`
        )
        .join("")}
    `;
  }

  function renderAdminQueryResult(rows, title, currentPage = 1, selectedProcessId = "", summary = {}, totalRows = null) {
    const pageSize = 15;
    const pageRows = getAdminQueryDetailRows(rows);
    const effectiveTotal = totalRows == null ? pageRows.length : totalRows;
    const totalPages = Math.max(1, Math.ceil(effectiveTotal / pageSize));
    const safePage = Math.min(Math.max(currentPage, 1), totalPages);
    const dailyWageMap = getAdminDailyWageMap(pageRows);
    const totalWage = Number(summary.totalWage) || pageRows.reduce((sum, row) => sum + row.totalPrice, 0);
    const workDays = Number(summary.workDays) || new Set(pageRows.map((row) => row.workDate).filter(Boolean)).size;
    const totalQuantity = Number(summary.totalQuantity) || pageRows.reduce((sum, row) => sum + row.quantity, 0);
    const secondaryStatLabel = selectedProcessId ? "数量" : "上班天数";
    const secondaryStatValue = selectedProcessId ? totalQuantity.toFixed(2) : workDays;

    return `
      <div class="admin-query-result-heading">
        <div>
          <h3>${escapeHtml(title)}</h3>
        </div>
      </div>
      <div class="admin-query-stats">
        <span>工资总额：<strong>¥${totalWage.toFixed(2)}</strong></span>
        <span>${secondaryStatLabel}：<strong>${secondaryStatValue}</strong></span>
      </div>
      <div class="table-wrap">
        <table class="data-table admin-query-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>工序</th>
              <th>数量</th>
              <th>工资</th>
            </tr>
          </thead>
          <tbody>
            ${
              pageRows.length
                ? pageRows.map((row, index) => renderAdminQueryRow(row, pageRows[index - 1], pageRows[index + 1], dailyWageMap)).join("")
                : `<tr><td colspan="4" class="history-empty">暂无报工记录</td></tr>`
            }
          </tbody>
        </table>
      </div>
      ${renderAdminQueryPagination(effectiveTotal, safePage, totalPages)}
    `;
  }

  function getAdminQueryDetailRows(rows) {
    return [...rows].sort((left, right) => {
      const dateOrder = right.workDate.localeCompare(left.workDate);
      if (dateOrder) return dateOrder;
      const employeeOrder = left.accountName.localeCompare(right.accountName, "zh-CN");
      if (employeeOrder) return employeeOrder;
      return left.processName.localeCompare(right.processName, "zh-CN");
    });
  }

  function getAdminDailyWageMap(rows) {
    const wageMap = new Map();
    rows.forEach((row) => {
      const dateTotal = Number(row.dateTotalPrice);
      if (Number.isFinite(dateTotal) && dateTotal > 0) {
        wageMap.set(row.workDate, dateTotal);
      } else if (!wageMap.has(row.workDate)) {
        wageMap.set(row.workDate, (wageMap.get(row.workDate) || 0) + row.totalPrice);
      }
    });
    return wageMap;
  }

  function getAdminQuerySummaryRows(rows) {
    const summaryMap = new Map();
    rows.forEach((row) => {
      const key = `${row.accountId}::${row.processId || row.processName}`;
      const current = summaryMap.get(key) || {
        accountName: row.accountName,
        processName: row.processName,
        quantity: 0,
        totalPrice: 0,
      };
      current.quantity += row.quantity;
      current.totalPrice += row.totalPrice;
      summaryMap.set(key, current);
    });

    return Array.from(summaryMap.values()).sort((left, right) => {
      const accountOrder = left.accountName.localeCompare(right.accountName, "zh-CN");
      if (accountOrder) return accountOrder;
      return left.processName.localeCompare(right.processName, "zh-CN");
    });
  }

  function renderAdminQueryPagination(totalRows, currentPage, totalPages) {
    if (totalPages <= 1) return "";

    return `
      <div class="history-pagination admin-query-pagination">
        <button class="button button-secondary button-small" data-action="admin-query-page" data-page="${currentPage - 1}" type="button" ${currentPage === 1 ? "disabled" : ""}>上一页</button>
        <span>${currentPage} / ${totalPages}，共 ${totalRows} 条</span>
        <button class="button button-secondary button-small" data-action="admin-query-page" data-page="${currentPage + 1}" type="button" ${currentPage === totalPages ? "disabled" : ""}>下一页</button>
      </div>
    `;
  }

  function renderAdminQueryRow(row, previousRow, nextRow, dailyWageMap) {
    const shouldShowDate = !previousRow || previousRow.workDate !== row.workDate;
    const shouldShowDailyTotal = !nextRow || nextRow.workDate !== row.workDate;
    const dailyTotal = dailyWageMap.get(row.workDate) || 0;
    return `
      <tr>
        <td>${shouldShowDate ? escapeHtml(formatMonthDay(row.workDate)) : ""}</td>
        <td>${escapeHtml(row.processName)}</td>
        <td class="money-cell">${row.quantity.toFixed(2)}</td>
        <td class="money-cell">¥${row.totalPrice.toFixed(2)}</td>
      </tr>
      ${
        shouldShowDailyTotal
          ? `<tr class="admin-query-day-total-row"><td colspan="4"><span>总工资：<strong>¥${dailyTotal.toFixed(2)}</strong></span></td></tr>`
          : ""
      }
    `;
  }

  function formatMonthDay(value) {
    const parts = String(value || "").split("-");
    if (parts.length !== 3) return value || "";
    return `${parts[1]}-${parts[2]}`;
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

  function bindDateDisplayControls() {
    document.querySelectorAll(".date-query-input").forEach((input) => {
      const update = () => updateDateDisplay(input);
      input.addEventListener("change", update);
      input.addEventListener("input", update);
      update();
    });
  }

  function updateDateDisplay(input) {
    const control = input.closest(".date-query-control");
    const display = document.querySelector(`[data-date-display='${input.id}']`);
    if (!control || !display) return;

    control.classList.toggle("has-date", Boolean(input.value));
    display.innerHTML = input.value ? formatDateDisplay(input.value) : "";
  }

  function formatDateDisplay(value) {
    const parts = String(value).split("-");
    if (parts.length === 2) return `<span>${escapeHtml(parts[0])}</span><span>${escapeHtml(parts[1])}月</span>`;
    if (parts.length !== 3) return escapeHtml(value);
    return `<span>${escapeHtml(parts[0])}</span><span>${escapeHtml(parts[1])}-${escapeHtml(parts[2])}</span>`;
  }

  function bindLogout() {
    const logoutButton = document.querySelector("#logoutButton");
    if (!logoutButton) return;
    logoutButton.addEventListener("click", async () => {
      await logoutCurrentUser();
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
