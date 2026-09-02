import React from "react";

function ProductCard({ listing, showPrice = false, onSelect }) {
  const isSold = listing.status === "sold" || Number(listing.stock) <= 0;

  return (
    <button type="button" className="product-card" onClick={() => onSelect(listing)}>
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
  );
}

export default ProductCard;
