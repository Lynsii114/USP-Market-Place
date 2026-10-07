import React, { useEffect, useState } from "react";

function ProductModal({ listing, currentUser, onClose, onAddToCart, onMessageSeller, onReportListing, onViewSeller }) {
  const [reportReason, setReportReason] = useState("");
  const [reportTarget, setReportTarget] = useState("listing");
  const [reportMode, setReportMode] = useState(null);
  const [reservedPaymentDetails, setReservedPaymentDetails] = useState(null);
  const [isLoadingPaymentDetails, setIsLoadingPaymentDetails] = useState(false);
  const [paymentDetailsError, setPaymentDetailsError] = useState("");

  useEffect(() => {
    let isCurrent = true;
    setReservedPaymentDetails(null);
    setPaymentDetailsError("");

    if (!listing || !currentUser?.id) {
      setIsLoadingPaymentDetails(false);
      return () => {
        isCurrent = false;
      };
    }

    setIsLoadingPaymentDetails(true);
    fetch(`http://localhost:8000/api/items/${listing.id}?user_id=${currentUser.id}`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Unable to refresh listing details");
        }
        return data;
      })
      .then((item) => {
        if (isCurrent) {
          setReservedPaymentDetails(item);
        }
      })
      .catch((error) => {
        if (isCurrent) {
          setReservedPaymentDetails(null);
          setPaymentDetailsError(error instanceof Error ? error.message : "Unable to load seller payment details");
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoadingPaymentDetails(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [listing?.id, listing?.status, listing?.reserved_buyer_id, currentUser?.id]);

  if (!listing) {
    return null;
  }

  const isSold = listing.status === "sold" || Number(listing.stock) <= 0;
  const isReserved = listing.status === "reserved";
  const isReservedForCurrentUser = isReserved && listing.reserved_buyer_id === currentUser?.id;
  const isOwnListing = currentUser?.id === listing.seller_id;
  const showReservedPaymentDetails =
    reservedPaymentDetails?.status === "reserved" &&
    reservedPaymentDetails.reserved_buyer_id === currentUser?.id &&
    Boolean(reservedPaymentDetails.payment_number);

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="product-modal" onClick={(event) => event.stopPropagation()}>
        <div className="auth-header">
          <h2>{listing.name}</h2>
          <div className="product-header-actions">
            {currentUser && !isOwnListing && (
              <div className="admin-action-dropdown">
                <button
                  type="button"
                  className="icon-nav-button product-more-button"
                  aria-label="Listing actions"
                  aria-expanded={reportMode === "menu"}
                  onClick={() => setReportMode((mode) => (mode === "menu" ? null : "menu"))}
                >
                  ...
                </button>
                {reportMode === "menu" && (
                  <div className="admin-action-menu">
                    <button type="button" onClick={() => setReportMode("report")}>
                      Report
                    </button>
                  </div>
                )}
              </div>
            )}
            <button type="button" className="close-button" onClick={onClose} aria-label="Close">
              x
            </button>
          </div>
        </div>

        <div className="product-modal-image">
          {listing.photo ? <img src={listing.photo} alt={listing.name} /> : <span>{listing.category}</span>}
          {isSold && <span className="sold-badge">Sold</span>}
          {!isSold && isReserved && <span className="sold-badge reserved">Reserved</span>}
        </div>

        <div className="product-modal-details">
          <p className="product-price">${Number(listing.price).toFixed(2)}</p>
          <p className="product-meta">{listing.category}</p>
          <p className={isSold ? "stock-badge sold" : isReserved ? "stock-badge reserved" : "stock-badge"}>
            {isSold ? "Sold" : isReserved ? "Reserved" : `${listing.stock} in stock`}
          </p>
          <p>{listing.description}</p>
          <div className="seller-details">
            <strong>Seller</strong>
            {onViewSeller ? (
              <button type="button" className="seller-link-button" onClick={() => onViewSeller(listing)}>
                {listing.seller_username}
              </button>
            ) : (
              <span>{listing.seller_username}</span>
            )}
          </div>
          <div className="seller-details">
            <strong>Contact</strong>
            <span>{listing.contact}</span>
          </div>
          {showReservedPaymentDetails && (
            <div className="seller-details">
              <strong>
                {reservedPaymentDetails.payment_method === "mpaisa" ? "M-PAiSA" : "MyCash"} Payment Number
              </strong>
              <span>{reservedPaymentDetails.payment_number}</span>
            </div>
          )}
          {!isOwnListing &&
            ["mpaisa", "mycash"].includes(listing.payment_method) &&
            isReservedForCurrentUser &&
            !showReservedPaymentDetails &&
            isLoadingPaymentDetails && <p>Loading the seller's reserved payment details...</p>}
          {!isOwnListing &&
            ["mpaisa", "mycash"].includes(listing.payment_method) &&
            isReservedForCurrentUser &&
            !showReservedPaymentDetails &&
            paymentDetailsError && <p role="alert">{paymentDetailsError}</p>}
          {!isOwnListing &&
            ["mpaisa", "mycash"].includes(listing.payment_method) &&
            !isReservedForCurrentUser && (
              <p className="product-meta">The seller's receiving number is shown after they reserve this item for you.</p>
            )}
          {currentUser && !isOwnListing && (
            <button type="button" className="secondary-button" onClick={() => onMessageSeller(listing)} disabled={isSold}>
              Message Seller
            </button>
          )}
          <button
            type="button"
            className="auth-submit"
            onClick={() => onAddToCart(listing)}
            disabled={isSold || isOwnListing || (isReserved && !isReservedForCurrentUser)}
          >
            {isSold
              ? "Sold Out"
              : isOwnListing
                ? "Your Listing"
                : isReserved && !isReservedForCurrentUser
                  ? "Reserved"
                  : "Add to Cart"}
          </button>
        </div>
      </div>

      {reportMode === "report" && currentUser && !isOwnListing && (
        <div className="nested-modal-backdrop" onClick={() => setReportMode(null)}>
          <div className="report-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className="section-kicker">Report</span>
                <h3>{listing.name}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setReportMode(null)} aria-label="Close">
                x
              </button>
            </div>
            <div className="feedback-block">
              <select value={reportTarget} onChange={(event) => setReportTarget(event.target.value)}>
                <option value="listing">Rule-breaking or suspicious item</option>
                <option value="user">Seller concern</option>
              </select>
              <textarea
                value={reportReason}
                onChange={(event) => setReportReason(event.target.value)}
                placeholder="Tell admin what looks wrong"
                rows="4"
              />
              <div className="feedback-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setReportMode(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="danger-outline-button"
                  onClick={() => {
                    onReportListing(listing, reportReason, reportTarget);
                    setReportReason("");
                    setReportMode(null);
                  }}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProductModal;
