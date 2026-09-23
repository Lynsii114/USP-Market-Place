import React, { useMemo, useState } from "react";

function Navbar({
  logo,
  currentUser,
  cartCount,
  notifications = [],
  activePage,
  onHome,
  onBrowse,
  onOpenSellerTab,
  onOpenPurchases,
  onOpenCart,
  onOpenAccountPage,
  onOpenAuth,
  onLogout,
}) {
  const [dismissedNotifications, setDismissedNotifications] = useState([]);
  const visibleNotifications = useMemo(
    () => notifications.filter((notification) => !dismissedNotifications.includes(notification.id)),
    [dismissedNotifications, notifications]
  );
  const navClass = (page) => (activePage === page ? "nav-item active" : "nav-item");

  return (
    <header className="navbar">
      <div className="brand">
        <img src={logo} alt="USP logo" className="usp-logo" />
        <span>USP Online Marketplace</span>
      </div>

      <nav className="nav-links">
        <a href="#home" className={navClass("home")} onClick={onHome}>
          <span aria-hidden="true">⌂</span>
          <span>Home</span>
        </a>
        <a href="#listings" className={navClass("shop")} onClick={onBrowse}>
          <span aria-hidden="true">▦</span>
          <span>Shop</span>
        </a>
        <a href="#seller-listings" className={navClass("sell")} onClick={() => onOpenSellerTab("add-listing")}>
          <span aria-hidden="true">＋</span>
          <span>Sell Item</span>
        </a>
        {currentUser ? (
          <div className="nav-dropdown activity-dropdown">
            <button type="button" className={activePage === "activity" ? "nav-dropdown-button active" : "nav-dropdown-button"}>
              <span aria-hidden="true">☷</span>
              <span>My Activity</span>
            </button>
            <div className="nav-dropdown-menu activity-menu">
              <div className="activity-menu-group">
                <strong>Buying</strong>
                <button type="button" onClick={() => onOpenPurchases("history")}>
                  <span aria-hidden="true">▤</span>
                  My Purchases
                </button>
                <button type="button" onClick={() => onOpenPurchases("track")}>
                  <span aria-hidden="true">◉</span>
                  Track Orders
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
              <div className="activity-menu-group">
                <strong>Other</strong>
                <button type="button" onClick={() => onOpenPurchases("history")}>
                  <span aria-hidden="true">★</span>
                  Reviews & Ratings
                </button>
              </div>
            </div>
          </div>
        ) : null}
        <button type="button" className={`${navClass("messages")} nav-symbol-button`} onClick={() => onOpenAccountPage("messages")} aria-label="Messages" title="Messages">
          <span aria-hidden="true">✉</span>
        </button>
        <div className="nav-actions">
          <div className="nav-dropdown notification-dropdown">
            <button type="button" className={activePage === "notifications" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} aria-label="Notifications" title="Notifications">
              <span aria-hidden="true">&#128276;</span>
              {visibleNotifications.length > 0 && <span className="notification-count">{visibleNotifications.length}</span>}
            </button>
            <div className="nav-dropdown-menu notification-menu">
              <strong>Notifications</strong>
              {visibleNotifications.length ? (
                visibleNotifications.slice(0, 4).map((notification) => (
                  <div className="notification-row viewed" key={notification.id}>
                    <p>{notification.message}</p>
                    <button
                      type="button"
                      className="notification-remove-button"
                      onClick={() =>
                        setDismissedNotifications((currentNotifications) => [
                          ...currentNotifications,
                          notification.id,
                        ])
                      }
                      aria-label="Remove notification"
                    >
                      x
                    </button>
                  </div>
                ))
              ) : (
                <p>No new notifications.</p>
              )}
            </div>
          </div>
          <button type="button" className={activePage === "cart" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} onClick={onOpenCart} aria-label="Open cart" title="Cart">
            <span className="cart-icon" aria-hidden="true">
              &#128722;
            </span>
            {cartCount > 0 && <span className="cart-count">{cartCount}</span>}
          </button>
          {currentUser ? (
            <div className="nav-dropdown account-dropdown">
              <button type="button" className={activePage === "account" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} aria-label="My account" title="Account">
                <span aria-hidden="true">&#128100;</span>
              </button>
              <div className="nav-dropdown-menu account-menu">
                <button type="button" onClick={() => onOpenAccountPage("profile")}>
                  My Profile
                </button>
                <button type="button" onClick={() => onOpenAccountPage("settings")}>
                  Settings
                </button>
                <div className="account-menu-divider" />
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
  );
}

export default Navbar;
