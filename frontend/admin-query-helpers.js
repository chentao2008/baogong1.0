(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
    return;
  }

  root.AdminQueryHelpers = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function getProcessesForAdminQueryEmployee(processes, employees, employeeId) {
    if (!employeeId) return processes;

    const employee = employees.find((account) => account.id === employeeId);
    if (!employee) return [];

    const configuredProcessIds = new Set(employee.processIds || []);
    return processes.filter((process) => configuredProcessIds.has(process.id));
  }

  return {
    getProcessesForAdminQueryEmployee,
  };
});
