import React, { useEffect, useRef, useState } from "react";
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
import ProductCard from "./components/ProductCard";
import ProductModal from "./components/ProductModal";
import SellerPanel from "./components/SellerPanel";
import Toast from "./components/Toast";
// FUTURE MICROSOFT ENTRA INTEGRATION: enable this import after USP provides tenant details.
// import { microsoftLoginAvailable, microsoftLogin } from "./auth/microsoft";
// FUTURE MICROSOFT ENTRA INTEGRATION: restore this when USP provides tenant configuration.
// const microsoftLoginAvailable = true;
import { EMPTY_AUTH_FORM, EMPTY_LISTING_FORM } from "./constants/forms";
import { categories } from "./data/categories";
import logo from "../logo.png";

const API_URL = "http://localhost:8000/api";
const PENDING_VERIFICATION_STORAGE_KEY = "usp-marketplace-pending-verification";

function readPendingVerification() {
  try {
    const pending = JSON.parse(window.sessionStorage.getItem(PENDING_VERIFICATION_STORAGE_KEY) || "null");
    if (
      pending &&
      typeof pending.email === "string" &&
      pending.email &&
      typeof pending.pendingToken === "string"
    ) {
      return pending;
    }
    window.sessionStorage.removeItem(PENDING_VERIFICATION_STORAGE_KEY);
  } catch {
    return null;
  }
  return null;
}

function Home() {
  const [storedPendingVerification] = useState(readPendingVerification);
  const [authMode, setAuthMode] = useState(storedPendingVerification ? "verify-email" : "login");
  const [verificationEmail, setVerificationEmail] = useState(storedPendingVerification?.email || "");
  const [verificationToken, setVerificationToken] = useState(storedPendingVerification?.pendingToken || "");
  const [resendAvailableAt, setResendAvailableAt] = useState(0);
  const [resendSecondsRemaining, setResendSecondsRemaining] = useState(0);
  const [authenticatorUserId, setAuthenticatorUserId] = useState(null);
  const [authenticatorSecret, setAuthenticatorSecret] = useState("");
  const [authenticatorUri, setAuthenticatorUri] = useState("");
  const [authenticatorQr, setAuthenticatorQr] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const lastToastRef = useRef({ message: "", shownAt: 0 });
  const [formMessage, setFormMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [authForm, setAuthForm] = useState(EMPTY_AUTH_FORM);
  const [listingForm, setListingForm] = useState(EMPTY_LISTING_FORM);
  const [pendingPhoto, setPendingPhoto] = useState(null);
  const [listings, setListings] = useState([]);
  const [sellerListings, setSellerListings] = useState([]);
  const [editingListingId, setEditingListingId] = useState(null);
  const [isLoadingListings, setIsLoadingListings] = useState(false);
  const [activeSellerTab, setActiveSellerTab] = useState("my-listings");
  const [openListingMenuId, setOpenListingMenuId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [sortOption, setSortOption] = useState("newest");
  const [selectedListing, setSelectedListing] = useState(null);
  const [selectedSeller, setSelectedSeller] = useState(null);
  const [selectedSellerReviews, setSelectedSellerReviews] = useState(null);
  const [isLoadingSellerReviews, setIsLoadingSellerReviews] = useState(false);
  const [showSellerPanel, setShowSellerPanel] = useState(false);
  const [showShopPage, setShowShopPage] = useState(false);
  const [activeCategoryPage, setActiveCategoryPage] = useState(null);
  const [cartItems, setCartItems] = useState([]);
  const [showCartPanel, setShowCartPanel] = useState(false);
  const [showPurchasesPage, setShowPurchasesPage] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [pendingReviewItems, setPendingReviewItems] = useState([]);
  const [checkoutReviewForm, setCheckoutReviewForm] = useState({ rating: "5", review: "" });
  const [purchaseHistory, setPurchaseHistory] = useState([]);
  const [sellerOrders, setSellerOrders] = useState([]);
  const [activeLegalPage, setActiveLegalPage] = useState(null);
  const [activeAccountPage, setActiveAccountPage] = useState(null);
  const [activeSalesView, setActiveSalesView] = useState("active");
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [unreadMessageCount, setUnreadMessageCount] = useState(0);
  const [userNotifications, setUserNotifications] = useState([]);
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
      loadListings();
      loadSellerListings(currentUser.id);
      loadPurchaseHistory(currentUser.id);
      loadSellerOrders(currentUser.id);
      loadConversations(currentUser.id);
      loadUnreadMessageCount(currentUser.id);
      loadUserNotifications(currentUser.id);
    } else {
      setSellerListings([]);
      setPurchaseHistory([]);
      setSellerOrders([]);
      setConversations([]);
      setActiveConversationId(null);
      setUnreadMessageCount(0);
      setUserNotifications([]);
    }
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      loadUserNotifications(currentUser.id, { silent: true });
    }, 15000);

    return () => window.clearInterval(intervalId);
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

  useEffect(() => {
    if (authMode !== "verify-email" || !resendAvailableAt) {
      setResendSecondsRemaining(0);
      return undefined;
    }

    const updateCountdown = () => {
      setResendSecondsRemaining(Math.max(0, Math.ceil((resendAvailableAt - Date.now()) / 1000)));
    };
    updateCountdown();
    const intervalId = window.setInterval(updateCountdown, 1000);
    return () => window.clearInterval(intervalId);
  }, [authMode, resendAvailableAt]);

  const startResendCountdown = () => {
    setResendAvailableAt(Date.now() + 60_000);
  };

  const parseResponse = async (response, fallbackMessage) => {
    const responseBody = await response.text();
    let data = null;
    try {
      data = responseBody ? JSON.parse(responseBody) : null;
    } catch {
      throw new Error(
        `Server returned an unreadable response (HTTP ${response.status}). Check the backend terminal for details.`
      );
    }

    if (!response.ok) {
      const detail = data?.detail || data?.message || fallbackMessage;
      if (response.status === 503 || /database unavailable/i.test(detail)) {
        throw new Error("Marketplace database is unavailable. Start MySQL in XAMPP, then refresh the page.");
      }
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }

    if (data === null) {
      throw new Error("Server returned an empty response");
    }

    return data;
  };

  const showToast = (message, type = "success") => {
    const now = Date.now();
    if (message === lastToastRef.current.message && now - lastToastRef.current.shownAt < 2500) {
      return;
    }
    lastToastRef.current = { message, shownAt: now };
    setToastMessage("");
    setToastType(type);
    window.setTimeout(() => setToastMessage(message), 10);
  };

  const loadListings = async () => {
    setIsLoadingListings(true);

    try {
      const viewerId = currentUser?.id;
      const query = viewerId ? `?user_id=${viewerId}` : "";
      const response = await fetch(`${API_URL}/items${query}`);
      const data = await parseResponse(response, "Unable to load listings");
      setListings(data);
      setCartItems((items) =>
        items.map((cartItem) => {
          const latestListing = data.find((listing) => listing.id === cartItem.id);
          return latestListing ? { ...latestListing, quantity: cartItem.quantity } : cartItem;
        })
      );
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
      return data;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load purchase history", "error");
      return [];
    }
  };

  const loadSellerListings = async (sellerId) => {
    try {
      const viewerId = currentUser?.id;
      const query = viewerId ? `?viewer_id=${viewerId}` : "";
      const response = await fetch(`${API_URL}/users/${sellerId}/items${query}`);
      const data = await parseResponse(response, "Unable to load your listings");
      setSellerListings(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load your listings", "error");
    }
  };

  const resetAuth = () => {
    setAuthMode(null);
    setVerificationEmail("");
    setVerificationToken("");
    setResendAvailableAt(0);
    setResendSecondsRemaining(0);
    setFormMessage("");
    setEmailError("");
    setAuthenticatorUserId(null);
    setAuthenticatorSecret("");
    setAuthenticatorUri("");
    setAuthenticatorQr("");
  };

  const cancelVerification = async () => {
    const email = verificationEmail;
    const pendingToken = verificationToken;
    if (!email) {
      resetAuth();
      return;
    }

    setIsSubmitting(true);
    setFormMessage("");
    try {
      const response = await fetch(`${API_URL}/users/cancel-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, pending_token: pendingToken }),
      });
      await parseResponse(response, "Unable to cancel registration");
      window.sessionStorage.removeItem(PENDING_VERIFICATION_STORAGE_KEY);
      resetAuth();
      setAuthMode("signup");
      setFormMessage("Registration cancelled. You can sign up again.");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Unable to cancel registration");
    } finally {
      setIsSubmitting(false);
    }
  };

  const validateEmail = (email) => {
    if (!email) {
      setEmailError("");
      return true;
    }

    const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    setEmailError(isValid ? "" : "Enter a valid email address");
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
      validateEmail(value);
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
          body: JSON.stringify({ email: verificationEmail, code: authForm.verification_code, pending_token: verificationToken }),
        });
        const data = await parseResponse(response, "Email verification failed");
        window.sessionStorage.removeItem(PENDING_VERIFICATION_STORAGE_KEY);
        if (data.authenticator_setup_required) {
          setAuthenticatorUserId(data.user_id);
          setAuthenticatorSecret(data.authenticator_secret);
          setAuthenticatorUri(data.authenticator_uri);
          setAuthenticatorQr(data.authenticator_qr);
          setAuthForm((previous) => ({ ...previous, verification_code: "", authenticator_code: "" }));
          setAuthMode("authenticator-setup");
          setResendAvailableAt(0);
        } else {
          setCurrentUser(data.user);
          setAuthForm(EMPTY_AUTH_FORM);
          setAuthMode(null);
          setVerificationEmail("");
          setVerificationToken("");
          setResendAvailableAt(0);
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
        setVerificationToken("");
        setAuthenticatorUserId(null);
        setAuthenticatorSecret("");
        setAuthenticatorUri("");
        setAuthenticatorQr("");
        showToast(data.message || "Login successful.");
        return;
      }

      if (authMode === "forgot-password") {
        if (!validateEmail(authForm.email)) {
          setFormMessage("Please enter a valid email address");
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
        setAuthMode("verify-reset-code");
        showToast(data.message);
        return;
      }

      if (authMode === "verify-reset-code") {
        const response = await fetch(`${API_URL}/users/verify-password-reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: verificationEmail,
            code: authForm.reset_code,
          }),
        });
        const data = await parseResponse(response, "Unable to verify your reset code");
        setAuthForm((previous) => ({ ...previous, new_password: "", new_password_confirmation: "" }));
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

      if (authMode === "signup" && !validateEmail(authForm.email)) {
        setFormMessage("Please enter a valid email address");
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
        const email = authForm.email.trim();
        const pendingToken = data.pending_token || "";
        window.sessionStorage.setItem(
          PENDING_VERIFICATION_STORAGE_KEY,
          JSON.stringify({ email, pendingToken }),
        );
        setVerificationEmail(email);
        setVerificationToken(pendingToken);
        setAuthForm((previous) => ({ ...previous, verification_code: "" }));
        setAuthMode("verify-email");
        startResendCountdown();
        showToast(data.message || "Verification code sent successfully");
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
        body: JSON.stringify({ email: verificationEmail, pending_token: verificationToken }),
      });
      const data = await parseResponse(response, "Unable to resend verification code");
      startResendCountdown();
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
    setShowShopPage(false);
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
        resendSecondsRemaining={resendSecondsRemaining}
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
    setListingForm((previous) => {
      if (name === "payment_method") {
        const usesMobilePayment = value === "mpaisa" || value === "mycash";
        return {
          ...previous,
          payment_method: value,
          payment_number: usesMobilePayment ? previous.payment_number || previous.contact : "",
        };
      }
      if (name === "contact") {
        return {
          ...previous,
          contact: value,
          payment_number:
            ["mpaisa", "mycash"].includes(previous.payment_method) &&
            (!previous.payment_number || previous.payment_number === previous.contact)
              ? value
              : previous.payment_number,
        };
      }
      return { ...previous, [name]: value };
    });
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
      await loadSellerListings(currentUser.id);
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
      payment_method: listing.payment_method || "cash",
      payment_number: listing.payment_number || "",
      photo: listing.photo || "",
    });
    document.getElementById("seller-listings")?.scrollIntoView({ behavior: "smooth" });
  };

  const handleViewOwnListing = (listing) => {
    setOpenListingMenuId(null);
    setSelectedListing(listing);
  };

  const loadConversations = async (userId, activeId = activeConversationId) => {
    try {
      const response = await fetch(`${API_URL}/users/${userId}/conversations`);
      const data = await parseResponse(response, "Unable to load messages");
      setConversations(data);
      if (!activeId && data.length) {
        setActiveConversationId(data[0].id);
      }
      return data;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load messages", "error");
      return [];
    }
  };

  const loadUnreadMessageCount = async (userId) => {
    try {
      const response = await fetch(`${API_URL}/users/${userId}/messages/unread`);
      const data = await parseResponse(response, "Unable to load unread messages");
      setUnreadMessageCount(data.unread_count || 0);
    } catch {
      setUnreadMessageCount(0);
    }
  };

  const loadUserNotifications = async (userId, options = {}) => {
    try {
      const response = await fetch(`${API_URL}/users/${userId}/notifications`);
      const data = await parseResponse(response, "Unable to load notifications");
      setUserNotifications(data);
    } catch (error) {
      if (!options.silent) {
        showToast(error instanceof Error ? error.message : "Unable to load notifications", "error");
      }
    }
  };

  const markUserNotificationViewed = async (notificationId) => {
    if (!currentUser) {
      return null;
    }

    try {
      const response = await fetch(`${API_URL}/users/${currentUser.id}/notifications/${notificationId}`, {
        method: "POST",
      });
      const updatedNotification = await parseResponse(response, "Unable to update notification");
      setUserNotifications((currentNotifications) =>
        currentNotifications.map((notification) =>
          notification.id === updatedNotification.id ? updatedNotification : notification
        )
      );
      return updatedNotification;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to update notification", "error");
      return null;
    }
  };

  const openUserNotification = async (notification) => {
    if (!notification) {
      return;
    }

    await markUserNotificationViewed(notification.id);

    if (notification.category === "message") {
      openAccountPage("messages");
      const latestConversations = conversations.length ? conversations : await loadConversations(currentUser.id);
      const unreadConversation = latestConversations.find((conversation) => conversation.unread_count > 0);
      const targetConversation = unreadConversation || latestConversations[0];
      if (targetConversation) {
        await openConversation(targetConversation.id);
      } else {
        await markUserNotificationsViewedByCategory("message");
        await loadUnreadMessageCount(currentUser.id);
      }
      return;
    }

    if (
      notification.category === "sale" ||
      (notification.category === "order" && /new order|placed an order/i.test(`${notification.title || ""} ${notification.message || ""}`))
    ) {
      await loadSellerOrders(currentUser.id);
      openAccountPage("sales", "history");
      await loadUserNotifications(currentUser.id);
      return;
    }

    if (notification.category === "order") {
      openPurchasesPage();
      await loadUserNotifications(currentUser.id);
      return;
    }

    if (notification.category === "listing" || /^Listing /i.test(notification.title || "")) {
      openSellerTab("my-listings");
      await loadUserNotifications(currentUser.id);
      return;
    }

    if (notification.category === "administration") {
      openAccountPage("profile");
      await loadUserNotifications(currentUser.id);
      return;
    }
  };

  const markUserNotificationsViewedByCategory = async (category) => {
    if (!currentUser) {
      return;
    }

    const unreadMatchingNotifications = userNotifications.filter(
      (notification) => notification.category === category && !notification.is_read
    );
    if (!unreadMatchingNotifications.length) {
      return;
    }

    await Promise.all(
      unreadMatchingNotifications.map((notification) =>
        fetch(`${API_URL}/users/${currentUser.id}/notifications/${notification.id}`, {
          method: "POST",
        }).then((response) => parseResponse(response, "Unable to update notification"))
      )
    );
    setUserNotifications((currentNotifications) =>
      currentNotifications.map((notification) =>
        notification.category === category ? { ...notification, is_read: true } : notification
      )
    );
  };

  const removeUserNotification = async (notificationId) => {
    if (!currentUser) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/users/${currentUser.id}/notifications/${notificationId}`, {
        method: "DELETE",
      });
      await parseResponse(response, "Unable to remove notification");
      setUserNotifications((currentNotifications) =>
        currentNotifications.filter((notification) => notification.id !== notificationId)
      );
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to remove notification", "error");
    }
  };

  const loadSellerOrders = async (sellerId) => {
    try {
      const response = await fetch(`${API_URL}/users/${sellerId}/sales`);
      const data = await parseResponse(response, "Unable to load seller orders");
      setSellerOrders(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load seller orders", "error");
    }
  };

  const handleViewSellerListings = async (sellerRef) => {
    if (!sellerRef) {
      return;
    }

    const sellerId = sellerRef.seller_id ?? sellerRef.id;
    const sellerUsername = sellerRef.seller_username ?? sellerRef.username;
    setSelectedSeller({
      id: sellerId,
      username: sellerUsername,
    });
    setSelectedSellerReviews(null);
    setSelectedListing(null);
    setIsLoadingSellerReviews(true);

    try {
      const response = await fetch(`${API_URL}/users/${sellerId}/reviews`);
      const data = await parseResponse(response, "Unable to load seller reviews");
      setSelectedSellerReviews(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load seller reviews", "error");
    } finally {
      setIsLoadingSellerReviews(false);
    }
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
      await loadSellerListings(currentUser.id);
      setOpenListingMenuId(null);
      showToast(data.message || "Listing removed successfully.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to remove listing", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const myListings = currentUser ? sellerListings : [];
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
  const selectedSellerListings = selectedSeller
    ? listings.filter((listing) => listing.seller_id === selectedSeller.id)
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
  const cartTotal = cartItems.reduce((total, item) => total + Number(item.price) * Number(item.quantity || 1), 0);
  const cartQuantityCount = cartItems.reduce((total, item) => total + Number(item.quantity || 1), 0);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    hideActivePages();
    setShowShopPage(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
    setSortOption("newest");
    setShowShopPage(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
    setShowShopPage(false);
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
    setShowShopPage(false);
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
    setShowShopPage(false);
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

    if (listing.status === "reserved" && listing.reserved_buyer_id !== currentUser.id) {
      setSelectedListing(null);
      showToast("This item is reserved for another buyer.", "error");
      return;
    }

    const alreadyInCart = cartItems.some((item) => item.id === listing.id);

    if (alreadyInCart) {
      setSelectedListing(null);
      showToast("Item is already in your cart.", "error");
      return;
    }

    setCartItems((currentItems) => [...currentItems, { ...listing, quantity: 1 }]);
    setReceipt(null);
    setSelectedListing(null);
    showToast("Item successfully added to cart.");
  };

  const updateCartQuantity = (listingId, nextQuantity) => {
    setCartItems((currentItems) =>
      currentItems.map((item) => {
        if (item.id !== listingId) {
          return item;
        }

        const stock = Math.max(1, Number(item.stock) || 1);
        const quantity = Math.min(stock, Math.max(1, Number(nextQuantity) || 1));
        return { ...item, quantity };
      })
    );
    setReceipt(null);
  };

  const deliveryMethodLabels = {
    self_pickup: "Self Pickup",
    delivery: "Delivery",
  };

  const paymentMethodLabels = {
    mpaisa: "M-PAiSA",
    mycash: "MyCash",
    visa: "VISA",
    cash: "Cash",
  };

  const checkoutCart = async (paymentMethod, checkoutSummary = {}, paymentDetails = {}, forceFailure = false) => {
    if (!currentUser) {
      showToast("Please login to purchase items.", "error");
      openAuth("login");
      return;
    }

    if (!paymentMethodLabels[paymentMethod]) {
      showToast("Please select a payment method.", "error");
      return;
    }

    const deliveryMethod = checkoutSummary.delivery_method || "self_pickup";
    if (!deliveryMethodLabels[deliveryMethod]) {
      showToast("Please select a delivery method.", "error");
      return;
    }

    const availableItems = cartItems.filter(
      (item) =>
        item.status !== "sold" &&
        Number(item.stock) > 0 &&
        (item.status !== "reserved" || item.reserved_buyer_id === currentUser.id)
    );
    if (!availableItems.length) {
      showToast("No available items to checkout.", "error");
      return;
    }

    setIsSubmitting(true);

    try {
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
      const response = await fetch(`${API_URL}/checkout?buyer_id=${currentUser.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payment_method: paymentMethod,
          delivery_method: deliveryMethod,
          payment_details: paymentDetails,
          simulate_failure: forceFailure,
          items: availableItems.map((item) => ({ item_id: item.id, quantity: Number(item.quantity || 1) })),
        }),
      });
      const checkout = await parseResponse(response, "Unable to process checkout");
      const orders = checkout.orders || [];
      const purchasedIds = orders.map((order) => order.item_id);
      setCartItems((currentItems) => currentItems.filter((item) => !purchasedIds.includes(item.id)));
      await loadListings();
      const updatedPurchaseHistory = await loadPurchaseHistory(currentUser.id);
      const reviewItems = updatedPurchaseHistory
        .filter(
          (purchase) =>
            checkout.payment.status !== "pending" &&
            purchasedIds.includes(purchase.item_id) &&
            !purchase.has_review
        )
        .map((purchase) => {
          const listing = availableItems.find((item) => item.id === purchase.item_id);
          return {
            ...purchase,
            name: purchase.item_name,
            photo: listing?.photo || "",
            seller_username: purchase.seller_username,
          };
        });
      setReceipt({
        id: orders.map((order) => `ORDER-${order.id}`).join(", "),
        items: orders.map((order) => ({
          ...order,
          name: order.item_name,
        })),
        total: checkout.total,
        paymentMethod: paymentMethodLabels[paymentMethod],
        paymentStatus: checkout.payment.status,
        paymentReference: checkout.payment.reference,
        paymentMessage: checkout.payment.message,
        purchasedAt: orders[0]?.purchased_at
          ? new Date(orders[0].purchased_at).toLocaleString()
          : new Date().toLocaleString(),
      });
      setShowAdminDashboard(false);
      setShowSellerPanel(false);
      setShowShopPage(false);
      setShowCartPanel(true);
      setShowPurchasesPage(false);
      setActiveCategoryPage(null);
      setActiveLegalPage(null);
      setActiveAccountPage(null);
      setPendingReviewItems(reviewItems);
      setCheckoutReviewForm({ rating: "5", review: "" });
      await loadSellerOrders(currentUser.id);
      await loadUserNotifications(currentUser.id);
      showToast(
        checkout.payment.status === "pending"
          ? "Cash order placed. Payment is due to the seller at handoff."
          : "Payment successful."
      );
    } catch (error) {
      await loadListings();
      if (error?.status === 402) {
        throw new Error("Payment failed. No money was taken and your items were not changed. Check your details or try another payment method.");
      }
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitListingReport = async (listing, reason, targetType = "listing") => {
    if (!currentUser) {
      showToast("Please login to report listings.", "error");
      openAuth("login");
      return;
    }

    if (reason.trim().length < 8) {
      showToast("Please enter a report reason with at least 8 characters.", "error");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reporter_id: currentUser.id,
          target_type: targetType,
          target_id: targetType === "user" ? listing.seller_id : listing.id,
          target_label: targetType === "user" ? listing.seller_username : listing.name,
          reason,
        }),
      });
      const data = await parseResponse(response, "Unable to submit report");
      showToast(data.message || "Report submitted to admin.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to submit report", "error");
    }
  };

  const submitRatingReview = async (purchase, rating, review) => {
    if (!currentUser) {
      showToast("Please login to submit a review.", "error");
      openAuth("login");
      return false;
    }

    if (review.trim().length < 5) {
      showToast("Please enter a review with at least 5 characters.", "error");
      return false;
    }

    try {
      const response = await fetch(`${API_URL}/ratings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer_id: currentUser.id,
          purchase_id: purchase.id,
          item_id: purchase.item_id || purchase.id,
          rating,
          review,
        }),
      });
      const data = await parseResponse(response, "Unable to submit review");
      showToast(data.message || "Rating and review submitted.");
      await loadPurchaseHistory(currentUser.id);
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to submit review", "error");
      return false;
    }
  };

  const cancelOrder = async (order) => {
    if (!currentUser) {
      openAuth("login");
      return;
    }

    if (!window.confirm(`Cancel order for ${order.item_name}?`)) {
      return;
    }

    setIsSubmitting(true);
    try {
      await fetch(`${API_URL}/orders/${order.id}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.id }),
      }).then((response) => parseResponse(response, "Unable to cancel order"));
      await loadPurchaseHistory(currentUser.id);
      await loadSellerOrders(currentUser.id);
      await loadListings();
      await loadSellerListings(currentUser.id);
      await loadUserNotifications(currentUser.id);
      showToast("Order cancelled.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to cancel order", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateSellerOrderStage = async (order, stage) => {
    if (!currentUser) {
      openAuth("login");
      return;
    }

    setIsSubmitting(true);
    try {
      await fetch(`${API_URL}/orders/${order.id}/seller-stage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seller_id: currentUser.id, stage }),
      }).then((response) => parseResponse(response, "Unable to update order progress"));
      await loadSellerOrders(currentUser.id);
      showToast("Order progress updated.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to update order progress", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openProductConversation = async (listing) => {
    if (!currentUser) {
      setSelectedListing(null);
      showToast("Please login to message the seller.", "error");
      openAuth("login");
      return;
    }

    if (listing.seller_id === currentUser.id) {
      showToast("You cannot message yourself about your own listing.", "error");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/items/${listing.id}/conversation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ buyer_id: currentUser.id }),
      });
      const conversation = await parseResponse(response, "Unable to open conversation");
      setSelectedListing(null);
      setConversations((currentConversations) => {
        const remaining = currentConversations.filter((item) => item.id !== conversation.id);
        return [conversation, ...remaining];
      });
      setActiveConversationId(conversation.id);
      await loadUnreadMessageCount(currentUser.id);
      openAccountPage("messages");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to open conversation", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openConversation = async (conversationId) => {
    if (!currentUser) {
      openAuth("login");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/conversations/${conversationId}?user_id=${currentUser.id}`);
      const conversation = await parseResponse(response, "Unable to open conversation");
      setConversations((currentConversations) =>
        currentConversations.map((item) => (item.id === conversation.id ? conversation : item))
      );
      setActiveConversationId(conversation.id);
      await loadUnreadMessageCount(currentUser.id);
      await markUserNotificationsViewedByCategory("message");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to open conversation", "error");
    }
  };

  const sendConversationMessage = async () => {
    if (!currentUser || !activeConversationId || !messageDraft.trim()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/conversations/${activeConversationId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender_id: currentUser.id, body: messageDraft }),
      });
      const conversation = await parseResponse(response, "Unable to send message");
      setConversations((currentConversations) =>
        currentConversations.map((item) => (item.id === conversation.id ? conversation : item))
      );
      setActiveConversationId(conversation.id);
      setMessageDraft("");
      await loadUnreadMessageCount(currentUser.id);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to send message", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const loadReservationBuyers = async (listing) => {
    if (!currentUser) {
      openAuth("login");
      return [];
    }

    try {
      const response = await fetch(`${API_URL}/items/${listing.id}/message-buyers?seller_id=${currentUser.id}`);
      return await parseResponse(response, "Unable to load interested buyers");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to load interested buyers", "error");
      return [];
    }
  };

  const reserveListingForBuyer = async (listing, buyerId) => {
    if (!currentUser) {
      openAuth("login");
      return false;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/items/${listing.id}/reserve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seller_id: currentUser.id, buyer_id: buyerId }),
      });
      const data = await parseResponse(response, "Unable to reserve listing");
      await loadListings();
      await loadSellerListings(currentUser.id);
      await loadConversations(currentUser.id);
      await loadUnreadMessageCount(currentUser.id);
      setOpenListingMenuId(null);
      showToast(data.message || "Listing reserved.");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to reserve listing", "error");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateListingSellerStatus = async (listing, status) => {
    if (!currentUser) {
      openAuth("login");
      return;
    }

    const labels = {
      available: "mark this listing available again",
      sold: "mark this listing sold",
      hidden: "deactivate this listing",
    };
    if (!window.confirm(`Are you sure you want to ${labels[status] || "update this listing"}?`)) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/items/${listing.id}/seller-status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seller_id: currentUser.id, status }),
      });
      const data = await parseResponse(response, "Unable to update listing status");
      await loadListings();
      await loadSellerListings(currentUser.id);
      setOpenListingMenuId(null);
      showToast(data.message || "Listing updated.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to update listing status", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitCheckoutReview = async () => {
    const currentItem = pendingReviewItems[0];
    if (!currentItem) {
      return;
    }

    const saved = await submitRatingReview(currentItem, Number(checkoutReviewForm.rating), checkoutReviewForm.review);
    if (!saved) {
      return;
    }

    setPendingReviewItems((currentItems) => currentItems.slice(1));
    setCheckoutReviewForm({ rating: "5", review: "" });
  };

  const skipCheckoutReview = () => {
    setPendingReviewItems((currentItems) => currentItems.slice(1));
    setCheckoutReviewForm({ rating: "5", review: "" });
  };

  const removeFromCart = (listingId) => {
    setCartItems((currentItems) => currentItems.filter((item) => item.id !== listingId));
    setReceipt(null);
    showToast("Item removed from cart.");
  };

  const handleSuggestionSelect = (listing) => {
    setSearchQuery(listing.name);
    hideActivePages();
    setShowShopPage(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedCategory("All");
    setSortOption("newest");
  };

  const openLegalPage = (page) => {
    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowShopPage(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(page);
    setActiveAccountPage(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openAccountPage = (page, salesView = "active") => {
    if (!currentUser) {
      openAuth("login");
      return;
    }

    if (page === "sales") {
      setActiveSalesView(salesView);
      loadSellerOrders(currentUser.id);
      loadSellerListings(currentUser.id);
    }

    setShowAdminDashboard(false);
    setShowSellerPanel(false);
    setShowShopPage(false);
    setShowCartPanel(false);
    setShowPurchasesPage(false);
    setActiveCategoryPage(null);
    setActiveLegalPage(null);
    setActiveAccountPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const confirmPaymentReceived = async (order) => {
    if (!currentUser) {
      openAuth("login");
      return;
    }
    if (!window.confirm(`Confirm that you received $${Number(order.total_amount).toFixed(2)} cash from ${order.buyer_username}?`)) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/orders/${order.id}/payment-confirmation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seller_id: currentUser.id }),
      });
      const data = await parseResponse(response, "Unable to confirm cash payment");
      await loadSellerOrders(currentUser.id);
      await loadPurchaseHistory(currentUser.id);
      await loadListings();
      await loadSellerListings(currentUser.id);
      await loadUserNotifications(currentUser.id);
      showToast(`Payment receipt recorded. Confirmation reference: ${data.payment_reference}`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Unable to confirm cash payment", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeNavPage = showCartPanel
    ? "cart"
    : showPurchasesPage || (showSellerPanel && activeSellerTab === "my-listings") || activeAccountPage === "sales"
      ? "activity"
      : showSellerPanel && activeSellerTab === "add-listing"
        ? "sell"
        : activeAccountPage === "messages"
          ? "messages"
          : activeAccountPage
            ? "account"
            : activeCategoryPage
              ? "shop"
              : showShopPage
                ? "shop"
                : "home";

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
            resendSecondsRemaining={resendSecondsRemaining}
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
        cartCount={cartQuantityCount}
        unreadMessageCount={unreadMessageCount}
        notifications={userNotifications}
        activePage={activeNavPage}
        onHome={hideActivePages}
        onBrowse={handleBrowse}
        onOpenSellerTab={openSellerTab}
        onOpenPurchases={openPurchasesPage}
        onOpenCart={openCart}
        onOpenAccountPage={openAccountPage}
        onOpenAuth={openAuth}
        onLogout={handleLogout}
        onNotificationView={openUserNotification}
        onNotificationRemove={removeUserNotification}
      />

      <Toast message={toastMessage} type={toastType} />

      <AuthModal
        authMode={authMode}
        authForm={authForm}
        emailError={emailError}
        formMessage={formMessage}
        isSubmitting={isSubmitting}
        verificationEmail={verificationEmail}
        resendSecondsRemaining={resendSecondsRemaining}
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
        onViewSeller={handleViewSellerListings}
      />

      {showCartPanel && (
        <CartPage
          cartItems={cartItems}
          cartTotal={cartTotal}
          currentUser={currentUser}
          receipt={receipt}
          onClose={() => setShowCartPanel(false)}
          onCheckout={checkoutCart}
          onClearReceipt={() => setReceipt(null)}
          onRemove={removeFromCart}
          onQuantityChange={updateCartQuantity}
          onViewSeller={handleViewSellerListings}
          isSubmitting={isSubmitting}
        />
      )}

      {showPurchasesPage && (
        <PastPurchasesPage
          currentUser={currentUser}
          purchases={purchaseHistory}
          onBack={hideActivePages}
          onLogin={() => openAuth("login")}
          onSubmitReview={submitRatingReview}
          onViewSeller={handleViewSellerListings}
          onCancelOrder={cancelOrder}
          isSubmitting={isSubmitting}
        />
      )}

      <AccountPage
        page={activeAccountPage}
        currentUser={currentUser}
        myListings={myListings}
        purchaseHistory={purchaseHistory}
        sellerOrders={sellerOrders}
        activeSalesView={activeSalesView}
        conversations={conversations}
        activeConversationId={activeConversationId}
        messageDraft={messageDraft}
        onConversationSelect={openConversation}
        onViewConversationListing={(listing) => listing && setSelectedListing(listing)}
        onMessageDraftChange={setMessageDraft}
        onSendMessage={sendConversationMessage}
        onBack={hideActivePages}
      />

      <LegalPage page={activeLegalPage} onBack={hideActivePages} />

      {showShopPage && !activeCategoryPage && !showCartPanel && !showPurchasesPage && !activeLegalPage && !activeAccountPage && !showSellerPanel && (
        <ListingsSection
          categories={categories}
          filteredListings={filteredListings}
          isLoadingListings={isLoadingListings}
          searchQuery={searchQuery}
          selectedCategory={selectedCategory}
          sortOption={sortOption}
          title="All Products"
          description="Browse every available listing in the marketplace."
          onClearFilters={clearFilters}
          onSelectCategory={setSelectedCategory}
          onSelectListing={setSelectedListing}
          onViewSeller={handleViewSellerListings}
          onSortChange={setSortOption}
        />
      )}

      {showSellerPanel && !showShopPage && !activeCategoryPage && !showCartPanel && !showPurchasesPage && !activeLegalPage && !activeAccountPage && (
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
          sellerOrders={sellerOrders}
          onLoadReservationBuyers={loadReservationBuyers}
          onReserveListing={reserveListingForBuyer}
          onUpdateListingStatus={updateListingSellerStatus}
          onClose={hideActivePages}
          onDeleteListing={handleDeleteListing}
          onEditListing={handleEditListing}
          onFieldChange={handleListingFieldChange}
          onLogin={() => openAuth("login")}
          onMenuToggle={(listingId) =>
            setOpenListingMenuId((currentId) => (currentId === listingId ? null : listingId))
          }
          onViewListing={handleViewOwnListing}
          onPhotoChange={handlePhotoChange}
          onPhotoConfirm={confirmPhoto}
          onPhotoRemove={removePhoto}
          onResetForm={resetListingForm}
          onSubmit={handleListingSubmit}
          onUpdateOrderStage={updateSellerOrderStage}
          onConfirmPaymentReceived={confirmPaymentReceived}
          onCancelOrder={cancelOrder}
        />
      )}

      {!showShopPage && !showSellerPanel && !activeCategoryPage && !showCartPanel && !showPurchasesPage && !activeLegalPage && !activeAccountPage && (
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
            onViewSeller={handleViewSellerListings}
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
        onMessageSeller={openProductConversation}
        onReportListing={submitListingReport}
        onViewSeller={handleViewSellerListings}
      />

      {selectedSeller && (
        <div className="auth-modal-backdrop" onClick={() => setSelectedSeller(null)}>
          <div className="seller-products-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className="section-kicker">Seller profile</span>
                <h3>{selectedSeller.username}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setSelectedSeller(null)} aria-label="Close">
                x
              </button>
            </div>
            <div className="seller-profile-summary">
              <div>
                <span>Rating</span>
                <strong>
                  {isLoadingSellerReviews
                    ? "Loading..."
                    : selectedSellerReviews?.review_count
                      ? `${selectedSellerReviews.average_rating} / 5`
                      : "No ratings yet"}
                </strong>
              </div>
              <div>
                <span>Reviews</span>
                <strong>{selectedSellerReviews?.review_count ?? 0}</strong>
              </div>
              <div>
                <span>Listed Items</span>
                <strong>{selectedSellerListings.length}</strong>
              </div>
            </div>
            {selectedSellerListings.length ? (
              <div className="seller-profile-section">
                <h4>Listed Items</h4>
                <div className="seller-products-grid">
                  {selectedSellerListings.map((listing) => (
                    <ProductCard
                      listing={listing}
                      showPrice
                      onSelect={(selectedProduct) => {
                        setSelectedSeller(null);
                        setSelectedListing(selectedProduct);
                      }}
                      key={listing.id}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <p className="empty-state">This seller has no other available listings.</p>
            )}
            <div className="seller-profile-section">
              <h4>Reviews</h4>
              {isLoadingSellerReviews ? (
                <p className="empty-state">Loading reviews...</p>
              ) : selectedSellerReviews?.reviews?.length ? (
                <div className="seller-review-list">
                  {selectedSellerReviews.reviews.map((review) => (
                    <div className="seller-review-item" key={review.id}>
                      <div>
                        <strong>{review.reviewer_username}</strong>
                        <span>{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</span>
                      </div>
                      <p>{review.review}</p>
                      <small>{review.item_name}</small>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">No reviews for this seller yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {pendingReviewItems.length > 0 && (
        <div className="auth-modal-backdrop" onClick={() => setPendingReviewItems([])}>
          <div className="checkout-review-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className="section-kicker">Purchase complete</span>
                <h2>Review your item</h2>
              </div>
              <button type="button" className="close-button" onClick={() => setPendingReviewItems([])} aria-label="Close">
                x
              </button>
            </div>
            <div className="review-item-summary">
              {pendingReviewItems[0].photo ? (
                <img src={pendingReviewItems[0].photo} alt={pendingReviewItems[0].name || pendingReviewItems[0].item_name} />
              ) : (
                <span>{pendingReviewItems[0].category?.charAt(0) || "I"}</span>
              )}
              <div>
                <strong>{pendingReviewItems[0].name || pendingReviewItems[0].item_name}</strong>
                <small>Seller: {pendingReviewItems[0].seller_username}</small>
              </div>
            </div>
            <div className="feedback-block checkout-review-form">
              <strong>Rating</strong>
              <div className="rating-control" role="group" aria-label="Rating">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    type="button"
                    className={Number(checkoutReviewForm.rating) >= value ? "active" : ""}
                    key={value}
                    onClick={() => setCheckoutReviewForm((form) => ({ ...form, rating: String(value) }))}
                    aria-label={`${value} star`}
                  >
                    &#9733;
                  </button>
                ))}
              </div>
              <textarea
                value={checkoutReviewForm.review}
                onChange={(event) => setCheckoutReviewForm((form) => ({ ...form, review: event.target.value }))}
                placeholder="Share your experience after checkout"
                rows="4"
              />
              <div className="checkout-review-actions">
                <button type="button" className="secondary-button" onClick={skipCheckoutReview}>
                  Skip
                </button>
                <button type="button" className="auth-submit" onClick={submitCheckoutReview}>
                  Submit
                </button>
              </div>
            </div>
            {pendingReviewItems.length > 1 && (
              <p className="review-progress">{pendingReviewItems.length - 1} more item review pending.</p>
            )}
          </div>
        </div>
      )}

      <Footer logo={logo} onLegalNavigate={openLegalPage} />
        </>
      )}
    </div>
  );
}

export default Home;
