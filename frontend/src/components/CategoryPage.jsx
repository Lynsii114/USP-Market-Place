import React from "react";
import ProductCard from "./ProductCard";
import PriceRangeFields from "./PriceRangeFields";

function CategoryPage({ categoryName, listings, onBack, onSelectListing, onViewSeller, minimumPrice, maximumPrice, priceError, onMinimumPriceChange, onMaximumPriceChange }) {
  if (!categoryName) {
    return null;
  }

  return (
    <section className="category-page">
      <div className="category-page-header">
        <button type="button" className="secondary-button" onClick={onBack}>
          Back to Categories
        </button>
        <div>
          <h1>{categoryName}</h1>
          <p>
            {listings.length
              ? `All products currently listed under ${categoryName}.`
              : categoryName === "Other"
              ? "More services coming soon."
              : `All products currently listed under ${categoryName}.`}
          </p>
        </div>
      </div>

      <div className="listing-filters">
        <PriceRangeFields {...{ minimumPrice, maximumPrice, priceError, onMinimumPriceChange, onMaximumPriceChange }} />
        {(minimumPrice || maximumPrice) && <button type="button" className="secondary-button" onClick={() => { onMinimumPriceChange(""); onMaximumPriceChange(""); }}>Clear Prices</button>}
      </div>

      {priceError ? null : categoryName === "Other" && !listings.length ? (
        <p className="empty-state">More services coming soon.</p>
      ) : listings.length ? (
        <div className="product-container">
          {listings.map((listing) => (
            <ProductCard listing={listing} showPrice onSelect={onSelectListing} onViewSeller={onViewSeller} key={listing.id} />
          ))}
        </div>
      ) : (
        <p className="empty-state">No items match these filters in {categoryName}.</p>
      )}
    </section>
  );
}

export default CategoryPage;
