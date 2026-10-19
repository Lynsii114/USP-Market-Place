import React from "react";

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
}) {
  const unreadNotifications = notifications.filter((notification) => !notification.is_read);
  const navClass = (page) => (activePage === page ? "nav-item active" : "nav-item");

return (
    <header className="navbar">
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
        <a href="#seller-listings" className={navClass("sell")} onClick={(event) => { event.preventDefault(); onOpenSellerTab("add-listing"); }}>
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
        <button type="button" className={`${navClass("messages")} nav-symbol-button nav-badge-button`} onClick={() => onOpenAccountPage("messages")} aria-label="Messages" title="Messages">
          <span aria-hidden="true">✉</span>
          <span className="nav-label">Messages</span>
          {unreadMessageCount > 0 && <span className="notification-count">{unreadMessageCount}</span>}
        </button>
        <div className="nav-actions">
          <button type="button" className={activePage === "notifications" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} onClick={() => onOpenAccountPage("notifications")} aria-label="Notifications">
            <span aria-hidden="true">&#128276;</span><span className="nav-label">Notifications</span>
            {unreadNotifications.length > 0 && <span className="notification-count">{unreadNotifications.length}</span>}
          </button>
          <button type="button" className={activePage === "cart" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} onClick={onOpenCart} aria-label="Open cart" title="Cart">
            <span className="cart-icon" aria-hidden="true">
              &#128722;
            </span>
            <span className="nav-label">Cart</span>
            {cartCount > 0 && <span className="cart-count">{cartCount}</span>}
          </button>
          <button type="button" className="nav-item nav-help-button" onClick={onOpenHelp} aria-label="Help and frequently asked questions">
            <span aria-hidden="true">?</span>
            <span>Help</span>
          </button>
          {currentUser ? (
            <div className="nav-dropdown account-dropdown">
              <button type="button" className={activePage === "account" ? "nav-item nav-badge-button nav-symbol-button active" : "nav-item nav-badge-button nav-symbol-button"} aria-label="My account" title="Account">
                <span aria-hidden="true">&#128100;</span><span className="nav-label">Account</span>
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
