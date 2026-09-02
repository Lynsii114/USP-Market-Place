import React, { useEffect, useMemo, useState } from "react";

const adminTabs = ["Dashboard", "Students", "Listings", "Orders", "Reports"];

function AdminDashboard({ apiUrl, currentUser, logo, onLogin, onLogout, onMarketplace, showToast }) {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [listings, setListings] = useState([]);
  const [orders, setOrders] = useState([]);
  const [report, setReport] = useState(null);
  const [studentSearch, setStudentSearch] = useState("");
  const [listingSearch, setListingSearch] = useState("");
  const [orderSearch, setOrderSearch] = useState("");
  const [orderStatus, setOrderStatus] = useState("");
  const [orderDate, setOrderDate] = useState("");
  const [reportPeriod, setReportPeriod] = useState("daily");
  const [isLoading, setIsLoading] = useState(false);
  const [isConfirmingReport, setIsConfirmingReport] = useState(false);

  const isAdmin = currentUser?.role === "admin";
  const adminId = currentUser?.id;

  const parseResponse = async (response, fallbackMessage) => {
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data?.detail || fallbackMessage);
    }
    return data;
  };

  const fetchAdmin = async (path, fallbackMessage, options = {}) => {
    const joiner = path.includes("?") ? "&" : "?";
    const response = await fetch(`${apiUrl}${path}${joiner}admin_id=${adminId}`, options);
    return parseResponse(response, fallbackMessage);
  };

  const loadDashboard = async () => {
    const data = await fetchAdmin("/admin/dashboard", "Unable to load dashboard");
    setDashboard(data);
  };

  const loadStudents = async () => {
    const data = await fetchAdmin(`/admin/students?search=${encodeURIComponent(studentSearch)}`, "Unable to load students");
    setStudents(data);
  };

  const loadListings = async () => {
    const data = await fetchAdmin(`/admin/listings?search=${encodeURIComponent(listingSearch)}`, "Unable to load listings");
    setListings(data);
  };

  const loadOrders = async () => {
    const params = new URLSearchParams({
      search: orderSearch,
      status: orderStatus,
      order_date: orderDate,
    });
    const data = await fetchAdmin(`/admin/orders?${params.toString()}`, "Unable to load orders");
    setOrders(data);
  };

  const loadReport = async () => {
    const data = await fetchAdmin(`/admin/reports?period=${reportPeriod}`, "Unable to load reports");
    setReport(data);
  };

  const refreshActiveTab = async () => {
    if (!isAdmin) {
      return;
    }

    setIsLoading(true);
    try {
      if (activeTab === "Dashboard") {
        await loadDashboard();
      } else if (activeTab === "Students") {
        await loadStudents();
      } else if (activeTab === "Listings") {
        await loadListings();
      } else if (activeTab === "Orders") {
        await loadOrders();
      } else if (activeTab === "Reports") {
        await loadReport();
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load admin data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshActiveTab();
  }, [activeTab, isAdmin, reportPeriod]);

  const stats = useMemo(
    () => [
      ["Total Students", dashboard?.total_students ?? 0],
      ["Active Listings", dashboard?.total_active_listings ?? 0],
      ["Total Orders", dashboard?.total_orders ?? 0],
      ["Today's Sales", `$${Number(dashboard?.todays_sales ?? 0).toFixed(2)}`],
    ],
    [dashboard]
  );

  const formatDate = (value) =>
    value
      ? new Date(value).toLocaleString([], {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "Not recorded";

  const updateStudentStatus = async (student, action) => {
    const verb = action === "suspend" ? "suspend" : "reactivate";
    if (!window.confirm(`Are you sure you want to ${verb} ${student.username}?`)) {
      return;
    }

    setIsLoading(true);
    try {
      await fetchAdmin(`/admin/students/${student.id}/${action}`, `Unable to ${verb} student`, { method: "POST" });
      await loadStudents();
      showToast(`Student ${action === "suspend" ? "suspended" : "reactivated"} successfully.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : `Unable to ${verb} student`);
    } finally {
      setIsLoading(false);
    }
  };

  const removeListing = async (listing) => {
    const reason = window.prompt(`Reason for removing "${listing.name}"`);
    if (!reason) {
      return;
    }

    setIsLoading(true);
    try {
      await fetchAdmin(`/admin/listings/${listing.id}/remove`, "Unable to remove listing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      await loadListings();
      showToast("Listing removed from student view.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to remove listing");
    } finally {
      setIsLoading(false);
    }
  };

  const restoreListing = async (listing) => {
    if (!window.confirm(`Restore "${listing.name}" to the marketplace?`)) {
      return;
    }

    setIsLoading(true);
    try {
      await fetchAdmin(`/admin/listings/${listing.id}/restore`, "Unable to restore listing", { method: "POST" });
      await loadListings();
      showToast("Listing restored successfully.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to restore listing");
    } finally {
      setIsLoading(false);
    }
  };

  const createReportPdf = () => {
    const rows = report?.rows ?? [];
    const clean = (value) => String(value).replace(/[^\x20-\x7E]/g, "?").replace(/[\\()]/g, "\\$&");
    const commands = [];
    const addText = (text, x, y, size = 10, font = "F1", color = "0.08 0.14 0.22") => {
      commands.push(`${color} rg BT /${font} ${size} Tf ${x} ${y} Td (${clean(text)}) Tj ET`);
    };
    const addLine = (x1, y1, x2, y2) => commands.push(`0.84 0.88 0.93 RG ${x1} ${y1} m ${x2} ${y2} l S`);

    commands.push("0.05 0.18 0.30 rg 40 710 532 52 re f");
    addText("USP", 58, 730, 18, "F2", "1 1 1");
    addText("USP MARKETPLACE ADMIN REPORT", 112, 736, 14, "F2", "1 1 1");
    addText(`Period: ${reportPeriod}`, 112, 720, 10, "F1", "1 1 1");
    addText(`Generated: ${new Date().toLocaleString()}`, 350, 720, 8, "F1", "1 1 1");
    addText(`Total Orders: ${report?.total_orders ?? 0}`, 44, 676, 11, "F2");
    addText(`Items Sold: ${report?.total_items_sold ?? 0}`, 230, 676, 11, "F2");
    addText(`Total Sales: $${Number(report?.total_sales ?? 0).toFixed(2)}`, 405, 676, 11, "F2");
    addLine(40, 650, 572, 650);
    addText("Date", 44, 628, 9, "F2");
    addText("Orders", 225, 628, 9, "F2");
    addText("Items Sold", 335, 628, 9, "F2");
    addText("Total Sales", 465, 628, 9, "F2");
    addLine(40, 618, 572, 618);

    let y = 598;
    rows.slice(0, 22).forEach((row) => {
      addText(row.date, 44, y);
      addText(String(row.orders), 225, y);
      addText(String(row.items_sold), 335, y);
      addText(`$${Number(row.total_sales).toFixed(2)}`, 465, y);
      addLine(40, y - 12, 572, y - 12);
      y -= 24;
    });

    addText("USP Marketplace | Admin Office | Laucala Campus", 44, 44, 8);
    const textCommands = commands.join("\n");
    const objects = [
      "<< /Type /Catalog /Pages 2 0 R >>",
      "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
      `<< /Length ${textCommands.length} >>\nstream\n${textCommands}\nendstream`,
    ];
    let pdf = "%PDF-1.4\n";
    const offsets = [0];
    objects.forEach((object, index) => {
      offsets.push(pdf.length);
      pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });
    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    offsets.slice(1).forEach((offset) => {
      pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
    });
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

    const blob = new Blob([pdf], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `usp-marketplace-admin-report-${Date.now()}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setIsConfirmingReport(false);
  };

  if (!isAdmin) {
    return (
      <main className="admin-shell">
        <section className="admin-access-panel">
          <img src={logo} alt="USP logo" />
          <h1>Admin Access Required</h1>
          <p>Only active USP Marketplace administrators can open this dashboard.</p>
          <div className="admin-access-actions">
            <button type="button" className="auth-submit" onClick={onLogin}>
              Admin Login
            </button>
            <button type="button" className="secondary-button" onClick={onMarketplace}>
              Back to Marketplace
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <img src={logo} alt="USP logo" />
          <div>
            <strong>USP Marketplace</strong>
            <span>Administrator</span>
          </div>
        </div>
        <nav className="admin-nav">
          {adminTabs.map((tab) => (
            <button
              type="button"
              className={activeTab === tab ? "active" : ""}
              key={tab}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>
        <button type="button" className="admin-logout" onClick={onLogout}>
          Logout
        </button>
      </aside>

      <section className="admin-content">
        <div className="admin-topbar">
          <div>
            <span className="section-kicker">Admin Panel</span>
            <h1>{activeTab}</h1>
          </div>
          <button type="button" className="secondary-button" onClick={onMarketplace}>
            Marketplace
          </button>
        </div>

        {isLoading && <p className="admin-loading">Loading admin data...</p>}

        {activeTab === "Dashboard" && (
          <>
            <div className="admin-stat-grid">
              {stats.map(([label, value]) => (
                <div className="admin-stat-card" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <div className="admin-table-card">
              <h2>Recent Orders</h2>
              <AdminOrdersTable orders={dashboard?.recent_orders ?? []} formatDate={formatDate} />
            </div>
          </>
        )}

        {activeTab === "Students" && (
          <div className="admin-table-card">
            <AdminSearch value={studentSearch} onChange={setStudentSearch} onSearch={loadStudents} placeholder="Search name or email" />
            <div className="admin-table">
              <div className="admin-table-head students-grid">
                <span>Student ID</span>
                <span>Name</span>
                <span>Email</span>
                <span>Status</span>
                <span>Registered</span>
                <span>Action</span>
              </div>
              {students.map((student) => (
                <div className="admin-table-row students-grid" key={student.id}>
                  <span>{student.id}</span>
                  <strong>{student.username}</strong>
                  <span>{student.email}</span>
                  <span className={`status-pill ${student.status}`}>{student.status}</span>
                  <span>{formatDate(student.created_at)}</span>
                  <button
                    type="button"
                    className={student.status === "suspended" ? "secondary-button" : "danger-outline-button"}
                    onClick={() => updateStudentStatus(student, student.status === "suspended" ? "reactivate" : "suspend")}
                  >
                    {student.status === "suspended" ? "Reactivate" : "Suspend"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "Listings" && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <AdminSearch value={listingSearch} onChange={setListingSearch} onSearch={loadListings} placeholder="Search listing, seller, or category" />
              <span className="admin-record-count">
                {listings.length} {listings.length === 1 ? "listing" : "listings"}
              </span>
            </div>
            <div className="admin-table">
              <div className="admin-table-head listings-grid">
                <span>Item</span>
                <span>Seller</span>
                <span>Category</span>
                <span>Price</span>
                <span>Stock</span>
                <span>Status</span>
                <span>Date</span>
                <span>Action</span>
              </div>
              {listings.length ? (
                listings.map((listing) => (
                  <div className="admin-table-row admin-listing-row listings-grid" key={listing.id}>
                    <div className="admin-listing-name">
                      {listing.photo ? <img src={listing.photo} alt={listing.name} /> : <span>{listing.category?.charAt(0) || "I"}</span>}
                      <div>
                        <strong>{listing.name}</strong>
                        <small>Listing #{listing.id}</small>
                      </div>
                    </div>
                    <div className="admin-listing-meta">
                      <strong>{listing.seller_username}</strong>
                      <small>{listing.contact || "No contact listed"}</small>
                    </div>
                    <span className="admin-category-pill">{listing.category}</span>
                    <strong className="admin-money">${Number(listing.price).toFixed(2)}</strong>
                    <span className={`stock-pill ${Number(listing.stock) <= 0 ? "empty" : ""}`}>
                      {Number(listing.stock)} {Number(listing.stock) === 1 ? "unit" : "units"}
                    </span>
                    <span className={`status-pill ${listing.status}`}>{listing.status}</span>
                    <time dateTime={listing.created_at}>{formatDate(listing.created_at)}</time>
                    <div className="admin-row-actions">
                      {listing.status === "removed" ? (
                        <button type="button" className="secondary-button" onClick={() => restoreListing(listing)}>
                          Restore
                        </button>
                      ) : (
                        <button type="button" className="danger-outline-button" onClick={() => removeListing(listing)}>
                          Remove
                        </button>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <p className="empty-state">No listings found.</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "Orders" && (
          <div className="admin-table-card">
            <div className="admin-filters">
              <input value={orderSearch} onChange={(event) => setOrderSearch(event.target.value)} placeholder="Order ID, buyer, seller, or item" />
              <input type="date" value={orderDate} onChange={(event) => setOrderDate(event.target.value)} />
              <select value={orderStatus} onChange={(event) => setOrderStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="completed">Completed</option>
              </select>
              <button type="button" className="auth-submit" onClick={loadOrders}>
                Search
              </button>
            </div>
            <AdminOrdersTable orders={orders} formatDate={formatDate} />
          </div>
        )}

        {activeTab === "Reports" && (
          <div className="admin-table-card">
            <div className="admin-filters">
              <select value={reportPeriod} onChange={(event) => setReportPeriod(event.target.value)}>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
              <button type="button" className="auth-submit" onClick={() => setIsConfirmingReport(true)}>
                Export PDF
              </button>
            </div>
            <div className="admin-stat-grid compact">
              <div className="admin-stat-card">
                <span>Total Orders</span>
                <strong>{report?.total_orders ?? 0}</strong>
              </div>
              <div className="admin-stat-card">
                <span>Total Items Sold</span>
                <strong>{report?.total_items_sold ?? 0}</strong>
              </div>
              <div className="admin-stat-card">
                <span>Total Revenue</span>
                <strong>${Number(report?.total_sales ?? 0).toFixed(2)}</strong>
              </div>
            </div>
            <div className="admin-table">
              <div className="admin-table-head reports-grid">
                <span>Date</span>
                <span>Orders</span>
                <span>Items Sold</span>
                <span>Total Sales</span>
              </div>
              {(report?.rows ?? []).map((row) => (
                <div className="admin-table-row reports-grid" key={row.date}>
                  <strong>{row.date}</strong>
                  <span>{row.orders}</span>
                  <span>{row.items_sold}</span>
                  <span>${Number(row.total_sales).toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {isConfirmingReport && (
        <div className="auth-modal-backdrop" onClick={() => setIsConfirmingReport(false)}>
          <div className="report-confirm-modal" onClick={(event) => event.stopPropagation()}>
            <h3>Download Admin Report?</h3>
            <p>Your browser will save the selected admin report as a PDF.</p>
            <div className="checkout-actions">
              <button type="button" className="secondary-button" onClick={() => setIsConfirmingReport(false)}>
                Cancel
              </button>
              <button type="button" className="auth-submit" onClick={createReportPdf}>
                Confirm Download
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function AdminSearch({ value, onChange, onSearch, placeholder }) {
  return (
    <div className="admin-filters">
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      <button type="button" className="auth-submit" onClick={onSearch}>
        Search
      </button>
    </div>
  );
}

function AdminOrdersTable({ orders, formatDate }) {
  if (!orders.length) {
    return <p className="empty-state">No records found.</p>;
  }

  return (
    <div className="admin-table">
      <div className="admin-table-head orders-grid">
        <span>Order ID</span>
        <span>Buyer</span>
        <span>Seller</span>
        <span>Item</span>
        <span>Qty</span>
        <span>Total</span>
        <span>Date</span>
        <span>Status</span>
      </div>
      {orders.map((order) => (
        <div className="admin-table-row orders-grid" key={order.id}>
          <strong>#{order.id}</strong>
          <span>{order.buyer_username}</span>
          <span>{order.seller_username}</span>
          <span>{order.item_name}</span>
          <span>{order.quantity}</span>
          <span>${Number(order.total_amount || order.price).toFixed(2)}</span>
          <span>{formatDate(order.purchased_at)}</span>
          <span className={`status-pill ${order.status}`}>{order.status}</span>
        </div>
      ))}
    </div>
  );
}

export default AdminDashboard;
