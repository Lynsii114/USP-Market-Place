import React, { useState } from "react";
import "./Home.css";
import logo from "../logo.png";

const API_URL = "http://localhost:8000/api";

function Home() {
  const [authMode, setAuthMode] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [authMessage, setAuthMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [signupSuccess, setSignupSuccess] = useState(null);
  const [emailError, setEmailError] = useState("");
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmationCode: "",
  });

  const validateUSPEmail = (email) => {
    if (!email) {
      setEmailError("");
      return true;
    }

    const validDomains = ["@usp.ac.fj", "@students.usp.ac.fj", "@usp.edu.fj"];
    const emailLower = email.toLowerCase();
    const isValid = validDomains.some(domain => emailLower.endsWith(domain));

    if (!isValid) {
      setEmailError("Email must be a valid USP student email");
    } else {
      setEmailError("");
    }

    return isValid;
  };

  const categories = [
    { id: 1, name: "Books", icon: "📚" },
    { id: 2, name: "Electronics", icon: "💻" },
    { id: 3, name: "Clothing", icon: "👕" },
    { id: 4, name: "Furniture", icon: "🪑" },
  ];

  const products = [
    { id: 1, name: "Computer Science Textbook", price: 30, icon: "📚" },
    { id: 2, name: "Laptop", price: 500, icon: "💻" },
    { id: 3, name: "Backpack", price: 25, icon: "🎒" },
    { id: 4, name: "Study Chair", price: 40, icon: "🪑" },
  ];

  const handleFieldChange = (event) => {
    const { name, value } = event.target;
    setFormData((previous) => ({ ...previous, [name]: value }));
    
    // Validate email as user types (only for signup mode)
    if (name === "email" && authMode === "signup") {
      validateUSPEmail(value);
    }
  };

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setAuthMessage("");

    try {
      if (signupSuccess && authMode === "verify") {
        // Verify confirmation code
        const response = await fetch(`${API_URL}/users/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: formData.username,
            confirmation_code: formData.confirmationCode,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Verification failed");
        }

        setCurrentUser(data.user);
        setAuthMessage(data.message || "Email verified!");
        setSignupSuccess(null);
        setFormData({ username: "", email: "", password: "", confirmationCode: "" });
        setAuthMode(null);
      } else {
        // Validate email for signup before sending
        if (authMode === "signup") {
          if (!validateUSPEmail(formData.email)) {
            setAuthMessage("Please enter a valid USP email address");
            setIsSubmitting(false);
            return;
          }
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

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Authentication failed");
        }

        if (authMode === "signup") {
          // Show verification form after successful signup
          setSignupSuccess({
            user: data.user,
            message: data.message,
            demo_code: data.confirmation_code,
          });
          setAuthMessage("");
          setEmailError("");
        } else {
          // Login successful
          setCurrentUser(data.user);
          setAuthMessage(data.message || "Login successful!");
          setFormData({ username: "", email: "", password: "", confirmationCode: "" });
          setAuthMode(null);
        }
      }
    } catch (error) {
      setAuthMessage(error.message || "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setAuthMessage("");
    setEmailError("");
  };

  return (
    <div className="home-page">
      <header className="navbar">
        <div className="brand">
          <img src={logo} alt="USP logo" className="usp-logo" />
          <span>USP MARKETPLACE</span>
        </div>

        <nav className="nav-links">
          <a href="/">Home</a>
          <a href="#listings">Browse</a>
          <a href="#categories">Categories</a>
          <a href="/cart">🛒 Cart</a>
          <button type="button" className="nav-button" onClick={() => openAuth("login")}>
            Login
          </button>
          <button type="button" className="signup-link" onClick={() => openAuth("signup")}>
            Sign Up
          </button>
        </nav>
      </header>

      {authMode && (
        <div className="auth-modal-backdrop" onClick={() => { setAuthMode(null); setSignupSuccess(null); }}>
          <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <h2>
                {signupSuccess
                  ? "Verify Email"
                  : authMode === "signup"
                  ? "Create Account"
                  : "Login"}
              </h2>
              <button type="button" className="close-button" onClick={() => { setAuthMode(null); setSignupSuccess(null); }}>
                ×
              </button>
            </div>

            {signupSuccess ? (
              <div className="success-message">
                <div className="success-icon">✓</div>
                <p className="success-title">Account Created!</p>
                <p className="success-desc">
                  We've sent a confirmation code to {signupSuccess.user.email}
                </p>
                <form onSubmit={handleAuthSubmit} className="auth-form">
                  <label>
                    Confirmation Code
                    <input
                      type="text"
                      name="confirmationCode"
                      value={formData.confirmationCode}
                      onChange={handleFieldChange}
                      placeholder="Enter 6-digit code"
                      maxLength="6"
                      required
                    />
                  </label>

                  {signupSuccess.demo_code && (
                    <p className="demo-code">
                      Demo code: <strong>{signupSuccess.demo_code}</strong>
                    </p>
                  )}

                  {authMessage && <p className="auth-message">{authMessage}</p>}

                  <button type="submit" className="auth-submit" disabled={isSubmitting}>
                    {isSubmitting ? "Verifying..." : "Verify Email"}
                  </button>
                </form>
              </div>
            ) : (
              <form onSubmit={handleAuthSubmit} className="auth-form">
                <label>
                  Username
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleFieldChange}
                    required
                  />
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
                        placeholder="student@usp.ac.fj"
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
            )}
          </div>
        </div>
      )}

      <section className="hero">
        <h1>Buy & Sell With USP Students</h1>

        <p>
          A simple marketplace for USP students to buy and sell items within the
          university community.
        </p>

        <div className="search-bar">
          <input
            type="text"
            placeholder="Search for books, electronics, clothing..."
          />

          <button type="button">🔍 Search</button>
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
                <button type="button" className="view-button">View Item</button>
              </div>
            </div>
          ))}
        </div>

        <div className="view-all-container">
          <button type="button" className="view-all-button">View All Items</button>
        </div>
      </section>

      <section className="info-section">
        <h2>Why USP Marketplace?</h2>

        <div className="info-container">
          <div className="info-card">
            <span>🎓</span>
            <h3>USP Community</h3>
            <p>A marketplace designed specifically for USP students.</p>
          </div>

          <div className="info-card">
            <span>🛍️</span>
            <h3>Easy Buying</h3>
            <p>Browse products and find affordable items from other students.</p>
          </div>

          <div className="info-card">
            <span>💰</span>
            <h3>Easy Selling</h3>
            <p>List items you no longer need and sell them to other students.</p>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-about">
          <h3>USP Marketplace</h3>
          <p>Buy and sell safely within the USP student community.</p>
        </div>

        <div className="footer-links">
          <a href="#about">About</a>
          <a href="#help">Help</a>
          <a href="#contact">Contact</a>
        </div>

        <div className="copyright">© 2026 USP Marketplace</div>
      </footer>
    </div>
  );
}

export default Home;
