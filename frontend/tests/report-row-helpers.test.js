const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildFixedReportRows,
  getSubmittableReportRows,
} = require("../report-row-helpers.js");

test("fixed report rows follow configured process order and merge saved quantities", () => {
  const processes = [
    { id: "p-cut", name: "裁剪", price: 1.5 },
    { id: "p-sew", name: "缝制", price: 2 },
    { id: "p-pack", name: "包装", price: 0.8 },
  ];
  const savedRows = [
    { processId: "p-pack", processName: "包装", unitPrice: 0.8, quantity: 12 },
    { processId: "p-cut", processName: "裁剪", unitPrice: 1.5, quantity: 3 },
  ];

  const rows = buildFixedReportRows(processes, savedRows);

  assert.deepEqual(
    rows.map((row) => [row.processId, row.processName, row.unitPrice, row.quantity]),
    [
      ["p-cut", "裁剪", 1.5, "3"],
      ["p-sew", "缝制", 2, ""],
      ["p-pack", "包装", 0.8, "12"],
    ]
  );
});

test("submittable report rows exclude empty and zero quantities", () => {
  const rows = [
    { processId: "p-cut", processName: "裁剪", unitPrice: 1.5, quantity: "3" },
    { processId: "p-sew", processName: "缝制", unitPrice: 2, quantity: "" },
    { processId: "p-pack", processName: "包装", unitPrice: 0.8, quantity: "0" },
  ];

  assert.deepEqual(getSubmittableReportRows(rows), [
    { process_id: "p-cut", quantity: 3 },
  ]);
});
