import React from "react";

function Navbar({
  logo,
  categories,
  currentUser,
  cartCount,
  onHome,
  onBrowse,
  onChooseCategory,
  onOpenSellerTab,
  onOpenCart,
  onOpenAuth,
  onLogout,
}) {
  return (
    <header className="navbar">
      <div className="brand">
        <img src={logo} alt="USP logo" className="usp-logo" />
        <span>USP Marketplace</span>
      </div>

      <nav className="nav-links">
        <a href="#home" onClick={onHome}>
          Home
        </a>
        <a href="#listings" onClick={onBrowse}>
          Browse
        </a>
        <div className="nav-dropdown">
          <a href="#categories" className="nav-dropdown-trigger" onClick={onHome}>
            Categories
          </a>
          <div className="nav-dropdown-menu">
            <button type="button" onClick={() => onChooseCategory("All")}>
              All Categories
            </button>
            {categories.map((category) => (
              <button type="button" key={category.id} onClick={() => onChooseCategory(category.name)}>
                {category.name}
              </button>
            ))}
          </div>
        </div>
        <div className="nav-dropdown">
          <a href="#seller-listings" className="nav-dropdown-trigger">
            Sell
          </a>
          <div className="nav-dropdown-menu">
            <button type="button" onClick={() => onOpenSellerTab("my-listings")}>
              My Listings
            </button>
            <button type="button" onClick={() => onOpenSellerTab("add-listing")}>
              Add Listing
            </button>
          </div>
        </div>
        <button type="button" className="cart-nav-button" onClick={onOpenCart}>
          <span className="cart-icon" aria-hidden="true">
            &#128722;
          </span>
          <span className="sr-only">Open cart</span>
          {cartCount > 0 && <span className="cart-count">{cartCount}</span>}
        </button>
        {currentUser ? (
          <div className="user-menu">
            <span className="current-user">{currentUser.username}</span>
            <button type="button" className="logout-button" onClick={onLogout}>
              Logout
            </button>
          </div>
        ) : (
          <>
            <button type="button" className="nav-button" onClick={() => onOpenAuth("login")}>
              Login
            </button>
            <button type="button" className="signup-link" onClick={() => onOpenAuth("signup")}>
              Sign Up
            </button>
          </>
        )}
      </nav>
    </header>
  );
}

export default Navbar;
