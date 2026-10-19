import React, { useEffect, useRef, useState } from "react";
import NotificationDismissDialog, { NotificationTrashIcon } from "./NotificationDismissDialog";
import WorkspaceSwitcher from "./WorkspaceSwitcher";

function Navbar({
  logo,
  currentUser,
  cartCount,
  unreadMessageCount = 0,
  notifications = [],
  activePage,
  onHome,
  onBrowse,
  onOpenSellerTab,
  onOpenPurchases,
  onOpenCart,
  onOpenAccountPage,
  onOpenAuth,
  onOpenHelp,
  onLogout,
  onNotificationView,
  onNotificationRemove,
  onAdmin,
}) {
  const isAdmin = currentUser?.role === "admin";
  const [isNavHidden, setIsNavHidden] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [notificationToRemove, setNotificationToRemove] = useState(null);
  const notificationMenuRef = useRef(null);
  const notificationBellRef = useRef(null);

  const closeNotifications = () => {
    setNotificationToRemove(null);
    setIsNotificationOpen(false);
    notificationBellRef.current?.focus();
  };

  useEffect(() => {
    const closeOutside = (event) => {
      if (!notificationMenuRef.current?.contains(event.target)) setIsNotificationOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setIsNotificationOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  const lastScrollY = useRef(0);
  const ticking = useRef(false);
  const unreadNotifications = notifications.filter((notification) => !notification.is_read);
  const navClass = (page) => (activePage === page ? "nav-item active" : "nav-item");

  useEffect(() => {
    lastScrollY.current = window.scrollY;

    const updateNavbar = () => {
      const currentScrollY = Math.max(window.scrollY, 0);
      const scrollDifference = currentScrollY - lastScrollY.current;

      if (currentScrollY <= 8) {
        setIsNavHidden(false);
      } else if (scrollDifference > 6 && currentScrollY > 96) {
        setIsNavHidden(true);
      } else if (scrollDifference < -6) {
        setIsNavHidden(false);
      }

      lastScrollY.current = currentScrollY;
      ticking.current = false;
    };

    const handleScroll = () => {
      if (!ticking.current) {
        window.requestAnimationFrame(updateNavbar);
        ticking.current = true;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
    <header className={isNavHidden ? "navbar navbar-hidden" : "navbar"}>
      <div className="brand">
        <img src={logo} alt="USP logo" className="usp-logo" />
        <span>USP Marketplace</span>
      </div>

      <nav className="nav-links">
        <a href="#home" className={navClass("home")} onClick={(event) => { event.preventDefault(); onHome(); }}>
          <span aria-hidden="true">⌂</span>
          <span>Home</span>
        </a>
        <a href="#listings" className={navClass("shop")} onClick={(event) => { event.preventDefault(); onBrowse(); }}>
          <span aria-hidden="true">▦</span>
          <span>Shop</span>
        </a>
        {!isAdmin && <a href="#seller-listings" className={navClass("sell")} onClick={(event) => { event.preventDefault(); onOpenSellerTab("add-listing"); }}>
          <span aria-hidden="true">＋</span>
          <span>Sell Item</span>
        </a>}
        {currentUser && !isAdmin ? (
          <div className="nav-dropdown activity-dropdown">
            <button type="button" className={activePage === "activity" ? "nav-dropdown-button active" : "nav-dropdown-button"}>
              <span aria-hidden="true">☷</span>
              <span>My Activity</span>
            </button>
            <div className="nav-dropdown-menu activity-menu">
              <button type="button" onClick={() => onOpenAccountPage("dashboard")}>
                My Dashboard
              </button>
              <div className="activity-menu-group">
                <strong>Buying</strong>
                <button type="button" onClick={onOpenPurchases}>
                  <span aria-hidden="true">▤</span>
                  My Purchases
                </button>
              </div>
              <div className="activity-menu-group">
                <strong>Selling</strong>
                <button type="button" onClick={() => onOpenSellerTab("my-listings")}>
                  <span aria-hidden="true">☰</span>
                  My Listings
                </button>
                <button type="button" onClick={() => onOpenAccountPage("sales")}>
                  <span aria-hidden="true">↗</span>
                  My Sales
                </button>
              </div>

            </div>
          </div>
        ) : null}
        {!isAdmin && <button type="button" className={`${navClass("messages")} nav-symbol-button nav-badge-button`} onClick={() => onOpenAccountPage("messages")} aria-label="Messages" title="Messages">
          <span aria-hidden="true">✉</span>
          <span className="nav-label">Messages</span>
          {unreadMessageCount > 0 && <span className="notification-count">{unreadMessageCount}</span>}
        </button>}
        <div className="nav-actions">
          <div className="nav-dropdown notification-dropdown" ref={notificationMenuRef}>
            <button ref={notificationBellRef} type="button" className={activePage === "notifications" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} aria-label="Notifications" title="Notifications" aria-expanded={isNotificationOpen} onClick={() => setIsNotificationOpen((open) => !open)}>
              <span aria-hidden="true">&#128276;</span>
              {unreadNotifications.length > 0 && <span className="notification-count" aria-label={`${unreadNotifications.length} unread notifications`} title={`${unreadNotifications.length} unread notifications`}>{unreadNotifications.length > 10 ? "10+" : unreadNotifications.length}</span>}
            </button>
            {isNotificationOpen && <div className="nav-dropdown-menu notification-menu notification-menu-open">
              <strong>Notifications</strong>
              {notifications.length ? (
                notifications.slice(0, 4).map((notification) => (
                  <div className={notification.is_read ? "notification-row viewed" : "notification-row unread"} key={notification.id}>
                    <button
                      type="button"
                      className="notification-item"
                      onClick={() => { closeNotifications(); onNotificationView?.(notification); }}
                    >
                      <span>{notification.title}</span>
                      <small>{notification.is_read ? "Viewed" : "New"}</small>
                      <p>{notification.message}</p>
                    </button>
                    <button
                      type="button"
                      className="notification-remove-button"
                      onClick={() => { setNotificationToRemove(notification); setIsNotificationOpen(false); }}
                      aria-label={`Remove notification: ${notification.title}`}
                      title="Remove notification"
                    >
                      <NotificationTrashIcon />
                    </button>
                  </div>
                ))
              ) : (
                <p>No new notifications.</p>
              )}
            </div>}
          </div>
          {isAdmin && <WorkspaceSwitcher active="marketplace" onAdmin={onAdmin} />}
          {!isAdmin && <button type="button" className={activePage === "cart" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} onClick={onOpenCart} aria-label="Open cart" title="Cart">
            <span className="cart-icon" aria-hidden="true">
              &#128722;
            </span>
            <span className="nav-label">Cart</span>
            {cartCount > 0 && <span className="cart-count">{cartCount}</span>}
          </button>}
          {currentUser ? (
            <div className="nav-dropdown account-dropdown">
              <button type="button" className={activePage === "account" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} aria-label="My account" title="Account">
                <span aria-hidden="true">&#128100;</span><span className="nav-label">Account</span>
              </button>
              <div className="nav-dropdown-menu account-menu">
                {!isAdmin && <><button type="button" onClick={() => onOpenAccountPage("profile")}>
                  My Profile
                </button>
                <button type="button" onClick={() => onOpenAccountPage("settings")}>
                  Settings
                </button>
                <div className="account-menu-divider" /></>}
                <button type="button" className="danger-button" onClick={onLogout}>
                  Logout
                </button>
              </div>
            </div>
          ) : (
            <button type="button" className="nav-button" onClick={() => onOpenAuth("login")} aria-label="Login">
              <span aria-hidden="true">&#128100;</span>
              Login
            </button>
          )}
        </div>
        {!currentUser && (
          <button type="button" className="signup-link" onClick={() => onOpenAuth("signup")}>
              Sign Up
          </button>
        )}
      </nav>
    </header>
    {notificationToRemove && <NotificationDismissDialog notification={notificationToRemove} onConfirm={onNotificationRemove} onClose={closeNotifications} />}
    </>
  );
}

export default Navbar;
