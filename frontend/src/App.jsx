import React, { useEffect, useState } from "react";
import "./Home.css";
import AccountPage from "./components/AccountPage";
import AdminDashboard from "./components/AdminDashboard";
import AuthModal from "./components/AuthModal";
import CartPage from "./components/CartPage";
import CategoriesSection from "./components/CategoriesSection";
import CategoryPage from "./components/CategoryPage";
import Footer from "./components/Footer";
import HeroSection from "./components/HeroSection";
import InfoSection from "./components/InfoSection";
import ListingsSection from "./components/ListingsSection";
import LegalPage from "./components/LegalPage";
import Navbar from "./components/Navbar";
import PastPurchasesPage from "./components/PastPurchasesPage";
import ProductModal from "./components/ProductModal";
import SellerPanel from "./components/SellerPanel";
import Toast from "./components/Toast";
import { EMPTY_AUTH_FORM, EMPTY_LISTING_FORM } from "./constants/forms";
import { categories } from "./data/categories";
import logo from "../logo.png";

const API_URL = "http://localhost:8000/api";

function Home() {
  const [authMode, setAuthMode] = useState("login");
  const [verificationEmail, setVerificationEmail] = useState("");
  const [authenticatorUserId, setAuthenticatorUserId] = useState(null);
  const [authenticatorSecret, setAuthenticatorSecret] = useState("");
  const [authenticatorUri, setAuthenticatorUri] = useState("");
  const [authenticatorQr, setAuthenticatorQr] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
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
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [sortOption, setSortOption] = useState("newest");
  const [selectedListing, setSelectedListing] = useState(null);
  const [showSellerPanel, setShowSellerPanel] = useState(false);
  const [activeCategoryPage, setActiveCategoryPage] = useState(null);
  const [cartItems, setCartItems] = useState([]);
  const [showCartPanel, setShowCartPanel] = useState(false);
  const [showPurchasesPage, setShowPurchasesPage] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [purchaseHistory, setPurchaseHistory] = useState([]);
  const [activeLegalPage, setActiveLegalPage] = useState(null);
  const [activeAccountPage, setActiveAccountPage] = useState(null);
  const [showAdminDashboard, setShowAdminDashboard] = useState(() =>
    window.location.pathname.startsWith("/admin")
  );

  useEffect(() => {
    loadListings();
  }, []);

  useEffect(() => {
    const handleRouteChange = () => {
      setShowAdminDashboard(window.location.pathname.startsWith("/admin"));
    };

    window.addEventListener("popstate", handleRouteChange);
    return () => window.removeEventListener("popstate", handleRouteChange);
  }, []);

  useEffect(() => {
    if (currentUser) {
      loadPurchaseHistory(currentUser.id);
    } else {
      setPurchaseHistory([]);
    }
  }, [currentUser]);

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

  const showToast = (message, type = "success") => {
    setToastMessage("");
    setToastType(type);
    window.setTimeout(() => setToastMessage(message), 10);
  };

  const loadListings = async () => {
    setIsLoadingListings(true);

    try {
      const response = await fetch(`${API_URL}/items`);
      const data = await parseResponse(response, "Unable to load listings");
      setListings(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load listings", "error");
    } finally {
      setIsLoadingListings(false);
    }
  };

  const loadPurchaseHistory = async (buyerId) => {
    try {
      const response = await fetch(`${API_URL}/users/${buyerId}/purchases`);
      const data = await parseResponse(response, "Unable to load purchase history");
      setPurchaseHistory(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load purchase history", "error");
    }
  };

  const resetAuth = () => {
    setAuthMode(null);
    setVerificationEmail("");
    setFormMessage("");
    setEmailError("");
    setAuthenticatorUserId(null);
    setAuthenticatorSecret("");
    setAuthenticatorUri("");
    setAuthenticatorQr("");
  };

  const cancelVerification = async () => {
    const email = verificationEmail;
    resetAuth();

    if (!email) {
      return;
    }

    try {
      await fetch(`${API_URL}/users/cancel-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
    } catch {
      // Closing the dialog should still work if the API is unavailable.
    }
  };

  const validateUSPEmail = (email) => {
    if (!email) {
      setEmailError("");
      return true;
    }

    const isValid = /^S\d+@student\.usp\.ac\.fj$/i.test(email.trim());
    setEmailError(isValid ? "" : "Use your USP student email, for example S12345678@student.usp.ac.fj");
    return isValid;
  };

  const validateUsername = (username) => {
    const normalizedUsername = username.trim();
    return normalizedUsername.length >= 3 && /^[a-zA-Z0-9_-]+$/.test(normalizedUsername);
  };

  const handleAuthFieldChange = (event) => {
    const { name, value } = event.target;
    setAuthForm((previous) => ({ ...previous, [name]: value }));
    setFormMessage("");

    if (name === "email" && authMode === "signup") {
      validateUSPEmail(value);
    }
  };

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setFormMessage("");

    try {
      if (authMode === "verify-email") {
        const response = await fetch(`${API_URL}/users/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: verificationEmail, code: authForm.verification_code }),
        });
        const data = await parseResponse(response, "Email verification failed");
        if (data.authenticator_setup_required) {
          setAuthenticatorUserId(data.user_id);
          setAuthenticatorSecret(data.authenticator_secret);
          setAuthenticatorUri(data.authenticator_uri);
          setAuthenticatorQr(data.authenticator_qr);
          setAuthForm((previous) => ({ ...previous, verification_code: "", authenticator_code: "" }));
          setAuthMode("authenticator-setup");
        } else {
          setCurrentUser(data.user);
          setAuthForm(EMPTY_AUTH_FORM);
          setAuthMode(null);
          setVerificationEmail("");
          showToast(data.message || "Email verified successfully.");
        }
        return;
      }

      if (authMode === "authenticator" || authMode === "authenticator-setup") {
        const response = await fetch(`${API_URL}/users/verify-authenticator`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: authenticatorUserId, code: authForm.authenticator_code }),
        });
        const data = await parseResponse(response, "Authenticator verification failed");
        setCurrentUser(data.user);
        setAuthForm(EMPTY_AUTH_FORM);
        setAuthMode(null);
        setVerificationEmail("");
        setAuthenticatorUserId(null);
        setAuthenticatorSecret("");
        setAuthenticatorUri("");
        setAuthenticatorQr("");
        showToast(data.message || "Login successful.");
        return;
      }

      if (authMode === "forgot-password") {
        if (!validateUSPEmail(authForm.email)) {
          setFormMessage("Please enter your USP student email address");
          return;
        }
        const response = await fetch(`${API_URL}/users/request-password-reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authForm.email.trim() }),
        });
        const data = await parseResponse(response, "Unable to request a password reset");
        setVerificationEmail(authForm.email.trim());
        setAuthForm((previous) => ({ ...previous, reset_code: "", new_password: "", new_password_confirmation: "" }));
        setAuthMode("reset-password");
        showToast(data.message);
        return;
      }

      if (authMode === "reset-password") {
        if (authForm.new_password !== authForm.new_password_confirmation) {
          setFormMessage("Passwords do not match");
          return;
        }
        const response = await fetch(`${API_URL}/users/reset-password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: verificationEmail,
            code: authForm.reset_code,
            password: authForm.new_password,
          }),
        });
        const data = await parseResponse(response, "Unable to reset your password");
        setAuthForm(EMPTY_AUTH_FORM);
        setVerificationEmail("");
        setAuthMode("login");
        showToast(data.message);
        return;
      }

      if (authMode === "signup" && !validateUsername(authForm.username)) {
        setFormMessage("Username must be at least 3 characters and use only letters, numbers, hyphens, or underscores");
        return;
      }

      if (authMode === "signup" && !validateUSPEmail(authForm.email)) {
        setFormMessage("Please enter your USP student email address");
        return;
      }

      if (authMode === "signup" && authForm.password !== authForm.password_confirmation) {
        setFormMessage("Passwords do not match");
        return;
      }

      const endpoint = authMode === "signup" ? "/users/signup" : "/users/login";
      const payload =
        authMode === "signup"
          ? { ...authForm, username: authForm.username.trim() }
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

      if (data.authenticator_setup_required || data.authenticator_required) {
        setAuthenticatorUserId(data.user_id);
        setAuthenticatorSecret(data.authenticator_secret || "");
        setAuthenticatorUri(data.authenticator_uri || "");
        setAuthenticatorQr(data.authenticator_qr || "");
        setAuthForm((previous) => ({ ...previous, authenticator_code: "" }));
        setAuthMode(data.authenticator_setup_required ? "authenticator-setup" : "authenticator");
        return;
      }

      if (authMode === "signup" && data.verification_required) {
        setVerificationEmail(authForm.email.trim());
        setAuthForm((previous) => ({ ...previous, verification_code: "" }));
        setAuthMode("verify-email");
        showToast("Registration started. Check your USP email for the verification code.");
        return;
      }

      setCurrentUser(data.user);
      setAuthForm(EMPTY_AUTH_FORM);
      setAuthMode(null);
      if (data.user?.role === "admin") {
        hideActivePages();
        setShowAdminDashboard(true);
        window.history.pushState({}, "", "/admin/dashboard");
      }
      showToast(authMode === "signup" ? "Registration successful. Welcome to USP Marketplace!" : data.message || "Login successful!");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong";
      setFormMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resendVerification = async () => {
    setIsSubmitting(true);
    setFormMessage("");
    try {
      const response = await fetch(`${API_URL}/users/resend-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: verificationEmail }),
      });
      const data = await parseResponse(response, "Unable to resend verification code");
      showToast(data.message);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Unable to resend verification code");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setFormMessage("");
    setEmailError("");
  };

  const resetListingForm = () => {
    setListingForm(EMPTY_LISTING_FORM);
    setPendingPhoto(null);
    setEditingListingId(null);
  };

  const hideActivePages = () => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(null);
    setActiveAccountPage(null);
    setOpenListingMenuId(null);
    resetListingForm();
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setAuthMode("login");
    hideActivePages();
    window.history.pushState({}, "", "/");
    showToast("Logged out successfully.");
  };

  const openMarketplace = () => {
    hideActivePages();
    window.history.pushState({}, "", "/");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (!currentUser && !showAdminDashboard) {
    return (
      <AuthModal
        authMode={authMode || "login"}
        authForm={authForm}
        emailError={emailError}
        formMessage={formMessage}
        isSubmitting={isSubmitting}
        verificationEmail={verificationEmail}
        onClose={resetAuth}
        onSubmit={handleAuthSubmit}
        onFieldChange={handleAuthFieldChange}
        onResendVerification={resendVerification}
        onCancelVerification={cancelVerification}
        standalone
        onSwitchMode={openAuth}
        authenticatorSecret={authenticatorSecret}
        authenticatorUri={authenticatorUri}
        authenticatorQr={authenticatorQr}
      />
    );
  }

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
      showToast("Please upload a JPG photo only.", "error");
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
      showToast("Unable to read the selected photo.", "error");
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

  const handleListingSubmit = async (event) => {
    event.preventDefault();

    if (!currentUser) {
      openAuth("login");
      return;
    }

    setIsSubmitting(true);

    try {
      if (pendingPhoto) {
        showToast("Please confirm the selected photo before adding the listing.", "error");
        return;
      }

      if (listingForm.stock === "") {
        showToast("Please enter the number of units in stock.", "error");
        return;
      }

      const payload = {
        ...listingForm,
        price: Number(listingForm.price),
        stock: Number(listingForm.stock),
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
      showToast(error instanceof Error ? error.message : "Something went wrong", "error");
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
      stock: String(listing.stock ?? 1),
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
      showToast(error instanceof Error ? error.message : "Unable to remove listing", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const myListings = currentUser ? listings.filter((listing) => listing.seller_id === currentUser.id) : [];
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredListings = listings
    .filter((listing) => {
      const matchesSearch =
        !normalizedSearch ||
        listing.name.toLowerCase().includes(normalizedSearch) ||
        listing.description.toLowerCase().includes(normalizedSearch) ||
        listing.category.toLowerCase().includes(normalizedSearch) ||
        listing.seller_username.toLowerCase().includes(normalizedSearch);
      const matchesCategory =
        selectedCategory === "All" || listing.category === selectedCategory;

      return matchesSearch && matchesCategory;
    })
    .sort((first, second) => {
      if (sortOption === "oldest") {
        return first.id - second.id;
      }

      if (sortOption === "name-asc") {
        return first.name.localeCompare(second.name);
      }

      if (sortOption === "name-desc") {
        return second.name.localeCompare(first.name);
      }

      if (sortOption === "price-asc") {
        return Number(first.price) - Number(second.price);
      }

      if (sortOption === "price-desc") {
        return Number(second.price) - Number(first.price);
      }

      return second.id - first.id;
    });
  const activeCategoryListings =
    activeCategoryPage
      ? listings.filter((listing) => listing.category === activeCategoryPage)
      : [];
  const searchSuggestions = normalizedSearch
    ? listings
        .filter(
          (listing) =>
            listing.name.toLowerCase().includes(normalizedSearch) ||
            listing.category.toLowerCase().includes(normalizedSearch)
        )
        .slice(0, 5)
    : [];
  const cartTotal = cartItems.reduce((total, item) => total + Number(item.price), 0);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    hideActivePages();
    document.getElementById("listings")?.scrollIntoView({ behavior: "smooth" });
  };

  const chooseCategory = (categoryName) => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveAccountPage(null);
    setSearchQuery("");
    setSelectedCategory(categoryName);
    if (categoryName === "All") {
      setActiveCategoryPage(null);
      document.getElementById("categories")?.scrollIntoView({ behavior: "smooth" });
      return;
    }

    setActiveCategoryPage(categoryName);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleBrowse = () => {
    hideActivePages();
    setSearchQuery("");
    setSelectedCategory("All");
    window.setTimeout(() => {
      document.getElementById("listings")?.scrollIntoView({ behavior: "smooth" });
    }, 0);
  };

  const openSellerTab = (tabName) => {
    if (!currentUser) {
      openAuth("login");
      return;
    }

    if (tabName === "add-listing") {
      resetListingForm();
    }

    setShowSellerPanel(true);
    setShowAdminDashboard(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(null);
    setActiveAccountPage(null);
    setActiveSellerTab(tabName);
    window.setTimeout(() => {
      document.getElementById("seller-listings")?.scrollIntoView({ behavior: "smooth" });
    }, 0);
  };

  const openCart = () => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(null);
    setActiveAccountPage(null);
    setShowCartPanel(true);
    window.setTimeout(() => {
      document.getElementById("cart")?.scrollIntoView({ behavior: "smooth" });
    }, 0);
  };

  const openPurchasesPage = () => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowCartPanel(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(null);
    setActiveAccountPage(null);
    setShowPurchasesPage(true);
    if (!currentUser) {
      openAuth("login");
    }
    window.setTimeout(() => {
      document.getElementById("past-purchases")?.scrollIntoView({ behavior: "smooth" });
    }, 0);
  };

  const addToCart = (listing) => {
    if (!currentUser) {
      setSelectedListing(null);
      showToast("Please login to add items to cart.", "error");
      openAuth("login");
      return;
    }

    if (listing.seller_id === currentUser.id) {
      setSelectedListing(null);
      showToast("You cannot add your own listing to cart.", "error");
      return;
    }

    if (listing.status === "sold" || Number(listing.stock) <= 0) {
      setSelectedListing(null);
      showToast("This item is sold out.", "error");
      return;
    }

    const alreadyInCart = cartItems.some((item) => item.id === listing.id);

    if (alreadyInCart) {
      setSelectedListing(null);
      showToast("Item is already in your cart.", "error");
      return;
    }

    setCartItems((currentItems) => [...currentItems, listing]);
    setReceipt(null);
    setSelectedListing(null);
    showToast("Item successfully added to cart.");
  };

  const checkoutCart = async () => {
    if (!currentUser) {
      showToast("Please login to purchase items.", "error");
      openAuth("login");
      return;
    }

    const availableItems = cartItems.filter((item) => item.status !== "sold" && Number(item.stock) > 0);
    if (!availableItems.length) {
      showToast("No available items to checkout.", "error");
      return;
    }

    setIsSubmitting(true);

    try {
      const purchasedItems = [];

      for (const item of availableItems) {
        const response = await fetch(`${API_URL}/items/${item.id}/purchase?buyer_id=${currentUser.id}`, {
          method: "POST",
        });
        const purchasedItem = await parseResponse(response, `Unable to purchase ${item.name}`);
        purchasedItems.push(purchasedItem);
      }

      const purchasedIds = purchasedItems.map((item) => item.id);
      setCartItems((currentItems) => currentItems.filter((item) => !purchasedIds.includes(item.id)));
      setListings((currentListings) =>
        currentListings.map((listing) => purchasedItems.find((item) => item.id === listing.id) || listing)
      );
      await loadPurchaseHistory(currentUser.id);
      setReceipt({
        id: `USP-${Date.now()}`,
        purchasedAt: new Date().toLocaleString(),
        items: purchasedItems,
        total: availableItems.reduce((total, item) => total + Number(item.price), 0),
      });
      showToast("Checkout successful.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to checkout", "error");
      await loadListings();
    } finally {
      setIsSubmitting(false);
    }
  };

  const removeFromCart = (listingId) => {
    setCartItems((currentItems) => currentItems.filter((item) => item.id !== listingId));
    setReceipt(null);
    showToast("Item removed from cart.");
  };

  const handleSuggestionSelect = (listing) => {
    setSearchQuery(listing.name);
    document.getElementById("listings")?.scrollIntoView({ behavior: "smooth" });
  };

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedCategory("All");
    setSortOption("newest");
  };

  const openLegalPage = (page) => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(page);
    setActiveAccountPage(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openAccountPage = (page) => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(null);
    setActiveAccountPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="home-page">
      {showAdminDashboard ? (
        <>
          <Toast message={toastMessage} type={toastType} />
          <AuthModal
            authMode={authMode}
            authForm={authForm}
            emailError={emailError}
            formMessage={formMessage}
            isSubmitting={isSubmitting}
            verificationEmail={verificationEmail}
            onClose={resetAuth}
            onSubmit={handleAuthSubmit}
            onFieldChange={handleAuthFieldChange}
            onResendVerification={resendVerification}
            onCancelVerification={cancelVerification}
          />
          <AdminDashboard
            apiUrl={API_URL}
            currentUser={currentUser}
            logo={logo}
            onLogin={() => openAuth("login")}
            onLogout={handleLogout}
            onMarketplace={openMarketplace}
            showToast={showToast}
          />
        </>
      ) : (
        <>
      <Navbar
        logo={logo}
        currentUser={currentUser}
        cartCount={cartItems.length}
        onHome={hideActivePages}
        onBrowse={handleBrowse}
        onOpenSellerTab={openSellerTab}
        onOpenPurchases={openPurchasesPage}
        onOpenCart={openCart}
        onOpenAccountPage={openAccountPage}
        onOpenAuth={openAuth}
        onLogout={handleLogout}
      />

      <Toast message={toastMessage} type={toastType} />

      <AuthModal
        authMode={authMode}
        authForm={authForm}
        emailError={emailError}
        formMessage={formMessage}
        isSubmitting={isSubmitting}
        verificationEmail={verificationEmail}
        onClose={resetAuth}
        onSubmit={handleAuthSubmit}
        onFieldChange={handleAuthFieldChange}
        onResendVerification={resendVerification}
        onCancelVerification={cancelVerification}
      />

      <CategoryPage
        categoryName={activeCategoryPage}
        listings={activeCategoryListings}
        onBack={() => setActiveCategoryPage(null)}
        onSelectListing={setSelectedListing}
      />

      {showCartPanel && (
        <CartPage
          cartItems={cartItems}
          cartTotal={cartTotal}
          receipt={receipt}
          onClose={() => setShowCartPanel(false)}
          onCheckout={checkoutCart}
          onClearReceipt={() => setReceipt(null)}
          onRemove={removeFromCart}
          isSubmitting={isSubmitting}
        />
      )}

      {showPurchasesPage && (
        <PastPurchasesPage
          currentUser={currentUser}
          purchases={purchaseHistory}
          onBack={hideActivePages}
          onLogin={() => openAuth("login")}
        />
      )}

      <AccountPage
        page={activeAccountPage}
        currentUser={currentUser}
        myListings={myListings}
        purchaseHistory={purchaseHistory}
        onBack={hideActivePages}
      />

      <LegalPage page={activeLegalPage} onBack={hideActivePages} />

      {!activeCategoryPage && !showCartPanel && !showPurchasesPage && !activeLegalPage && !activeAccountPage && (
        <>
          <HeroSection
            searchQuery={searchQuery}
            suggestions={searchSuggestions}
            onSearchChange={setSearchQuery}
            onSearchSubmit={handleSearchSubmit}
            onSuggestionSelect={handleSuggestionSelect}
          />

          <CategoriesSection
            categories={categories}
            selectedCategory={selectedCategory}
            onChooseCategory={chooseCategory}
          />

          {showSellerPanel && (
            <SellerPanel
              activeSellerTab={activeSellerTab}
              categories={categories}
              currentUser={currentUser}
              editingListingId={editingListingId}
              isSubmitting={isSubmitting}
              listingForm={listingForm}
              myListings={myListings}
              openListingMenuId={openListingMenuId}
              pendingPhoto={pendingPhoto}
              onClose={hideActivePages}
              onDeleteListing={handleDeleteListing}
              onEditListing={handleEditListing}
              onFieldChange={handleListingFieldChange}
              onLogin={() => openAuth("login")}
              onMenuToggle={(listingId) =>
                setOpenListingMenuId((currentId) => (currentId === listingId ? null : listingId))
              }
              onPhotoChange={handlePhotoChange}
              onPhotoConfirm={confirmPhoto}
              onPhotoRemove={removePhoto}
              onResetForm={resetListingForm}
              onSubmit={handleListingSubmit}
            />
          )}

          <ListingsSection
            categories={categories}
            filteredListings={filteredListings}
            isLoadingListings={isLoadingListings}
            searchQuery={searchQuery}
            selectedCategory={selectedCategory}
            sortOption={sortOption}
            onClearFilters={clearFilters}
            onSelectCategory={setSelectedCategory}
            onSelectListing={setSelectedListing}
            onSortChange={setSortOption}
          />

          <InfoSection />
        </>
      )}

      <ProductModal
        listing={selectedListing}
        currentUser={currentUser}
        onClose={() => setSelectedListing(null)}
        onAddToCart={addToCart}
      />

      <Footer logo={logo} onLegalNavigate={openLegalPage} />
        </>
      )}
    </div>
  );
}

export default Home;
