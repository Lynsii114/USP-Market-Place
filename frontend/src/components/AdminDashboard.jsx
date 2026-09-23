import React, { useEffect, useMemo, useState } from "react";

const adminTabs = ["Dashboard", "Students", "Listings", "Orders", "Reports", "Flags", "Reviews"];

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
  const [reportFromDate, setReportFromDate] = useState("");
  const [reportToDate, setReportToDate] = useState("");
  const [reportOrders, setReportOrders] = useState([]);
  const [reportListings, setReportListings] = useState([]);
  const [userReports, setUserReports] = useState([]);
  const [ratingReviews, setRatingReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfirmingReport, setIsConfirmingReport] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [isNotificationPanelOpen, setIsNotificationPanelOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [selectedAdminListing, setSelectedAdminListing] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [openStudentActionId, setOpenStudentActionId] = useState(null);
  const [openListingActionId, setOpenListingActionId] = useState(null);

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
    const [reportData, ordersData, listingsData] = await Promise.all([
      fetchAdmin(`/admin/reports?period=${reportPeriod}`, "Unable to load reports"),
      fetchAdmin("/admin/orders", "Unable to load report orders"),
      fetchAdmin("/admin/listings", "Unable to load report listings"),
    ]);
    setReport(reportData);
    setReportOrders(ordersData);
    setReportListings(listingsData);
  };

  const loadNotifications = async () => {
    const data = await fetchAdmin("/admin/notifications", "Unable to load notifications");
    setNotifications(data);
  };

  const loadUserReports = async () => {
    const data = await fetchAdmin("/admin/user-reports", "Unable to load user reports");
    setUserReports(data);
  };

  const loadRatingReviews = async () => {
    const data = await fetchAdmin("/admin/ratings", "Unable to load ratings and reviews");
    setRatingReviews(data);
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
      } else if (activeTab === "Flags") {
        await loadUserReports();
      } else if (activeTab === "Reviews") {
        await loadRatingReviews();
      }
      await loadNotifications();
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load admin data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshActiveTab();
  }, [activeTab, isAdmin, reportPeriod]);

  useEffect(() => {
    if (isAdmin) {
      loadNotifications().catch(() => {});
    }
  }, [isAdmin]);

  const stats = useMemo(
    () => [
      ["Total Students", dashboard?.total_students ?? 0],
      ["Active Listings", dashboard?.total_active_listings ?? 0],
      ["Total Orders", dashboard?.total_orders ?? 0],
      ["Today's Sales", `$${Number(dashboard?.todays_sales ?? 0).toFixed(2)}`],
    ],
    [dashboard]
  );

  const filteredReportOrders = useMemo(() => {
    const fromTime = reportFromDate ? new Date(`${reportFromDate}T00:00:00`).getTime() : null;
    const toTime = reportToDate ? new Date(`${reportToDate}T23:59:59`).getTime() : null;

    return reportOrders.filter((order) => {
      if (!order.purchased_at) {
        return false;
      }

      const orderTime = new Date(order.purchased_at).getTime();
      return (fromTime === null || orderTime >= fromTime) && (toTime === null || orderTime <= toTime);
    });
  }, [reportOrders, reportFromDate, reportToDate]);

  const reportSummary = useMemo(() => {
    const useReportTotals = !reportFromDate && !reportToDate && reportOrders.length === 0;
    const totalRevenue = filteredReportOrders.reduce(
      (total, order) => total + Number(order.total_amount || order.price || 0),
      0
    );
    const itemsSold = filteredReportOrders.reduce((total, order) => total + Number(order.quantity || 1), 0);
    const completedOrders = filteredReportOrders.filter((order) => order.status === "completed").length;

    return {
      totalSales: useReportTotals ? report?.total_orders ?? 0 : completedOrders,
      totalOrders: useReportTotals ? report?.total_orders ?? 0 : filteredReportOrders.length,
      itemsSold: useReportTotals ? report?.total_items_sold ?? 0 : itemsSold,
      revenue: useReportTotals ? Number(report?.total_sales ?? 0) : totalRevenue,
    };
  }, [filteredReportOrders, report, reportFromDate, reportOrders.length, reportToDate]);

  const orderStatusSummary = useMemo(
    () => ({
      completed: filteredReportOrders.filter((order) => order.status === "completed").length,
      pending: filteredReportOrders.filter((order) => order.status === "pending").length,
      cancelled: filteredReportOrders.filter((order) => ["cancelled", "canceled"].includes(order.status)).length,
    }),
    [filteredReportOrders]
  );

  const listingSummary = useMemo(
    () => ({
      active: reportListings.filter((listing) => listing.status === "available").length,
      sold: reportListings.filter((listing) => listing.status === "sold").length,
      removed: reportListings.filter((listing) => listing.status === "removed").length,
    }),
    [reportListings]
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

  const openUserProfile = (user) => {
    if (!user) {
      showToast("Profile details are not available for this user.");
      return;
    }
    setSelectedStudent(user);
  };

  const unreadNotifications = notifications.filter((notification) => !notification.is_read);

  const openNotification = async (notification) => {
    setSelectedNotification(notification);
    if (notification.is_read) {
      return;
    }

    setNotifications((currentNotifications) =>
      currentNotifications.map((currentNotification) =>
        currentNotification.id === notification.id
          ? { ...currentNotification, is_read: true }
          : currentNotification
      )
    );

    try {
      const updatedNotification = await fetchAdmin(`/admin/notifications/${notification.id}/view`, "Unable to mark notification as viewed", {
        method: "POST",
      });
      setSelectedNotification(updatedNotification);
      setNotifications((currentNotifications) =>
        currentNotifications.map((currentNotification) =>
          currentNotification.id === updatedNotification.id ? updatedNotification : currentNotification
        )
      );
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to mark notification as viewed");
    }
  };

  const removeNotification = async (notificationId) => {
    try {
      await fetchAdmin(`/admin/notifications/${notificationId}/view`, "Unable to remove notification", {
        method: "DELETE",
      });
      setNotifications((currentNotifications) =>
        currentNotifications.filter((notification) => notification.id !== notificationId)
      );
      if (selectedNotification?.id === notificationId) {
        setSelectedNotification(null);
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to remove notification");
    }
  };

  const updateStudentStatus = async (student, action) => {
    const verb = action === "suspend" ? "suspend" : "reactivate";
    if (!window.confirm(`Are you sure you want to ${verb} ${student.username}?`)) {
      return;
    }

    setIsLoading(true);
    try {
      const data = await fetchAdmin(`/admin/students/${student.id}/${action}`, `Unable to ${verb} student`, { method: "POST" });
      const notificationMessage =
        data?.message || `${student.username} was ${action === "suspend" ? "suspended" : "reactivated"}. Email notification sent.`;
      await loadStudents();
      await loadNotifications();
      if (selectedStudent?.id === student.id && data?.user) {
        setSelectedStudent(data.user);
      }
      setOpenStudentActionId(null);
      showToast(`${student.username} ${action === "suspend" ? "suspended" : "reactivated"}. ${notificationMessage}`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : `Unable to ${verb} student`);
    } finally {
      setIsLoading(false);
    }
  };

  const moderateListing = async (listing, action) => {
    const verb = action === "hide" ? "hiding" : "removing";
    const reason = window.prompt(`Reason for ${verb} "${listing.name}"`);
    if (!reason) {
      return;
    }

    setIsLoading(true);
    try {
      await fetchAdmin(`/admin/listings/${listing.id}/${action}`, `Unable to ${action} listing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      await loadListings();
      await loadNotifications();
      setOpenListingActionId(null);
      showToast(action === "hide" ? "Listing hidden from the marketplace." : "Listing removed from student view.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : `Unable to ${action} listing`);
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
      await loadNotifications();
      setOpenListingActionId(null);
      showToast("Listing restored successfully.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to restore listing");
    } finally {
      setIsLoading(false);
    }
  };

  const deleteStudentPermanently = async (student) => {
    const confirmed = window.confirm(
      `Permanently delete ${student.username}? This removes the student account and all listings created by this student.`
    );
    if (!confirmed) {
      return;
    }

    setIsLoading(true);
    try {
      const data = await fetchAdmin(`/admin/students/${student.id}`, "Unable to delete student", { method: "DELETE" });
      await loadStudents();
      await loadNotifications();
      if (selectedStudent?.id === student.id) {
        setSelectedStudent(null);
      }
      setOpenStudentActionId(null);
      showToast(data.message || "Student permanently deleted.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to delete student");
    } finally {
      setIsLoading(false);
    }
  };

  const generateReport = async () => {
    if (reportFromDate && reportToDate && reportFromDate > reportToDate) {
      showToast("From date cannot be after To date.");
      return;
    }

    await loadReport();
    showToast("Report generated successfully.");
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
    addText("USP BUY & SELL ADMIN REPORT", 112, 736, 14, "F2", "1 1 1");
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

    addText("USP Buy & Sell | Admin Office | Laucala Campus", 44, 44, 8);
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
    link.download = `usp-buy-sell-admin-report-${Date.now()}.pdf`;
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
          <p>Only active USP Buy & Sell administrators can open this dashboard.</p>
          <div className="admin-access-actions">
            <button type="button" className="auth-submit" onClick={onLogin}>
              Admin Login
            </button>
            <button type="button" className="secondary-button" onClick={onMarketplace}>
              Back to USP Buy & Sell
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
            <strong>USP Buy & Sell</strong>
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
          <div className="admin-topbar-actions">
            <div className="notification-popover-anchor">
              <button
                type="button"
                className="icon-nav-button notification-icon-button"
                onClick={() => setIsNotificationPanelOpen((isOpen) => !isOpen)}
                aria-label="Notifications"
                aria-expanded={isNotificationPanelOpen}
              >
                <span aria-hidden="true">&#128276;</span>
                {unreadNotifications.length > 0 && <span className="notification-count">{unreadNotifications.length}</span>}
              </button>
              {isNotificationPanelOpen && (
                <div className="notification-center-modal">
                  <div className="notification-center-header">
                    <div>
                      <span className="section-kicker">Admin notifications</span>
                      <h3>Notifications</h3>
                    </div>
                    <button
                      type="button"
                      className="close-button"
                      onClick={() => setIsNotificationPanelOpen(false)}
                      aria-label="Close notifications"
                    >
                      x
                    </button>
                  </div>
                  <div className="notification-center-summary">
                    <span>{notifications.length} total</span>
                    <span>{unreadNotifications.length} unread</span>
                  </div>
                  <div className="notification-center-list">
                    {notifications.length ? (
                      notifications.map((notification) => (
                        <div className={notification.is_read ? "notification-row viewed" : "notification-row unread"} key={notification.id}>
                          <button
                            type="button"
                            className="notification-item"
                            onClick={() => {
                              setIsNotificationPanelOpen(false);
                              openNotification(notification);
                            }}
                          >
                            <span>{notification.title}</span>
                            <small>{notification.is_read ? "Viewed" : "New"}</small>
                            <p>{notification.message}</p>
                            <time dateTime={notification.created_at}>{formatDate(notification.created_at)}</time>
                          </button>
                          <button
                            type="button"
                            className="notification-remove-button"
                            onClick={() => removeNotification(notification.id)}
                            aria-label="Remove notification"
                          >
                            x
                          </button>
                        </div>
                      ))
                    ) : (
                      <p className="empty-state">No admin notifications yet.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
            <button type="button" className="secondary-button" onClick={onMarketplace}>
              USP Buy & Sell
            </button>
          </div>
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
              <AdminOrdersTable orders={dashboard?.recent_orders ?? []} formatDate={formatDate} onViewProfile={openUserProfile} />
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
                <span>Actions</span>
              </div>
              {students.map((student) => (
                <div className="admin-table-row students-grid" key={student.id}>
                  <span>{student.id}</span>
                  <button type="button" className="profile-name-button" onClick={() => openUserProfile(student)}>
                    {student.username}
                  </button>
                  <span>{student.email}</span>
                  <span className={`status-pill ${student.status}`}>{student.status}</span>
                  <span>{formatDate(student.created_at)}</span>
                  <div className="admin-action-dropdown">
                    <button
                      type="button"
                      className="admin-action-trigger"
                      onClick={() =>
                        setOpenStudentActionId((currentId) => (currentId === student.id ? null : student.id))
                      }
                      aria-expanded={openStudentActionId === student.id}
                    >
                      Actions
                    </button>
                    {openStudentActionId === student.id && (
                      <div className="admin-action-menu">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedStudent(student);
                            setOpenStudentActionId(null);
                          }}
                        >
                          View
                        </button>
                        {student.status === "suspended" ? (
                          <button type="button" onClick={() => updateStudentStatus(student, "reactivate")}>
                            Reactivate
                          </button>
                        ) : (
                          <button type="button" onClick={() => updateStudentStatus(student, "suspend")}>
                            Suspend
                          </button>
                        )}
                        <div className="admin-action-divider" />
                        <button type="button" className="danger-action" onClick={() => deleteStudentPermanently(student)}>
                          Delete Permanently
                        </button>
                      </div>
                    )}
                  </div>
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
                <span>Actions</span>
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
                      <button type="button" className="profile-name-button" onClick={() => openUserProfile(listing.seller)}>
                        {listing.seller_username}
                      </button>
                      <small>{listing.contact || "No contact listed"}</small>
                    </div>
                    <span className="admin-category-pill">{listing.category}</span>
                    <strong className="admin-money">${Number(listing.price).toFixed(2)}</strong>
                    <span className={`stock-pill ${Number(listing.stock) <= 0 ? "empty" : ""}`}>
                      {Number(listing.stock)} {Number(listing.stock) === 1 ? "unit" : "units"}
                    </span>
                    <span className={`status-pill ${listing.status}`}>{listing.status}</span>
                    <time dateTime={listing.created_at}>{formatDate(listing.created_at)}</time>
                    <div className="admin-action-dropdown">
                      <button
                        type="button"
                        className="admin-action-trigger"
                        onClick={() =>
                          setOpenListingActionId((currentId) => (currentId === listing.id ? null : listing.id))
                        }
                        aria-expanded={openListingActionId === listing.id}
                      >
                        Actions
                      </button>
                      {openListingActionId === listing.id && (
                        <div className="admin-action-menu">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedAdminListing(listing);
                              setOpenListingActionId(null);
                            }}
                          >
                            View
                          </button>
                          {listing.status === "hidden" || listing.status === "removed" ? (
                            <button type="button" onClick={() => restoreListing(listing)}>
                              Restore
                            </button>
                          ) : (
                            <button type="button" onClick={() => moderateListing(listing, "hide")}>
                              Hide
                            </button>
                          )}
                          {listing.status !== "removed" && (
                            <>
                              <div className="admin-action-divider" />
                              <button type="button" className="danger-action" onClick={() => moderateListing(listing, "remove")}>
                                Remove
                              </button>
                            </>
                          )}
                        </div>
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
            <AdminOrdersTable orders={orders} formatDate={formatDate} onViewProfile={openUserProfile} />
          </div>
        )}

        {activeTab === "Reports" && (
          <div className="reports-page">
            <div className="reports-header">
              <div>
                <p className="section-kicker">Marketplace analytics</p>
                <h2>Reports</h2>
                <span>View marketplace sales, orders and listing activity.</span>
              </div>
              <button type="button" className="auth-submit" onClick={() => setIsConfirmingReport(true)}>
                Export PDF
              </button>
            </div>

            <div className="report-filter">
              <label>
                Period
                <select value={reportPeriod} onChange={(event) => setReportPeriod(event.target.value)}>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </label>
              <label>
                From
                <input type="date" value={reportFromDate} onChange={(event) => setReportFromDate(event.target.value)} />
              </label>
              <label>
                To
                <input type="date" value={reportToDate} onChange={(event) => setReportToDate(event.target.value)} />
              </label>
              <button type="button" className="secondary-button" onClick={generateReport}>
                Generate Report
              </button>
            </div>

            <div className="summary-grid">
              <div className="summary-card">
                <span>Total Sales</span>
                <h3>{reportSummary.totalSales}</h3>
              </div>
              <div className="summary-card">
                <span>Total Orders</span>
                <h3>{reportSummary.totalOrders}</h3>
              </div>
              <div className="summary-card">
                <span>Items Sold</span>
                <h3>{reportSummary.itemsSold}</h3>
              </div>
              <div className="summary-card revenue-card">
                <span>Total Revenue</span>
                <h3>${Number(reportSummary.revenue).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
              </div>
            </div>

            <div className="report-sections">
              <div className="report-box">
                <h3>Order Summary</h3>
                <div className="status-row">
                  <span>Completed</span>
                  <strong>{orderStatusSummary.completed}</strong>
                </div>
                <div className="status-row">
                  <span>Pending</span>
                  <strong>{orderStatusSummary.pending}</strong>
                </div>
                <div className="status-row">
                  <span>Cancelled</span>
                  <strong>{orderStatusSummary.cancelled}</strong>
                </div>
              </div>

              <div className="report-box">
                <h3>Listings</h3>
                <div className="status-row">
                  <span>Active</span>
                  <strong>{listingSummary.active}</strong>
                </div>
                <div className="status-row">
                  <span>Sold</span>
                  <strong>{listingSummary.sold}</strong>
                </div>
                <div className="status-row">
                  <span>Removed</span>
                  <strong>{listingSummary.removed}</strong>
                </div>
              </div>
            </div>

            <div className="transactions admin-table-card">
              <h3>Sales & Order Report</h3>
              <AdminReportTable orders={filteredReportOrders} onViewProfile={openUserProfile} />
            </div>
          </div>
        )}

        {activeTab === "Flags" && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <h2>Flags</h2>
              <span className="admin-record-count">
                {userReports.length} {userReports.length === 1 ? "report" : "reports"}
              </span>
            </div>
            <div className="admin-table">
              <div className="admin-table-head user-reports-grid">
                <span>Reporter</span>
                <span>Target</span>
                <span>Seller</span>
                <span>Reason</span>
                <span>Status</span>
                <span>Date</span>
              </div>
              {userReports.length ? (
                userReports.map((reportRecord) => (
                  <div className="admin-table-row user-reports-grid" key={reportRecord.id}>
                    <button type="button" className="profile-name-button" onClick={() => openUserProfile(reportRecord.reporter)}>
                      {reportRecord.reporter_username}
                    </button>
                    <div className="flag-target">
                      <strong>{reportRecord.target_label}</strong>
                      {reportRecord.target_item ? (
                        <button type="button" onClick={() => setSelectedAdminListing(reportRecord.target_item)}>
                          View item
                        </button>
                      ) : (
                        <span>{reportRecord.target_type}</span>
                      )}
                    </div>
                    <div className="flag-target">
                      {reportRecord.seller ? (
                        <button
                          type="button"
                          className="profile-name-button"
                          onClick={() => openUserProfile(reportRecord.seller)}
                        >
                          {reportRecord.seller.username}
                        </button>
                      ) : (
                        <span>Not available</span>
                      )}
                    </div>
                    <span>{reportRecord.reason}</span>
                    <span className={`status-pill ${reportRecord.status}`}>{reportRecord.status}</span>
                    <span>{formatDate(reportRecord.created_at)}</span>
                  </div>
                ))
              ) : (
                <p className="empty-state">No user reports submitted.</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "Reviews" && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <h2>Reviews</h2>
              <span className="admin-record-count">
                {ratingReviews.length} {ratingReviews.length === 1 ? "review" : "reviews"}
              </span>
            </div>
            <div className="admin-table">
              <div className="admin-table-head ratings-grid">
                <span>Reviewer</span>
                <span>Listing</span>
                <span>Seller</span>
                <span>Rating</span>
                <span>Review</span>
                <span>Date</span>
              </div>
              {ratingReviews.length ? (
                ratingReviews.map((reviewRecord) => (
                  <div className="admin-table-row ratings-grid" key={reviewRecord.id}>
                    <button type="button" className="profile-name-button" onClick={() => openUserProfile(reviewRecord.reviewer)}>
                      {reviewRecord.reviewer_username}
                    </button>
                    <span>{reviewRecord.item_name}</span>
                    <button type="button" className="profile-name-button" onClick={() => openUserProfile(reviewRecord.seller)}>
                      {reviewRecord.seller_username}
                    </button>
                    <span className="rating-stars">{"★".repeat(reviewRecord.rating)}{"☆".repeat(5 - reviewRecord.rating)}</span>
                    <span>{reviewRecord.review}</span>
                    <span>{formatDate(reviewRecord.created_at)}</span>
                  </div>
                ))
              ) : (
                <p className="empty-state">No ratings or reviews submitted.</p>
              )}
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

      {selectedNotification && (
        <div className="auth-modal-backdrop" onClick={() => setSelectedNotification(null)}>
          <div className="notification-detail-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className={`notification-view-state ${selectedNotification.is_read ? "viewed" : "unread"}`}>
                  {selectedNotification.is_read ? "Viewed" : "New"}
                </span>
                <h3>{selectedNotification.title}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setSelectedNotification(null)} aria-label="Close">
                x
              </button>
            </div>
            <p>{selectedNotification.message}</p>
            <div className="notification-detail-meta">
              <span>Type: {selectedNotification.category}</span>
              <span>
                From:{" "}
                {selectedNotification.actor ? (
                  <button type="button" className="profile-name-button" onClick={() => openUserProfile(selectedNotification.actor)}>
                    {selectedNotification.actor_username}
                  </button>
                ) : (
                  selectedNotification.actor_username || "System"
                )}
              </span>
              <span>{formatDate(selectedNotification.created_at)}</span>
            </div>
            <div className="admin-detail-actions">
              <button type="button" className="danger-outline-button" onClick={() => removeNotification(selectedNotification.id)}>
                Remove Notification
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedAdminListing && (
        <div className="auth-modal-backdrop" onClick={() => setSelectedAdminListing(null)}>
          <div className="admin-listing-detail-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className={`status-pill ${selectedAdminListing.status}`}>{selectedAdminListing.status}</span>
                <h3>{selectedAdminListing.name}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setSelectedAdminListing(null)} aria-label="Close">
                x
              </button>
            </div>
            {selectedAdminListing.photo ? (
              <img src={selectedAdminListing.photo} alt={selectedAdminListing.name} className="admin-listing-detail-image" />
            ) : null}
            <div className="admin-listing-detail-grid">
              <span>Listing ID</span>
              <strong>#{selectedAdminListing.id}</strong>
              <span>Seller</span>
              {selectedAdminListing.seller ? (
                <button type="button" className="profile-name-button" onClick={() => openUserProfile(selectedAdminListing.seller)}>
                  {selectedAdminListing.seller_username}
                </button>
              ) : (
                <strong>{selectedAdminListing.seller_username}</strong>
              )}
              <span>Category</span>
              <strong>{selectedAdminListing.category}</strong>
              <span>Price</span>
              <strong>${Number(selectedAdminListing.price).toFixed(2)}</strong>
              <span>Stock</span>
              <strong>{selectedAdminListing.stock}</strong>
              <span>Contact</span>
              <strong>{selectedAdminListing.contact || "No contact listed"}</strong>
              <span>Created</span>
              <strong>{formatDate(selectedAdminListing.created_at)}</strong>
            </div>
            <p>{selectedAdminListing.description}</p>
            {selectedAdminListing.removed_reason ? (
              <div className="admin-listing-reason">
                <strong>Moderation Reason</strong>
                <p>{selectedAdminListing.removed_reason}</p>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {selectedStudent && (
        <div className="auth-modal-backdrop" onClick={() => setSelectedStudent(null)}>
          <div className="admin-student-detail-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className={`status-pill ${selectedStudent.status}`}>{selectedStudent.status}</span>
                <h3>{selectedStudent.username}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setSelectedStudent(null)} aria-label="Close">
                x
              </button>
            </div>
            <div className="admin-listing-detail-grid">
              <span>Student ID</span>
              <strong>{selectedStudent.student_id || selectedStudent.id}</strong>
              <span>Email</span>
              <strong>{selectedStudent.email}</strong>
              <span>Role</span>
              <strong>{selectedStudent.role}</strong>
              <span>Status</span>
              <strong>{selectedStudent.status}</strong>
              <span>Registered</span>
              <strong>{formatDate(selectedStudent.created_at)}</strong>
            </div>
            <div className="admin-detail-actions">
              {selectedStudent.status === "suspended" ? (
                <button type="button" className="secondary-button" onClick={() => updateStudentStatus(selectedStudent, "reactivate")}>
                  Reactivate
                </button>
              ) : (
                <button type="button" className="danger-outline-button" onClick={() => updateStudentStatus(selectedStudent, "suspend")}>
                  Suspend
                </button>
              )}
              <button type="button" className="danger-outline-button" onClick={() => deleteStudentPermanently(selectedStudent)}>
                Delete Permanently
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

function AdminOrdersTable({ orders, formatDate, onViewProfile }) {
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
          <button type="button" className="profile-name-button" onClick={() => onViewProfile(order.buyer)}>
            {order.buyer_username}
          </button>
          <button type="button" className="profile-name-button" onClick={() => onViewProfile(order.seller)}>
            {order.seller_username}
          </button>
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

function AdminReportTable({ orders, onViewProfile }) {
  if (!orders.length) {
    return <p className="empty-state">No report records found.</p>;
  }

  return (
    <div className="admin-table">
      <div className="admin-table-head report-orders-grid">
        <span>Order ID</span>
        <span>Item</span>
        <span>Seller</span>
        <span>Buyer</span>
        <span>Status</span>
        <span>Amount</span>
      </div>
      {orders.map((order) => (
        <div className="admin-table-row report-orders-grid" key={order.id}>
          <strong>ORD{String(order.id).padStart(3, "0")}</strong>
          <span>{order.item_name}</span>
          <button type="button" className="profile-name-button" onClick={() => onViewProfile(order.seller)}>
            {order.seller_username}
          </button>
          <button type="button" className="profile-name-button" onClick={() => onViewProfile(order.buyer)}>
            {order.buyer_username}
          </button>
          <span className={`status-pill ${order.status}`}>{order.status}</span>
          <span>${Number(order.total_amount || order.price).toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}

export default AdminDashboard;
