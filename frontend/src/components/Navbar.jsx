import React, { useMemo, useState } from "react";

function Navbar({
  logo,
  currentUser,
  cartCount,
  notifications = [],
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

  return (
    <header className="navbar">
      <div className="brand">
        <img src={logo} alt="USP logo" className="usp-logo" />
        <span>USP Online Marketplace</span>
      </div>

      <nav className="nav-links">
        <a href="#home" onClick={onHome}>
          Home
        </a>
        <a href="#listings" onClick={onBrowse}>
          Shop
        </a>
        <a href="#seller-listings" onClick={() => onOpenSellerTab("add-listing")}>
          Sell an Item
        </a>
        {currentUser ? (
          <div className="nav-dropdown activity-dropdown">
            <button type="button" className="nav-dropdown-button">
              My Activity
            </button>
            <div className="nav-dropdown-menu activity-menu">
              <button type="button" onClick={onOpenPurchases}>
                My Purchases
              </button>
              <button type="button" onClick={() => onOpenSellerTab("my-listings")}>
                My Listings
              </button>
              <button type="button" onClick={() => onOpenAccountPage("sales")}>
                My Sales
              </button>
            </div>
          </div>
        ) : null}
        <div className="nav-actions">
          <div className="nav-dropdown notification-dropdown">
            <button type="button" className="icon-nav-button notification-icon-button" aria-label="Notifications">
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
          <button type="button" className="icon-nav-button cart-nav-button" onClick={onOpenCart} aria-label="Open cart">
            <span className="cart-icon" aria-hidden="true">
              &#128722;
            </span>
            {cartCount > 0 && <span className="cart-count">{cartCount}</span>}
          </button>
          {currentUser ? (
            <div className="nav-dropdown account-dropdown">
              <button type="button" className="icon-nav-button account-icon-button" aria-label="My account">
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
