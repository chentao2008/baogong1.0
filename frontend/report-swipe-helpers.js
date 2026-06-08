(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
    return;
  }

  root.ReportSwipeHelpers = factory();
})(typeof window !== "undefined" ? window : typeof globalThis !== "undefined" ? globalThis : this, function () {
  function getReportedDates(historyRows) {
    return Array.from(
      new Set(
        historyRows
          .map((row) => row.workDate || row.work_date || "")
          .filter(Boolean)
      )
    );
  }

  function getPreviousReportedDate(historyRows, currentDate) {
    const reportDates = getReportedDates(historyRows)
      .filter((workDate) => workDate < currentDate)
      .sort((left, right) => right.localeCompare(left));

    return reportDates[0] || "";
  }

  function getNextReportSwipeDate(historyRows, currentDate, today) {
    if (currentDate >= today) return "";

    const reportDates = getReportedDates(historyRows)
      .filter((workDate) => workDate > currentDate)
      .sort((left, right) => left.localeCompare(right));

    return reportDates[0] || today;
  }

  return {
    getNextReportSwipeDate,
    getPreviousReportedDate,
  };
});
