const assert = require("node:assert/strict");
const test = require("node:test");

const {
  getNextReportSwipeDate,
  getPreviousReportedDate,
} = require("../report-swipe-helpers.js");

test("right swipe goes to the nearest earlier reported date", () => {
  const historyRows = [
    { workDate: "2026-06-01" },
    { workDate: "2026-06-05" },
    { workDate: "2026-06-07" },
  ];

  assert.equal(getPreviousReportedDate(historyRows, "2026-06-06"), "2026-06-05");
});

test("left swipe goes to the nearest later reported date before today", () => {
  const historyRows = [
    { workDate: "2026-06-01" },
    { workDate: "2026-06-05" },
    { workDate: "2026-06-07" },
  ];

  assert.equal(getNextReportSwipeDate(historyRows, "2026-06-05", "2026-06-08"), "2026-06-07");
});

test("left swipe falls through to today when no later report exists", () => {
  const historyRows = [{ workDate: "2026-06-01" }, { workDate: "2026-06-07" }];

  assert.equal(getNextReportSwipeDate(historyRows, "2026-06-07", "2026-06-08"), "2026-06-08");
});

test("left swipe from today has no target", () => {
  const historyRows = [{ workDate: "2026-06-01" }, { workDate: "2026-06-08" }];

  assert.equal(getNextReportSwipeDate(historyRows, "2026-06-08", "2026-06-08"), "");
});

test("left swipe does not duplicate today when today is already reported", () => {
  const historyRows = [{ workDate: "2026-06-05" }, { workDate: "2026-06-08" }];

  assert.equal(getNextReportSwipeDate(historyRows, "2026-06-05", "2026-06-08"), "2026-06-08");
});
