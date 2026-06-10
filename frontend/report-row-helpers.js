(function () {
  function normalizeQuantity(quantity) {
    if (quantity === null || quantity === undefined || quantity === "") return "";
    return String(quantity);
  }

  function buildFixedReportRows(processes, savedRows) {
    const savedByProcessId = new Map(
      (savedRows || [])
        .filter((row) => row.processId)
        .map((row) => [row.processId, row])
    );

    return (processes || []).map((process) => {
      const saved = savedByProcessId.get(process.id) || {};
      return {
        processId: process.id,
        processName: process.name,
        unitPrice: Number(process.price) || Number(saved.unitPrice) || 0,
        quantity: normalizeQuantity(saved.quantity),
      };
    });
  }

  function getSubmittableReportRows(rows) {
    return (rows || [])
      .filter((row) => row.processId && Number(row.quantity) > 0)
      .map((row) => ({
        process_id: row.processId,
        quantity: Number(row.quantity),
      }));
  }

  const helpers = {
    buildFixedReportRows,
    getSubmittableReportRows,
  };

  if (typeof window !== "undefined") {
    window.ReportRowHelpers = helpers;
  }

  if (typeof module !== "undefined") {
    module.exports = helpers;
  }
})();
