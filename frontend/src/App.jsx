import React, { useEffect, useState } from "react";
import "./Home.css";
import logo from "../logo.png";

const API_URL = "http://localhost:8000/api";

const EMPTY_AUTH_FORM = {
  username: "",
  email: "",
  password: "",
};

const EMPTY_LISTING_FORM = {
  name: "",
  price: "",
  description: "",
  contact: "",
  category: "Books",
  photo: "",
};

const categories = [
  { id: 1, name: "Books", icon: "Book" },
  { id: 2, name: "Electronics", icon: "Tech" },
  { id: 3, name: "Clothing", icon: "Wear" },
  { id: 4, name: "Furniture", icon: "Home" },
  { id: 5, name: "Other", icon: "More" },
];

function Home() {
  const [authMode, setAuthMode] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [toastMessage, setToastMessage] = useState("");
  const [formMessage, setFormMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [authForm, setAuthForm] = useState(EMPTY_AUTH_FORM);
  const [listingForm, setListingForm] = useState(EMPTY_LISTING_FORM);
  const [pendingPhoto, setPendingPhoto] = useState(null);
  const [listings, setListings] = useState([]);
  const [editingListingId, setEditingListingId] = useState(null);
  const [isLoadingListings, setIsLoadingListings] = useState(false);
  const [activeSellerTab, setActiveSellerTab] = useState("my-listings");
  const [openListingMenuId, setOpenListingMenuId] = useState(null);

  useEffect(() => {
    loadListings();
  }, []);

  useEffect(() => {
    if (!toastMessage) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setToastMessage("");
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [toastMessage]);

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

  const showToast = (message) => {
    setToastMessage("");
    window.setTimeout(() => setToastMessage(message), 10);
  };

  const loadListings = async () => {
    setIsLoadingListings(true);

    try {
      const response = await fetch(`${API_URL}/items`);
      const data = await parseResponse(response, "Unable to load listings");
      setListings(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load listings");
    } finally {
      setIsLoadingListings(false);
    }
  };

  const resetAuth = () => {
    setAuthMode(null);
    setFormMessage("");
    setEmailError("");
  };

  const validateUSPEmail = (email) => {
    if (!email) {
      setEmailError("");
      return true;
    }

    const isValid = /^s\d{8}@student\.usp\.ac\.fj$/.test(email.toLowerCase());
    setEmailError(isValid ? "" : "Email must be in format: SXXXXXXXX@student.usp.ac.fj");
    return isValid;
  };

  const handleAuthFieldChange = (event) => {
    const { name, value } = event.target;
    setAuthForm((previous) => ({ ...previous, [name]: value }));

    if (name === "email" && authMode === "signup") {
      validateUSPEmail(value);
    }
  };

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setFormMessage("");

    try {
      if (authMode === "signup" && !validateUSPEmail(authForm.email)) {
        setFormMessage("Please enter a valid USP email address");
        return;
      }

      const endpoint = authMode === "signup" ? "/users/signup" : "/users/login";
      const payload =
        authMode === "signup"
          ? authForm
          : {
              username: authForm.username,
              password: authForm.password,
            };

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await parseResponse(response, "Authentication failed");

      setCurrentUser(data.user);
      setAuthForm(EMPTY_AUTH_FORM);
      setAuthMode(null);
      showToast(data.message || (authMode === "signup" ? "Account created successfully!" : "Login successful!"));
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setFormMessage("");
    setEmailError("");
  };

  const handleLogout = () => {
    setCurrentUser(null);
    resetListingForm();
    showToast("Logged out successfully.");
  };

  const handleListingFieldChange = (event) => {
    const { name, value } = event.target;
    setListingForm((previous) => ({ ...previous, [name]: value }));
  };

  const handlePhotoChange = (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      setPendingPhoto(null);
      return;
    }

    const isJpg = file.type === "image/jpeg" || /\.(jpe?g)$/i.test(file.name);
    if (!isJpg) {
      event.target.value = "";
      setPendingPhoto(null);
      showToast("Please upload a JPG photo only.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setPendingPhoto({
        dataUrl: reader.result || "",
        name: file.name,
      });
    };
    reader.onerror = () => {
      showToast("Unable to read the selected photo.");
    };
    reader.readAsDataURL(file);
  };

  const confirmPhoto = () => {
    if (!pendingPhoto?.dataUrl) {
      return;
    }

    setListingForm((previous) => ({ ...previous, photo: pendingPhoto.dataUrl }));
    setPendingPhoto(null);
    showToast("Photo added to listing.");
  };

  const removePhoto = () => {
    setPendingPhoto(null);
    setListingForm((previous) => ({ ...previous, photo: "" }));
  };

  const resetListingForm = () => {
    setListingForm(EMPTY_LISTING_FORM);
    setPendingPhoto(null);
    setEditingListingId(null);
  };

  const handleListingSubmit = async (event) => {
    event.preventDefault();

    if (!currentUser) {
      openAuth("login");
      return;
    }

    setIsSubmitting(true);

    try {
      if (pendingPhoto) {
        showToast("Please confirm the selected photo before adding the listing.");
        return;
      }

      const payload = {
        ...listingForm,
        price: Number(listingForm.price),
        seller_id: currentUser.id,
      };
      const url = editingListingId
        ? `${API_URL}/items/${editingListingId}?seller_id=${currentUser.id}`
        : `${API_URL}/items`;
      const response = await fetch(url, {
        method: editingListingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      await parseResponse(response, editingListingId ? "Unable to update listing" : "Unable to create listing");
      resetListingForm();
      await loadListings();
      setActiveSellerTab("my-listings");
      setOpenListingMenuId(null);
      showToast(editingListingId ? "Listing updated successfully." : "Listing created successfully.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditListing = (listing) => {
    setEditingListingId(listing.id);
    setActiveSellerTab("add-listing");
    setPendingPhoto(null);
    setOpenListingMenuId(null);
    setListingForm({
      name: listing.name,
      price: String(listing.price),
      description: listing.description,
      contact: listing.contact,
      category: listing.category,
      photo: listing.photo || "",
    });
    document.getElementById("seller-listings")?.scrollIntoView({ behavior: "smooth" });
  };

  const handleDeleteListing = async (listingId) => {
    if (!currentUser) {
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/items/${listingId}?seller_id=${currentUser.id}`, {
        method: "DELETE",
      });

      const data = await parseResponse(response, "Unable to remove listing");
      await loadListings();
      setOpenListingMenuId(null);
      showToast(data.message || "Listing removed successfully.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to remove listing");
    } finally {
      setIsSubmitting(false);
    }
  };

  const myListings = currentUser ? listings.filter((listing) => listing.seller_id === currentUser.id) : [];

  return (
    <div className="home-page">
      <header className="navbar">
        <div className="brand">
          <img src={logo} alt="USP logo" className="usp-logo" />
          <span>USP Marketplace</span>
        </div>

        <nav className="nav-links">
          <a href="#home">Home</a>
          <a href="#listings">Browse</a>
          <a href="#categories">Categories</a>
          <a href="#seller-listings">Sell</a>
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

      {toastMessage && (
        <div className="toast-message" role="status">
          {toastMessage}
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
                <input type="text" name="username" value={authForm.username} onChange={handleAuthFieldChange} required />
              </label>

              {authMode === "signup" && (
                <div>
                  <label>
                    Email
                    <input
                      type="email"
                      name="email"
                      value={authForm.email}
                      onChange={handleAuthFieldChange}
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
                  value={authForm.password}
                  onChange={handleAuthFieldChange}
                  required
                />
              </label>

              {formMessage && <p className="auth-message">{formMessage}</p>}

              <button type="submit" className="auth-submit" disabled={isSubmitting}>
                {isSubmitting ? "Please wait..." : authMode === "signup" ? "Sign Up" : "Login"}
              </button>
            </form>
          </div>
        </div>
      )}

      <section className="hero" id="home">
        <h1>Buy and Sell With USP Students</h1>
        <p>A simple marketplace for USP students to buy and sell items within the university community.</p>

        <div className="search-bar">
          <input type="text" placeholder="Search for books, electronics, clothing..." />
          <button type="button">Search</button>
        </div>
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

      <section className="seller-section" id="seller-listings">
        <div className="section-heading">
          <h2>My Listings</h2>
          <p>Create and manage the items you want to sell.</p>
        </div>

        {currentUser ? (
          <>
            <div className="seller-tabs" role="tablist" aria-label="Seller listing sections">
              <button
                type="button"
                role="tab"
                aria-selected={activeSellerTab === "my-listings"}
                className={activeSellerTab === "my-listings" ? "seller-tab active" : "seller-tab"}
                onClick={() => setActiveSellerTab("my-listings")}
              >
                My Listings
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeSellerTab === "add-listing"}
                className={activeSellerTab === "add-listing" ? "seller-tab active" : "seller-tab"}
                onClick={() => {
                  resetListingForm();
                  setActiveSellerTab("add-listing");
                }}
              >
                Add Listing
              </button>
            </div>

            {activeSellerTab === "add-listing" ? (
              <form className="listing-form" onSubmit={handleListingSubmit}>
                <label>
                  JPG Photo
                  <input
                    type="file"
                    accept=".jpg,.jpeg,image/jpeg"
                    onChange={handlePhotoChange}
                  />
                </label>

                {listingForm.photo && (
                  <div className="confirmed-photo">
                    <div className="photo-preview">
                      <img src={listingForm.photo} alt="Confirmed listing" />
                    </div>
                    <div>
                      <strong>Photo ready</strong>
                      <p>This photo will be saved with the listing.</p>
                      <button type="button" className="secondary-button" onClick={removePhoto}>
                        Remove Photo
                      </button>
                    </div>
                  </div>
                )}

                {pendingPhoto && (
                  <div className="photo-review">
                    <div className="photo-preview">
                      <img src={pendingPhoto.dataUrl} alt="Photo selected for review" />
                    </div>
                    <div className="photo-review-details">
                      <span>Review JPG Photo</span>
                      <strong>{pendingPhoto.name}</strong>
                      <p>Check the image before attaching it to your listing.</p>
                      <div className="photo-review-actions">
                        <button type="button" className="auth-submit" onClick={confirmPhoto}>
                          Use This Photo
                        </button>
                        <button type="button" className="secondary-button" onClick={removePhoto}>
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <label>
                  Item Name
                  <input
                    type="text"
                    name="name"
                    value={listingForm.name}
                    onChange={handleListingFieldChange}
                    placeholder="Computer Science Textbook"
                    required
                  />
                </label>

                <label>
                  Price
                  <input
                    type="number"
                    name="price"
                    value={listingForm.price}
                    onChange={handleListingFieldChange}
                    min="0"
                    step="0.01"
                    placeholder="30.00"
                    required
                  />
                </label>

                <label>
                  Category
                  <select name="category" value={listingForm.category} onChange={handleListingFieldChange} required>
                    {categories.map((category) => (
                      <option value={category.name} key={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Contact
                  <input
                    type="text"
                    name="contact"
                    value={listingForm.contact}
                    onChange={handleListingFieldChange}
                    placeholder="Phone, email, or preferred contact"
                    required
                  />
                </label>

                <label className="listing-description">
                  Description
                  <textarea
                    name="description"
                    value={listingForm.description}
                    onChange={handleListingFieldChange}
                    placeholder="Condition, pickup location, or extra details"
                    rows="4"
                    required
                  />
                </label>

                <div className="listing-actions">
                  <button type="submit" className="auth-submit" disabled={isSubmitting}>
                    {isSubmitting ? "Saving..." : editingListingId ? "Update Listing" : "Add Listing"}
                  </button>
                  {editingListingId && (
                    <button type="button" className="secondary-button" onClick={resetListingForm}>
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            ) : (
              <div className="my-listings">
                <h3>My Listings</h3>
                {myListings.length ? (
                  <div className="seller-list">
                    {myListings.map((listing) => (
                      <div className="seller-list-item" key={listing.id}>
                        <div className="seller-list-details">
                          <strong>{listing.name}</strong>
                          <span>${Number(listing.price).toFixed(2)} - {listing.category}</span>
                        </div>
                        <div className="listing-menu">
                          <button
                            type="button"
                            className="listing-menu-button"
                            aria-label={`Open actions for ${listing.name}`}
                            aria-expanded={openListingMenuId === listing.id}
                            onClick={() =>
                              setOpenListingMenuId((currentId) => (currentId === listing.id ? null : listing.id))
                            }
                          >
                            ...
                          </button>
                          {openListingMenuId === listing.id && (
                            <div className="listing-menu-panel">
                              <button type="button" onClick={() => handleEditListing(listing)}>
                                Edit
                              </button>
                              <button
                                type="button"
                                className="danger-button"
                                onClick={() => handleDeleteListing(listing.id)}
                              >
                                Remove
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">You have not listed any items yet.</p>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="signin-prompt">
            <p>Login or sign up to create and manage your item listings.</p>
            <button type="button" className="auth-submit" onClick={() => openAuth("login")}>
              Login to Sell
            </button>
          </div>
        )}
      </section>

      <section className="listings" id="listings">
        <div className="section-heading">
          <h2>Recent Listings</h2>
          <p>This section updates automatically as sellers add items.</p>
        </div>

        {isLoadingListings ? (
          <p className="empty-state">Loading listings...</p>
        ) : listings.length ? (
          <div className="product-container">
            {listings.map((listing) => (
              <div className="product-card" key={listing.id}>
                <div className="product-image">
                  {listing.photo ? <img src={listing.photo} alt={listing.name} /> : <span>{listing.category}</span>}
                </div>
                <div className="product-details">
                  <div className="product-meta">{listing.category}</div>
                  <h3>{listing.name}</h3>
                  <p className="product-price">${Number(listing.price).toFixed(2)}</p>
                  <p className="product-description">{listing.description}</p>
                  <p className="seller-contact">Seller: {listing.seller_username}</p>
                  <p className="seller-contact">Contact: {listing.contact}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">No seller listings yet.</p>
        )}
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
