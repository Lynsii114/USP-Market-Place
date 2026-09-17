import React from "react";

function ProductModal({ listing, currentUser, onClose, onAddToCart, onMessageSeller }) {
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
          <button type="button" className="close-button" onClick={onClose} aria-label="Close">
            x
          </button>
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
            <span>{listing.seller_username}</span>
          </div>
          <div className="seller-details">
            <strong>Contact</strong>
            <span>{listing.contact}</span>
          </div>
          <div className="product-modal-actions">
            <button type="button" className="auth-submit" onClick={() => onAddToCart(listing)} disabled={isSold || isOwnListing}>
              {isSold ? "Sold Out" : isOwnListing ? "Your Listing" : "Add to Cart"}
            </button>
            <button type="button" className="secondary-button" onClick={() => onMessageSeller(listing)} disabled={isOwnListing}>
              Message Seller
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProductModal;
