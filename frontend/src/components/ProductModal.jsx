import React, { useState } from "react";

function ProductModal({ listing, currentUser, onClose, onAddToCart, onReportListing, onViewSeller }) {
  const [reportReason, setReportReason] = useState("");
  const [reportTarget, setReportTarget] = useState("listing");
  const [reportMode, setReportMode] = useState(null);

  if (!listing) {
    return null;
  }

  const isSold = listing.status === "sold" || Number(listing.stock) <= 0;
  const isOwnListing = currentUser?.id === listing.seller_id;

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
        </div>

        <div className="product-modal-details">
          <p className="product-price">${Number(listing.price).toFixed(2)}</p>
          <p className="product-meta">{listing.category}</p>
          <p className={isSold ? "stock-badge sold" : "stock-badge"}>
            {isSold ? "Sold" : `${listing.stock} in stock`}
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
          <button type="button" className="auth-submit" onClick={() => onAddToCart(listing)} disabled={isSold || isOwnListing}>
            {isSold ? "Sold Out" : isOwnListing ? "Your Listing" : "Add to Cart"}
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
