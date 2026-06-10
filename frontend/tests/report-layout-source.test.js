const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const frontendRoot = path.resolve(__dirname, "..");
const appSource = fs.readFileSync(path.join(frontendRoot, "app.js"), "utf8");
const cssSource = fs.readFileSync(path.join(frontendRoot, "styles.css"), "utf8");

test("employee report quantity input uses decimal text entry instead of number spinners", () => {
  assert.match(appSource, /class="report-input report-quantity-input"[^>]+type="text"[^>]+inputmode="decimal"/);
  assert.doesNotMatch(appSource, /class="report-input report-quantity-input"[^>]+type="number"/);
});

test("employee report summary is a two-column pill group at the top", () => {
  const summaryIndex = appSource.indexOf('class="report-summary-bar report-top-summary"');
  const panelIndex = appSource.indexOf('class="panel report-panel"');

  assert.ok(summaryIndex > -1);
  assert.ok(panelIndex > summaryIndex);
  assert.match(appSource, /<span>当日工资：<\/span>/);
  assert.match(appSource, /<span>当月工资：<\/span>/);
  assert.match(cssSource, /\.report-top-summary\s*{[^}]+grid-template-columns:\s*1fr 1fr;/s);
  assert.match(cssSource, /\.report-summary-item\s*{[^}]+border-radius:\s*999px;/s);
});

test("employee report action buttons are full-height fixed bottom actions", () => {
  const panelIndex = appSource.indexOf('class="panel report-panel"');
  const actionIndex = appSource.indexOf('class="action-row report-bottom-actions"');
  const logoutIndex = appSource.indexOf('class="employee-logout-row"');

  assert.ok(actionIndex > panelIndex);
  assert.ok(logoutIndex > actionIndex);
  assert.match(cssSource, /\.report-action-button\s*{[^}]+min-height:\s*48px;/s);
});

test("employee report date row keeps height and shows monthly work days before right-aligned picker", () => {
  const workDaysIndex = appSource.indexOf('class="report-month-workdays"');
  const dateLabelIndex = appSource.indexOf('<label for="workDate">日期：</label>');
  const dateInputIndex = appSource.indexOf('class="input report-date-input"');

  assert.ok(workDaysIndex > -1);
  assert.ok(dateLabelIndex > workDaysIndex);
  assert.ok(dateInputIndex > dateLabelIndex);
  assert.match(appSource, /const monthWorkDays = Number\(monthSummary\?\.summary\?\.workDays\) \|\| 0;/);
  assert.match(appSource, /当月上班：<strong>\$\{monthWorkDays\}<\/strong>天/);
  assert.match(cssSource, /\.report-date-row\s*{[^}]+grid-template-columns:\s*minmax\(0, 1fr\) auto minmax\(132px, auto\);/s);
  assert.match(cssSource, /\.report-date-input\s*{[^}]+height:\s*38px;[^}]+justify-self:\s*end;/s);
  assert.match(cssSource, /\.report-month-workdays\s*{[^}]+height:\s*38px;/s);
});

test("login page redirects existing sessions without storing passwords", () => {
  assert.match(appSource, /await refreshCurrentUser\(\);/);
  assert.match(appSource, /\["\/", "\/login"\]\.includes\(path\) && currentUser/);
  assert.match(appSource, /navigate\(getDefaultRouteForUser\(currentUser\)\);/);
  assert.doesNotMatch(appSource, /localStorage\.setItem\([^)]*password/i);
  assert.doesNotMatch(appSource, /sessionStorage\.setItem\([^)]*password/i);
});

test("logout keeps server session for next device reopen", () => {
  const logoutStart = appSource.indexOf("async function logoutCurrentUser()");
  const logoutEnd = appSource.indexOf("function requireEmployee()", logoutStart);
  const logoutSource = appSource.slice(logoutStart, logoutEnd);

  assert.match(logoutSource, /clearCurrentUser\(\);/);
  assert.doesNotMatch(logoutSource, /apiRequest\("\/api\/auth\/logout"/);
});

test("saved report dates render only actual saved report rows", () => {
  assert.match(appSource, /const rows = hasSavedReport \? normalizeSavedReportRows\(report\.rows \|\| \[\]\) : normalizeReportRows\(processes, report\.rows \|\| \[\]\);/);
  assert.match(appSource, /function normalizeSavedReportRows\(savedRows\)/);
});
