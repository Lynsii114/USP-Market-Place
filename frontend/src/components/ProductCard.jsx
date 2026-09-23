import React from "react";

function ProductCard({ listing, showPrice = false, onSelect, onViewSeller }) {
  const isSold = listing.status === "sold" || Number(listing.stock) <= 0;

  return (
    <article className="product-card">
      <button type="button" className="product-card-main" onClick={() => onSelect(listing)}>
        <div className="product-image">
          {listing.photo ? <img src={listing.photo} alt={listing.name} /> : <span>{listing.category}</span>}
          {isSold && <span className="sold-badge">Sold</span>}
        </div>
        <div className="product-details">
          <h3>{listing.name}</h3>
          {showPrice && <p className="product-card-price">${Number(listing.price).toFixed(2)}</p>}
          <p className={isSold ? "stock-badge sold" : "stock-badge"}>
            {isSold ? "Sold" : `${listing.stock} in stock`}
          </p>
        </div>
      </button>
      <div className="product-card-seller">
        <span>Seller</span>
        {onViewSeller ? (
          <button type="button" onClick={() => onViewSeller(listing)}>
            {listing.seller_username}
          </button>
        ) : (
          <strong>{listing.seller_username}</strong>
        )}
      </div>
    </article>
  );
}

export default ProductCard;
