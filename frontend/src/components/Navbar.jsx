import React from "react";

function Navbar({
  logo,
  currentUser,
  cartCount,
  onHome,
  onBrowse,
  onOpenSellerTab,
  onOpenPurchases,
  onOpenCart,
  onOpenAccountPage,
  onOpenAuth,
  onLogout,
}) {
  return (
    <header className="navbar">
      <div className="brand">
        <img src={logo} alt="USP logo" className="usp-logo" />
        <span>USP Buy & Sell</span>
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
