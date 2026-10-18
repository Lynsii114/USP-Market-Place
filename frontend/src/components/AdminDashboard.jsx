import Breadcrumbs from "./Breadcrumbs";
import { apiFetch as fetch } from "../config/request";
import React, { useEffect, useMemo, useRef, useState } from "react";
import ReportsPanel from "./ReportsPanel";

const adminTabs = ["Dashboard", "Students", "Listings", "Orders", "Categories", "Reports", "Flags", "Reviews"];

function AdminDashboard({
  apiUrl,
  categories = [],
  currentUser,
  logo,
  onCategoryCreated,
  onCategoryDeleted,
  onCategoryUpdated,
  onLogin,
  onLogout,
  onMarketplace,
  onOpenMessages,
  unreadMessageCount = 0,
  showToast,
}) {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [listings, setListings] = useState([]);
  const [orders, setOrders] = useState([]);
  const [studentSearch, setStudentSearch] = useState("");
  const [listingSearch, setListingSearch] = useState("");
  const [orderSearch, setOrderSearch] = useState("");
  const [orderDate, setOrderDate] = useState("");
  const [userReports, setUserReports] = useState([]);
  const [ratingReviews, setRatingReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [isNotificationPanelOpen, setIsNotificationPanelOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [selectedAdminListing, setSelectedAdminListing] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [openStudentActionId, setOpenStudentActionId] = useState(null);
  const [openListingActionId, setOpenListingActionId] = useState(null);
  const [openCategoryActionId, setOpenCategoryActionId] = useState(null);
  const [editingCategoryId, setEditingCategoryId] = useState(null);
  const [categoryForm, setCategoryForm] = useState({ name: "", image: "" });
  const [categoryImageName, setCategoryImageName] = useState("");
  const loadedTabsRef = useRef(new Set());
  const prefetchStartedRef = useRef(false);

  const isAdmin = currentUser?.role === "admin";
  const adminId = currentUser?.id;
  const uniqueCategories = useMemo(() => {
    const seenCategories = new Set();
    return categories.filter((category) => {
      const key = category.name.toLowerCase();
      if (seenCategories.has(key)) {
        return false;
      }
      seenCategories.add(key);
      return true;
    });
  }, [categories]);

  const parseResponse = async (response, fallbackMessage) => {
    const responseBody = await response.text();
    let data = null;
    try {
      data = responseBody ? JSON.parse(responseBody) : null;
    } catch {
      const preview = responseBody.replace(/\s+/g, " ").trim().slice(0, 160) || response.statusText || "No response body";
      throw new Error(`Server returned a non-JSON response (HTTP ${response.status}) from ${response.url}. ${preview}`);
    }
    if (!response.ok) {
      const detail = data?.detail || fallbackMessage;
      if (response.status === 503 || /database unavailable/i.test(detail)) {
        throw new Error("Marketplace database is unavailable. Check the backend database configuration.");
      }
      throw new Error(detail);
    }
    return data;
  };

  const fetchAdmin = async (path, fallbackMessage, options = {}) => {
    const joiner = path.includes("?") ? "&" : "?";
    const url = `${apiUrl}${path}${joiner}admin_id=${adminId}`;
    let response;
    try {
      response = await fetch(url, options);
    } catch {
      throw new Error(`Cannot reach the admin API at ${apiUrl}. Check the backend deployment, API URL, and CORS settings.`);
    }
    return parseResponse(response, fallbackMessage);
  };

  const loadDashboard = async () => {
    const data = await fetchAdmin("/admin/dashboard", "Unable to load dashboard");
    setDashboard(data);
    loadedTabsRef.current.add("Dashboard");
  };

  const loadStudents = async () => {
    const data = await fetchAdmin(`/admin/students?search=${encodeURIComponent(studentSearch)}`, "Unable to load students");
    setStudents(data);
    loadedTabsRef.current.add("Students");
  };

  const loadListings = async () => {
    const data = await fetchAdmin(`/admin/listings?search=${encodeURIComponent(listingSearch)}`, "Unable to load listings");
    setListings(data);
    loadedTabsRef.current.add("Listings");
  };

  const loadOrders = async () => {
    const params = new URLSearchParams({
      search: orderSearch,
      order_date: orderDate,
    });
    const data = await fetchAdmin(`/admin/orders?${params.toString()}`, "Unable to load orders");
    setOrders(data);
    loadedTabsRef.current.add("Orders");
  };

  const loadNotifications = async () => {
    const data = await fetchAdmin("/admin/notifications", "Unable to load notifications");
    setNotifications(data);
  };

  const loadUserReports = async () => {
    const data = await fetchAdmin("/admin/user-reports", "Unable to load user reports");
    setUserReports(data);
    loadedTabsRef.current.add("Flags");
  };

  const loadRatingReviews = async () => {
    const data = await fetchAdmin("/admin/ratings", "Unable to load ratings and reviews");
    setRatingReviews(data);
    loadedTabsRef.current.add("Reviews");
  };

  const readCompressedImageFile = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const image = new Image();
        image.onload = () => {
          const maxSize = 900;
          const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
          const canvas = document.createElement("canvas");
          canvas.width = Math.max(1, Math.round(image.width * scale));
          canvas.height = Math.max(1, Math.round(image.height * scale));
          const context = canvas.getContext("2d");
          if (!context) {
            reject(new Error("Unable to process category image"));
            return;
          }
          context.drawImage(image, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL("image/jpeg", 0.82));
        };
        image.onerror = () => reject(new Error("Unable to read category image"));
        image.src = reader.result;
      };
      reader.onerror = () => reject(new Error("Unable to read category image"));
      reader.readAsDataURL(file);
    });

  const handleCategoryImageChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      setCategoryImageName("");
      setCategoryForm((currentForm) => ({ ...currentForm, image: "" }));
      return;
    }
    if (!file.type.startsWith("image/")) {
      showToast("Please choose an image file.", "error");
      event.target.value = "";
      return;
    }
    try {
      const image = await readCompressedImageFile(file);
      setCategoryImageName(file.name);
      setCategoryForm((currentForm) => ({ ...currentForm, image }));
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to read category image", "error");
    }
  };

  const createCategory = async (event) => {
    event.preventDefault();
    const name = categoryForm.name.trim();
    if (!name) {
      showToast("Category name is required.", "error");
      return;
    }

    setIsLoading(true);
    try {
      const isEditing = Boolean(editingCategoryId);
      const category = await fetchAdmin(
        isEditing ? `/admin/categories/${editingCategoryId}` : "/admin/categories",
        isEditing ? "Unable to update category" : "Unable to add category",
        {
          method: isEditing ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, image: categoryForm.image, icon: name.slice(0, 4) || "More" }),
        }
      );
      if (isEditing) {
        onCategoryUpdated?.(category);
      } else {
        onCategoryCreated?.(category);
      }
      setCategoryForm({ name: "", image: "" });
      setCategoryImageName("");
      setEditingCategoryId(null);
      setActiveTab("Categories");
      showToast(`${category.name} category ${isEditing ? "updated" : "added"}.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to save category", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const editCategory = (category) => {
    if (!category.created_at) {
      showToast("Built-in categories cannot be edited from this menu.", "error");
      return;
    }
    setEditingCategoryId(category.id);
    setCategoryForm({ name: category.name, image: category.image || "" });
    setCategoryImageName("");
    setOpenCategoryActionId(null);
    setActiveTab("Edit Category");
  };

  const deleteCategory = async (category) => {
    if (!category.created_at) {
      showToast("Built-in categories cannot be deleted from this menu.", "error");
      return;
    }
    if (!window.confirm(`Delete "${category.name}" from marketplace categories?`)) {
      return;
    }

    setIsLoading(true);
    try {
      await fetchAdmin(`/admin/categories/${category.id}`, "Unable to delete category", { method: "DELETE" });
      onCategoryDeleted?.(category);
      setOpenCategoryActionId(null);
      showToast(`${category.name} category deleted.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to delete category", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const refreshActiveTab = async () => {
    if (!isAdmin) {
      return;
    }

    if (activeTab === "Reports" || activeTab === "Categories" || activeTab === "Add Category") {
      loadNotifications().catch(() => {});
      return;
    }

    if (loadedTabsRef.current.has(activeTab)) {
      loadNotifications().catch(() => {});
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
      } else if (activeTab === "Flags") {
        await loadUserReports();
      } else if (activeTab === "Reviews") {
        await loadRatingReviews();
      }
      loadNotifications().catch(() => {});
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load admin data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshActiveTab();
  }, [activeTab, isAdmin]);

  useEffect(() => {
    if (isAdmin) {
      loadNotifications().catch(() => {});
    }
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin || prefetchStartedRef.current) {
      return;
    }

    prefetchStartedRef.current = true;
    const timerId = window.setTimeout(() => {
      Promise.allSettled([
        loadDashboard(),
        loadStudents(),
        loadListings(),
        loadOrders(),
        loadUserReports(),
        loadRatingReviews(),
      ]).catch(() => {});
    }, 250);

    return () => window.clearTimeout(timerId);
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
        data?.message || `${student.username} was ${action === "suspend" ? "suspended" : "reactivated"}.`;
      if (data?.user) {
        setStudents((currentStudents) =>
          currentStudents.map((currentStudent) => (currentStudent.id === student.id ? data.user : currentStudent))
        );
        if (selectedStudent?.id === student.id) {
          setSelectedStudent(data.user);
        }
      }
      setOpenStudentActionId(null);
      loadNotifications().catch(() => {});
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
      setStudents((currentStudents) => currentStudents.filter((currentStudent) => currentStudent.id !== student.id));
      if (selectedStudent?.id === student.id) {
        setSelectedStudent(null);
      }
      setOpenStudentActionId(null);
      loadNotifications().catch(() => {});
      showToast(data.message || "Student permanently deleted.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to delete student");
    } finally {
      setIsLoading(false);
    }
  };

  const goBack = () => {
    if (activeTab === "Add Category" || activeTab === "Edit Category") {
      setCategoryForm({ name: "", image: "" });
      setCategoryImageName("");
      setEditingCategoryId(null);
      setActiveTab("Categories");
      return;
    }
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    onMarketplace();
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
              Back to USP Marketplace
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
        <Breadcrumbs items={[{ label: "Home", onClick: onMarketplace }, { label: "Administration", onClick: () => setActiveTab("Dashboard") }, { label: activeTab }]} />
        <div className="admin-topbar">
          <button
            type="button"
            className="admin-back-button"
            onClick={goBack}
            aria-label="Go back"
            title="Go back"
          >
            <span aria-hidden="true">‹</span>
          </button>
          <div className="admin-page-title">
            {activeTab !== "Categories" && <h1>{activeTab}</h1>}
          </div>
          <div className="admin-topbar-actions">
            <button type="button" className="secondary-button" onClick={onOpenMessages}>
              Messages{unreadMessageCount > 0 ? ` (${unreadMessageCount} unread)` : ""}
            </button>
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
              USP Marketplace
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
            <AdminSearch
              value={studentSearch}
              onChange={(value) => {
                loadedTabsRef.current.delete("Students");
                setStudentSearch(value);
              }}
              onSearch={loadStudents}
              placeholder="Search name or email"
            />
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
              <AdminSearch
                value={listingSearch}
                onChange={(value) => {
                  loadedTabsRef.current.delete("Listings");
                  setListingSearch(value);
                }}
                onSearch={loadListings}
                placeholder="Search listing, seller, or category"
              />
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
              <input
                value={orderSearch}
                onChange={(event) => {
                  loadedTabsRef.current.delete("Orders");
                  setOrderSearch(event.target.value);
                }}
                placeholder="Order ID, buyer, seller, or item"
              />
              <input
                type="date"
                value={orderDate}
                onChange={(event) => {
                  loadedTabsRef.current.delete("Orders");
                  setOrderDate(event.target.value);
                }}
              />
              <button type="button" className="auth-submit" onClick={loadOrders}>
                Search
              </button>
            </div>
            <AdminOrdersTable orders={orders} formatDate={formatDate} onViewProfile={openUserProfile} />
          </div>
        )}

        {activeTab === "Categories" && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <h2>Marketplace Categories</h2>
              <div className="admin-section-actions">
                <span className="admin-record-count">
                  {uniqueCategories.length} {uniqueCategories.length === 1 ? "category" : "categories"}
                </span>
                <button type="button" className="auth-submit" onClick={() => setActiveTab("Add Category")}>
                  Add Category
                </button>
              </div>
            </div>
            <div className="admin-category-grid">
              {uniqueCategories.map((category) => (
                <div className="admin-category-card" key={`${category.created_at ? "stored" : "default"}-${category.name}-${category.id}`}>
                  {category.created_at && !category.built_in && <div className="admin-category-card-actions">
                    <button
                      type="button"
                      className="admin-category-menu-trigger"
                      onClick={() =>
                        setOpenCategoryActionId((currentId) => (currentId === category.name ? null : category.name))
                      }
                      aria-label={`Actions for ${category.name}`}
                      aria-expanded={openCategoryActionId === category.name}
                    >
                      ...
                    </button>
                    {openCategoryActionId === category.name && (
                      <div className="admin-category-menu">
                        <button type="button" onClick={() => editCategory(category)}>
                          Edit
                        </button>
                        <button type="button" className="danger-action" onClick={() => deleteCategory(category)}>
                          Delete
                        </button>
                      </div>
                    )}
                  </div>}
                  {category.image ? <img src={category.image} alt={category.name} style={{ objectPosition: category.imagePosition || "center" }} /> : <span>{category.icon || category.name.charAt(0)}</span>}
                  <strong>{category.name}</strong>
                </div>
              ))}
            </div>
          </div>
        )}

        {(activeTab === "Add Category" || activeTab === "Edit Category") && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <h2>{activeTab}</h2>
            </div>
            <form className="admin-category-form" onSubmit={createCategory}>
              <label>
                Category name
                <input
                  value={categoryForm.name}
                  onChange={(event) => setCategoryForm((currentForm) => ({ ...currentForm, name: event.target.value }))}
                  maxLength={64}
                  placeholder="e.g. Sports"
                />
              </label>
              <label>
                Category image
                <input type="file" accept="image/*" onChange={handleCategoryImageChange} />
              </label>
              {categoryForm.image ? (
                <div className="admin-category-preview">
                  <img src={categoryForm.image} alt={categoryForm.name || "Category preview"} />
                  <span>{categoryImageName || "Selected image"}</span>
                </div>
              ) : null}
              <div className="admin-category-form-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setCategoryForm({ name: "", image: "" });
                    setCategoryImageName("");
                    setEditingCategoryId(null);
                    setActiveTab("Categories");
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="auth-submit" disabled={isLoading}>
                  {activeTab === "Edit Category" ? "Update Category" : "Save Category"}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === "Reports" && <ReportsPanel apiUrl={apiUrl} adminId={adminId} showToast={showToast} />}

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
        </div>
      ))}
    </div>
  );
}

export default AdminDashboard;
