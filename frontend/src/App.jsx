import React, { useEffect, useState } from "react";
import "./Home.css";
import logo from "../logo.png";

const API_URL = "http://localhost:8000/api";
const EMPTY_FORM = {
  username: "",
  email: "",
  password: "",
};

const categories = [
  { id: 1, name: "Books", icon: "Book" },
  { id: 2, name: "Electronics", icon: "Tech" },
  { id: 3, name: "Clothing", icon: "Wear" },
  { id: 4, name: "Furniture", icon: "Home" },
];

const products = [
  { id: 1, name: "Computer Science Textbook", price: 30, icon: "Book" },
  { id: 2, name: "Laptop", price: 500, icon: "Tech" },
  { id: 3, name: "Backpack", price: 25, icon: "Bag" },
  { id: 4, name: "Study Chair", price: 40, icon: "Seat" },
];

function Home() {
  const [authMode, setAuthMode] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [authMessage, setAuthMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [formData, setFormData] = useState(EMPTY_FORM);

  useEffect(() => {
    if (!authMessage || authMode) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setAuthMessage("");
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [authMessage, authMode]);

  const resetAuth = () => {
    setAuthMode(null);
    setAuthMessage("");
    setEmailError("");
  };

  const validateUSPEmail = (email) => {
    if (!email) {
      setEmailError("");
      return true;
    }

    const isValid = /^[a-z0-9]+@student\.usp\.ac\.fj$/.test(email.toLowerCase());
    setEmailError(isValid ? "" : "Email must be in format: Sxxxxxxxx@student.usp.ac.fj");
    return isValid;
  };

  const parseResponse = async (response, fallbackMessage) => {
    let data;

    try {
      data = await response.json();
    } catch {
      throw new Error("Invalid response from server");
    }

    if (!response.ok) {
      throw new Error(data?.detail || data?.message || fallbackMessage);
    }

    return data;
  };

  const handleFieldChange = (event) => {
    const { name, value } = event.target;
    setFormData((previous) => ({ ...previous, [name]: value }));

    if (name === "email" && authMode === "signup") {
      validateUSPEmail(value);
    }
  };

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setAuthMessage("");

    try {
      if (authMode === "signup" && !validateUSPEmail(formData.email)) {
        setAuthMessage("Please enter a valid USP email address");
        return;
      }

      const endpoint = authMode === "signup" ? "/users/signup" : "/users/login";
      const payload =
        authMode === "signup"
          ? {
              username: formData.username,
              email: formData.email,
              password: formData.password,
            }
          : {
              username: formData.username,
              password: formData.password,
            };

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await parseResponse(response, "Authentication failed");

      setCurrentUser(data.user);
      setAuthMessage(data.message || (authMode === "signup" ? "Account created successfully!" : "Login successful!"));
      setFormData(EMPTY_FORM);
      setAuthMode(null);
    } catch (error) {
      setAuthMessage(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setAuthMessage("");
    setEmailError("");
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setAuthMessage("Logged out successfully.");
  };

  return (
    <div className="home-page">
      <header className="navbar">
        <div className="brand">
          <img src={logo} alt="USP logo" className="usp-logo" />
          <span>USP Marketplace</span>
        </div>

        <nav className="nav-links">
          <a href="/">Home</a>
          <a href="#listings">Browse</a>
          <a href="#categories">Categories</a>
          <a href="/cart">Cart</a>
          {currentUser ? (
            <div className="user-menu">
              <span className="current-user">{currentUser.username}</span>
              <button type="button" className="logout-button" onClick={handleLogout}>
                Logout
              </button>
            </div>
          ) : (
            <>
              <button type="button" className="nav-button" onClick={() => openAuth("login")}>
                Login
              </button>
              <button type="button" className="signup-link" onClick={() => openAuth("signup")}>
                Sign Up
              </button>
            </>
          )}
        </nav>
      </header>

      {!authMode && authMessage && (
        <div className="toast-message" role="status">
          {authMessage}
        </div>
      )}

      {authMode && (
        <div className="auth-modal-backdrop" onClick={resetAuth}>
          <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <h2>{authMode === "signup" ? "Create Account" : "Login"}</h2>
              <button type="button" className="close-button" onClick={resetAuth} aria-label="Close">
                x
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className="auth-form">
              <label>
                Username
                <input type="text" name="username" value={formData.username} onChange={handleFieldChange} required />
              </label>

              {authMode === "signup" && (
                <div>
                  <label>
                    Email
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleFieldChange}
                      className={emailError ? "input-error" : ""}
                      placeholder="SXXXXXXXX@student.usp.ac.fj"
                      required
                    />
                  </label>
                  {emailError && <p className="email-error-message">{emailError}</p>}
                </div>
              )}

              <label>
                Password
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleFieldChange}
                  required
                />
              </label>

              {authMessage && <p className="auth-message">{authMessage}</p>}

              <button type="submit" className="auth-submit" disabled={isSubmitting}>
                {isSubmitting ? "Please wait..." : authMode === "signup" ? "Sign Up" : "Login"}
              </button>
            </form>
          </div>
        </div>
      )}

      <section className="hero">
        <h1>Buy and Sell With USP Students</h1>
        <p>A simple marketplace for USP students to buy and sell items within the university community.</p>

        <div className="search-bar">
          <input type="text" placeholder="Search for books, electronics, clothing..." />
          <button type="button">Search</button>
        </div>

        <a href="#listings" className="browse-button">
          Browse Marketplace
        </a>
      </section>

      <section className="categories" id="categories">
        <div className="section-heading">
          <h2>Categories</h2>
          <p>Find what you're looking for</p>
        </div>

        <div className="category-container">
          {categories.map((category) => (
            <div className="category-card" key={category.id}>
              <div className="category-icon">{category.icon}</div>
              <h3>{category.name}</h3>
            </div>
          ))}
        </div>
      </section>

      <section className="listings" id="listings">
        <div className="section-heading">
          <h2>Recent Listings</h2>
          <p>See the latest items listed by USP students</p>
        </div>

        <div className="product-container">
          {products.map((product) => (
            <div className="product-card" key={product.id}>
              <div className="product-image">{product.icon}</div>
              <div className="product-details">
                <h3>{product.name}</h3>
                <p className="product-price">${product.price}</p>
                <button type="button" className="view-button">
                  View Item
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="view-all-container">
          <button type="button" className="view-all-button">
            View All Items
          </button>
        </div>
      </section>

      <section className="info-section">
        <h2>Why USP Marketplace?</h2>

        <div className="info-container">
          <div className="info-card">
            <span>USP</span>
            <h3>USP Community</h3>
            <p>A marketplace designed specifically for USP students.</p>
          </div>

          <div className="info-card">
            <span>Buy</span>
            <h3>Easy Buying</h3>
            <p>Browse products and find affordable items from other students.</p>
          </div>

          <div className="info-card">
            <span>Sell</span>
            <h3>Easy Selling</h3>
            <p>List items you no longer need and sell them to other students.</p>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-container">
          <div className="footer-brand">
            <h2>USP Marketplace</h2>
            <p>
              Buy and sell safely within the
              <br />
              USP student community.
            </p>
          </div>

          <div className="footer-column">
            <h3>Explore</h3>
            <a href="/about">About Us</a>
            <a href="/help">Help &amp; FAQ</a>
            <a href="/contact">Contact Us</a>
          </div>

          <div className="footer-column">
            <h3>Quick Links</h3>
            <a href="/browse">Browse Items</a>
            <a href="/orders">My Orders</a>
            <a href="/account">My Account</a>
          </div>

          <div className="footer-updates">
            <h3>Stay Updated</h3>
            <p>Get the latest marketplace updates.</p>

            <form>
              <div className="subscribe">
                <input type="email" placeholder="Enter your email" required />
                <button type="submit">Subscribe</button>
              </div>
            </form>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-safe">
            <strong>Safe. Trusted. For Students.</strong>
            <span>Verified USP students only.</span>
          </div>

          <div className="footer-copyright">
            <img src={logo} alt="USP logo" className="footer-logo" />
            <p>&copy; 2026 USP Marketplace. All rights reserved.</p>
          </div>

          <div className="footer-legal">
            <a href="/privacy">Privacy Policy</a>
            <span>|</span>
            <a href="/terms">Terms of Use</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Home;
