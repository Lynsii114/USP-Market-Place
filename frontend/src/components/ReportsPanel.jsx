import React, { useEffect, useState } from "react";

const money = (value) =>
  `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// Reporting & Analytics tab (FR4.1 - FR4.5). All figures come from the backend
// (/admin/reports), which only counts completed orders and checks admin access.
function ReportsPanel({ apiUrl, adminId, showToast }) {
  const [period, setPeriod] = useState("daily");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [report, setReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfirmingExport, setIsConfirmingExport] = useState(false);

  const buildQuery = () => {
    const params = new URLSearchParams({ admin_id: adminId, period });
    if (fromDate) params.set("from", fromDate);
    if (toDate) params.set("to", toDate);
    return params.toString();
  };

  const loadReport = async (announce = false) => {
    if (fromDate && toDate && fromDate > toDate) {
      showToast("From date cannot be after To date.", "error");
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch(`${apiUrl}/admin/reports?${buildQuery()}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          response.status === 503
            ? "Marketplace database is unavailable. Start MySQL in XAMPP, then refresh the page."
            : data?.detail || "Unable to load report"
        );
      }
      setReport(data);
      if (announce) showToast("Report generated successfully.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load report", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, [period]);

  const exportPdf = async () => {
    setIsConfirmingExport(false);
    try {
      const response = await fetch(`${apiUrl}/admin/reports/pdf?${buildQuery()}`);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.detail || "Unable to export PDF");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `usp-sales-report-${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to export PDF", "error");
    }
  };

  const rows = report?.rows ?? [];
  const topItems = report?.top_items ?? [];

  return (
    <div className="reports-page">
      <div className="reports-header">
        <div>
          <p className="section-kicker">Marketplace analytics</p>
          <h2>Reports</h2>
          <span>Sales and orders from completed purchases.</span>
        </div>
        <button type="button" className="auth-submit" onClick={() => setIsConfirmingExport(true)}>
          Export PDF
        </button>
      </div>

      <div className="report-filter">
        <label>
          Group by
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        <label>
          From
          <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
        </label>
        <button type="button" className="secondary-button" onClick={() => loadReport(true)} disabled={isLoading}>
          {isLoading ? "Loading..." : "Generate Report"}
        </button>
      </div>

      <div className="summary-grid">
        <div className="summary-card">
          <span>Total Orders</span>
          <h3>{report?.total_orders ?? 0}</h3>
        </div>
        <div className="summary-card">
          <span>Items Sold</span>
          <h3>{report?.total_items_sold ?? 0}</h3>
        </div>
        <div className="summary-card">
          <span>Average Order</span>
          <h3>{money(report?.average_order_value)}</h3>
        </div>
        <div className="summary-card revenue-card">
          <span>Total Revenue</span>
          <h3>{money(report?.total_sales)}</h3>
        </div>
      </div>

      <div className="report-sections">
        <div className="report-box">
          <h3>Top-selling items</h3>
          {topItems.length ? (
            topItems.map((item, index) => (
              <div className="status-row" key={`${item.item_name}-${index}`}>
                <span>
                  {index + 1}. {item.item_name}
                </span>
                <strong>
                  {item.units_sold} sold · {money(item.revenue)}
                </strong>
              </div>
            ))
          ) : (
            <p className="empty-state">No completed orders in this range.</p>
          )}
        </div>

        <div className="report-box">
          <h3>Sales by {period === "daily" ? "day" : period === "weekly" ? "week" : "month"}</h3>
          {rows.length ? (
            rows.slice(0, 8).map((row) => (
              <div className="status-row" key={row.date}>
                <span>{row.date}</span>
                <strong>
                  {row.orders} orders · {money(row.total_sales)}
                </strong>
              </div>
            ))
          ) : (
            <p className="empty-state">No completed orders in this range.</p>
          )}
          {rows.length > 8 && <p className="empty-state">Showing latest 8 of {rows.length}. The PDF lists all.</p>}
        </div>
      </div>

      {isConfirmingExport && (
        <div className="auth-modal-backdrop" onClick={() => setIsConfirmingExport(false)}>
          <div className="report-confirm-modal" onClick={(event) => event.stopPropagation()}>
            <h3>Download Sales Report?</h3>
            <p>Your browser will save the report for the selected date range as a PDF.</p>
            <div className="checkout-actions">
              <button type="button" className="secondary-button" onClick={() => setIsConfirmingExport(false)}>
                Cancel
              </button>
              <button type="button" className="auth-submit" onClick={exportPdf}>
                Confirm Download
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReportsPanel;
