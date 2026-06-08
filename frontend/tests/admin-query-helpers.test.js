const assert = require("node:assert/strict");
const test = require("node:test");

const { getProcessesForAdminQueryEmployee } = require("../admin-query-helpers.js");

test("selected employee only sees configured processes in admin query", () => {
  const processes = [
    { id: "p-cut", name: "裁剪" },
    { id: "p-sew", name: "缝制" },
    { id: "p-pack", name: "包装" },
  ];
  const employees = [
    { id: "u-a", account: "alice", processIds: ["p-cut", "p-pack"] },
    { id: "u-b", account: "bob", processIds: ["p-sew"] },
  ];

  const visibleProcesses = getProcessesForAdminQueryEmployee(processes, employees, "u-b");

  assert.deepEqual(
    visibleProcesses.map((process) => process.id),
    ["p-sew"]
  );
});

test("admin query shows all processes before an employee is selected", () => {
  const processes = [
    { id: "p-cut", name: "裁剪" },
    { id: "p-sew", name: "缝制" },
  ];

  const visibleProcesses = getProcessesForAdminQueryEmployee(processes, [], "");

  assert.deepEqual(visibleProcesses, processes);
});
