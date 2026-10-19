import Breadcrumbs from "./Breadcrumbs";
import { apiFetch as fetch } from "../config/request";
import React, { useEffect, useMemo, useRef, useState } from "react";
import ReportsPanel from "./ReportsPanel";
import SearchInput from "./SearchInput";
import FlagReviewPanel from "./FlagReviewPanel";
import StudentActionDialog from "./StudentActionDialog";
import NotificationDismissDialog from "./NotificationDismissDialog";
import { searchRecords } from "../utils/search.mjs";
import NotificationsPage from "./NotificationsPage";

const adminTabs = ["Dashboard", "Students", "Listings", "Orders", "Categories", "Reports", "Flags", "Reviews", "Notifications"];
const ADMIN_LISTINGS_PAGE_SIZE = 20;

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
  initialListing = null,
}) {
  const [activeTab, setActiveTab] = useState(initialListing ? "Listings" : "Dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [listings, setListings] = useState([]);
  const [listingPage, setListingPage] = useState(1);
  const [orders, setOrders] = useState([]);
  const [studentSearch, setStudentSearch] = useState("");
  const [studentStatusFilter, setStudentStatusFilter] = useState("all");
  const [listingSearch, setListingSearch] = useState("");
  const [orderSearch, setOrderSearch] = useState("");
  const [categorySearch, setCategorySearch] = useState("");
  const [reviewSearch, setReviewSearch] = useState("");
  const [orderDate, setOrderDate] = useState("");
  const [userReports, setUserReports] = useState([]);
  const [ratingReviews, setRatingReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [notificationToRemove, setNotificationToRemove] = useState(null);
  const notificationBellRef = useRef(null);

  const closeNotifications = () => {
    setNotificationToRemove(null);
    setSelectedNotification(null);
    setIsNotificationPanelOpen(false);
    notificationBellRef.current?.focus();
  };

  const requestNotificationRemoval = (notification) => {
    setNotificationToRemove(notification);
    setSelectedNotification(null);
    setIsNotificationPanelOpen(false);
  };
  const [selectedAdminListing, setSelectedAdminListing] = useState(initialListing);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentAction, setStudentAction] = useState(null);
  const [openStudentActionId, setOpenStudentActionId] = useState(null);
  const [openListingActionId, setOpenListingActionId] = useState(null);
  const [openCategoryActionId, setOpenCategoryActionId] = useState(null);
  const [editingCategoryId, setEditingCategoryId] = useState(null);
  const [categoryForm, setCategoryForm] = useState({ name: "", image: "" });
  const [categoryImageName, setCategoryImageName] = useState("");
  const loadedTabsRef = useRef(new Set());
  const prefetchStartedRef = useRef(false);

  const isAdmin = currentUser?.role === "admin";
  const filteredStudents = searchRecords(students, studentSearch, (student) => [student.username, student.name, student.student_id, student.id, student.email, student.status]).filter((student) => studentStatusFilter === "all" || student.status === studentStatusFilter);
  const filteredAdminListings = searchRecords(listings, listingSearch, (listing) => [listing.name, listing.id, listing.seller_username, listing.category, listing.description, listing.status]);
  const filteredOrders = searchRecords(orders, orderSearch, (order) => [order.id, order.item_name, order.buyer_username, order.seller_username, order.category, order.payment_method, order.payment_status, order.order_stage, order.status]).filter((order) => !orderDate || String(order.purchased_at || "").slice(0, 10) === orderDate);
  const filteredReviews = searchRecords(ratingReviews, reviewSearch, (review) => [review.item_name, review.reviewer_username, review.seller_username, review.review, review.rating, review.id]);
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
  const listingPageCount = Math.max(1, Math.ceil(listings.length / ADMIN_LISTINGS_PAGE_SIZE));
  const currentListingPage = Math.min(listingPage, listingPageCount);
  const listingStart = (currentListingPage - 1) * ADMIN_LISTINGS_PAGE_SIZE;
  const visibleListings = listings.slice(listingStart, listingStart + ADMIN_LISTINGS_PAGE_SIZE);
  const listingPageNumbers = [...new Set([1, currentListingPage - 1, currentListingPage, currentListingPage + 1, listingPageCount])]
    .filter((page) => page >= 1 && page <= listingPageCount)
    .sort((a, b) => a - b);

  const changeListingPage = (page) => {
    setListingPage(page);
    setOpenListingActionId(null);
    document.getElementById("admin-listings-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const filteredCategories = searchRecords(uniqueCategories, categorySearch, (category) => [category.name, category.id]);

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
    const data = await fetchAdmin("/admin/students", "Unable to load students");
    setStudents(data);
    loadedTabsRef.current.add("Students");
  };

  const loadListings = async (resetPage = false) => {
    const data = await fetchAdmin(`/admin/listings?search=${encodeURIComponent(listingSearch)}`, "Unable to load listings");
    setListings(data);
    if (resetPage) setListingPage(1);
    loadedTabsRef.current.add("Listings");
  };

  const loadOrders = async () => {
    const data = await fetchAdmin("/admin/orders", "Unable to load orders");
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

  const runSearch = async (load) => {
    setIsLoading(true);
    try { await load(); }
    catch (error) { showToast(error instanceof Error ? error.message : "Unable to refresh search results."); }
    finally { setIsLoading(false); }
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
      setSelectedNotification((current) => current?.id === updatedNotification.id ? updatedNotification : current);
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
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to remove notification");
      return false;
    }
  };

  const updateStudentStatus = (student, action) => {
    setStudentAction({ student, action });
    setOpenStudentActionId(null);
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
      setSelectedAdminListing(null);
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
      setSelectedAdminListing(null);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to restore listing");
    } finally {
      setIsLoading(false);
    }
  };

  const deleteStudentPermanently = (student) => {
    setStudentAction({ student, action: "delete" });
    setOpenStudentActionId(null);
  };

  const confirmStudentAction = async (details) => {
    const { student, action } = studentAction;
    const deleting = action === "delete";
    const data = await fetchAdmin(`/admin/students/${student.id}${deleting ? "" : `/${action}`}`, `Unable to ${action} student`, {
      method: deleting ? "DELETE" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(details),
    });
    setStudents((current) => deleting ? current.filter((row) => row.id !== student.id) : current.map((row) => row.id === student.id ? data.user : row));
    setSelectedStudent((current) => current?.id === student.id ? (deleting ? null : data.user) : current);
    if (data.user) {
      const updateSeller = (listing) => listing?.seller_id === student.id ? { ...listing, seller: data.user } : listing;
      setListings((current) => current.map(updateSeller));
      setSelectedAdminListing((current) => updateSeller(current));
      setUserReports((current) => current.map((report) => ({ ...report, ...(report.seller?.id === student.id ? { seller: data.user } : {}), ...(report.reporter?.id === student.id ? { reporter: data.user } : {}) })));
    }
    loadNotifications().catch(() => {});
    return data;
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
            {activeTab !== "Categories" && activeTab !== "Notifications" && <h1>{activeTab}</h1>}
          </div>
          <div className="admin-topbar-actions">
            <button type="button" className="secondary-button" onClick={onOpenMessages}>
              Messages{unreadMessageCount > 0 ? ` (${unreadMessageCount} unread)` : ""}
            </button>
            <button type="button" className={activeTab === "Notifications" ? "icon-nav-button notification-icon-button active" : "icon-nav-button notification-icon-button"} onClick={() => setActiveTab("Notifications")} aria-label="Notifications" aria-current={activeTab === "Notifications" ? "page" : undefined}>
              <span aria-hidden="true">&#128276;</span>
              {unreadNotifications.length > 0 && <span className="notification-count">{unreadNotifications.length}</span>}
            </button>
            <button type="button" className="secondary-button" onClick={onMarketplace}>
              USP Marketplace
            </button>
          </div>
        </div>

        {isLoading && <p className="admin-loading">Loading admin data...</p>}

        {activeTab === "Notifications" && (
          <NotificationsPage notifications={notifications} onBack={() => setActiveTab("Dashboard")} onOpen={openNotification} onRemove={removeNotification} />
        )}

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
            <div className="admin-section-toolbar"><label className="student-status-filter">Account status<select value={studentStatusFilter} onChange={(event) => setStudentStatusFilter(event.target.value)}><option value="all">All accounts</option><option value="active">Active</option><option value="suspended">Suspended</option></select></label></div>
            <AdminSearch
              value={studentSearch}
              onChange={(value) => {
                loadedTabsRef.current.delete("Students");
                setStudentSearch(value);
              }}
              onSearch={() => runSearch(loadStudents)}
              placeholder="Name, student ID or email"
              resultCount={filteredStudents.length}
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
              {filteredStudents.map((student) => (
                <div className={`admin-table-row students-grid${student.status === "suspended" ? " suspended-student-row" : ""}`} key={student.id}>
                  <span>{student.student_id || "Not provided"}</span>
                  <button type="button" className="profile-name-button" onClick={() => openUserProfile(student)}>
                    {student.username}
                  </button>
                  <span>{student.email}</span>
                  <div className="student-account-status"><span className={`status-pill ${student.status}`}>{student.status === "suspended" ? "Suspended" : student.status === "active" ? "Active" : student.status}</span>{student.status === "suspended" && <small>{student.suspended_until ? `Until ${formatDate(student.suspended_until)}` : "Until admin review"}</small>}</div>
                  <span>{formatDate(student.created_at)}</span>
                  <div className="student-row-actions">
                  {student.status === "suspended" && <button type="button" className="secondary-button reactivate-account-button" onClick={() => updateStudentStatus(student, "reactivate")} aria-label={`Reactivate ${student.username} after reconsideration`}>Reactivate</button>}
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
                        {student.status !== "suspended" && (
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
                </div>
              ))}
              {!filteredStudents.length && <p className="empty-state">{studentStatusFilter === "suspended" ? "No suspended accounts match your search." : "No student accounts match your filters."}</p>}
            </div>
          </div>
        )}

        {activeTab === "Listings" && (
          <div className="admin-table-card" id="admin-listings-results">
            <div className="admin-section-toolbar">
              <AdminSearch
                value={listingSearch}
                onChange={(value) => {
                  loadedTabsRef.current.delete("Listings");
                  setListingSearch(value);
                  setListingPage(1);
                  setOpenListingActionId(null);
                }}
                onSearch={() => loadListings(true)}
                placeholder="Search listing, seller, or category"
              />
              <span className="admin-record-count">
                {listings.length ? `Showing ${listingStart + 1}–${Math.min(listingStart + ADMIN_LISTINGS_PAGE_SIZE, listings.length)} of ${listings.length} listings` : "0 listings"}
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
                visibleListings.map((listing) => (
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
                      {listing.seller?.status === "suspended" && <><span className="status-pill suspended">Account suspended</span><button type="button" className="secondary-button reactivate-account-button" onClick={() => updateStudentStatus(listing.seller, "reactivate")}>Reactivate account</button></>}
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
            {listingPageCount > 1 && (
              <nav className="inventory-pagination" aria-label="Admin listing pages">
                <button type="button" className="secondary-button" disabled={currentListingPage === 1} onClick={() => changeListingPage(currentListingPage - 1)}>Previous</button>
                {listingPageNumbers.map((page, index) => (
                  <React.Fragment key={page}>
                    {index > 0 && page - listingPageNumbers[index - 1] > 1 && <span aria-hidden="true">…</span>}
                    <button type="button" className="secondary-button" aria-label={`Page ${page}`} aria-current={page === currentListingPage ? "page" : undefined} onClick={() => changeListingPage(page)}>{page}</button>
                  </React.Fragment>
                ))}
                <button type="button" className="secondary-button" disabled={currentListingPage === listingPageCount} onClick={() => changeListingPage(currentListingPage + 1)}>Next</button>
              </nav>
            )}
          </div>
        )}

        {activeTab === "Orders" && (
          <div className="admin-table-card">
            <div className="admin-filters">
              <SearchInput value={orderSearch} onChange={setOrderSearch} label="Search orders" placeholder="Order ID, buyer, seller, item or payment status" onSearch={() => runSearch(loadOrders)} />
              <input
                type="date"
                value={orderDate}
                onChange={(event) => {
                  loadedTabsRef.current.delete("Orders");
                  setOrderDate(event.target.value);
                }}
              />
              <button type="button" className="auth-submit" onClick={() => runSearch(loadOrders)}>
                Search
              </button>
            </div>
            <p className="search-result-count" role="status">{filteredOrders.length} matching orders</p>
            <AdminOrdersTable orders={filteredOrders} formatDate={formatDate} onViewProfile={openUserProfile} />
          </div>
        )}

        {activeTab === "Categories" && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <h2>Marketplace Categories</h2>
              <div className="admin-section-actions">
                <span className="admin-record-count">
                  {filteredCategories.length} {filteredCategories.length === 1 ? "category" : "categories"}
                </span>
                <button type="button" className="auth-submit" onClick={() => setActiveTab("Add Category")}>
                  Add Category
                </button>
              </div>
            </div>
            <AdminSearch value={categorySearch} onChange={setCategorySearch} placeholder="Search categories by name or ID" />
            {!filteredCategories.length && <p className="empty-state">No categories match your search.</p>}
            <div className="admin-category-grid">
              {filteredCategories.map((category) => (
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

        {activeTab === "Flags" && <FlagReviewPanel
          reports={userReports}
          onRefresh={loadUserReports}
          onViewUser={openUserProfile}
          onSave={async (report, details) => {
            const result = await fetchAdmin(`/admin/user-reports/${report.id}`, "Unable to save report review", {
              method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(details),
            });
            setUserReports((current) => current.map((row) => row.id === report.id ? { ...row, ...result.report, target_item: result.listing } : row));
            loadNotifications().catch(() => {});
            loadListings().catch(() => {});
            return result;
          }}
        />}

        {activeTab === "Reviews" && (
          <div className="admin-table-card">
            <div className="admin-section-toolbar">
              <h2>Reviews</h2>
              <span className="admin-record-count">
                {filteredReviews.length} {filteredReviews.length === 1 ? "review" : "reviews"}
              </span>
            </div>
            <AdminSearch value={reviewSearch} onChange={setReviewSearch} placeholder="Listing, reviewer, seller, rating or review text" />
            <div className="admin-table">
              <div className="admin-table-head ratings-grid">
                <span>Reviewer</span>
                <span>Listing</span>
                <span>Seller</span>
                <span>Rating</span>
                <span>Review</span>
                <span>Date</span>
              </div>
              {filteredReviews.length ? (
                filteredReviews.map((reviewRecord) => (
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
                <p className="empty-state">No reviews match your search.</p>
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
              <button type="button" className="secondary-button" onClick={closeNotifications} aria-label="Close notification">
                Close
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
              <button type="button" className="danger-outline-button" onClick={() => requestNotificationRemoval(selectedNotification)}>
                <NotificationTrashIcon />
                Remove Notification
              </button>
            </div>
          </div>
        </div>
      )}

      {notificationToRemove && <NotificationDismissDialog notification={notificationToRemove} onConfirm={removeNotification} onClose={closeNotifications} />}

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
            <div className="admin-detail-actions">
              {selectedAdminListing.status === "hidden" || selectedAdminListing.status === "removed" ? (
                <button type="button" className="secondary-button" disabled={isLoading} onClick={() => restoreListing(selectedAdminListing)}>Restore listing</button>
              ) : (
                <button type="button" className="secondary-button" disabled={isLoading} onClick={() => moderateListing(selectedAdminListing, "hide")}>Hide listing</button>
              )}
              {selectedAdminListing.status !== "removed" && <button type="button" className="danger-outline-button" disabled={isLoading} onClick={() => moderateListing(selectedAdminListing, "remove")}>Remove listing</button>}
            </div>
          </div>
        </div>
      )}

      {studentAction && <StudentActionDialog student={studentAction.student} action={studentAction.action} onConfirm={confirmStudentAction} onClose={() => setStudentAction(null)} />}

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
              <strong>{selectedStudent.student_id || "Not provided"}</strong>
              <span>Email</span>
              <strong>{selectedStudent.email}</strong>
              <span>Role</span>
              <strong>{selectedStudent.role}</strong>
              <span>Status</span>
              <strong>{selectedStudent.status}</strong>
              {selectedStudent.status === "suspended" && <>
                <span>Suspension reason</span><strong>{selectedStudent.suspension_reason || "No reason recorded (legacy suspension)"}</strong>
                <span>Suspended until</span><strong>{selectedStudent.suspended_until ? `${formatDate(selectedStudent.suspended_until)} (your local time)` : "Manual reactivation required (legacy suspension)"}</strong>
              </>}
              <span>Registered</span>
              <strong>{formatDate(selectedStudent.created_at)}</strong>
            </div>
            <div className="admin-detail-actions">
              {selectedStudent.status === "suspended" ? (
                <button type="button" className="secondary-button" onClick={() => updateStudentStatus(selectedStudent, "reactivate")}>
                  Reactivate after reconsideration
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

function AdminSearch({ value, onChange, onSearch, placeholder, resultCount }) {
  return (
    <div className="admin-filters">
      <SearchInput value={value} onChange={onChange} onSearch={onSearch} label={placeholder || "Search records"} placeholder={placeholder} />
      {onSearch && <button type="button" className="auth-submit" onClick={onSearch}>Search</button>}
      {resultCount !== undefined && <span className="search-result-count" role="status">{resultCount} results</span>}
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
