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
          <p>{categoryName === "Other" ? "Items that don't fit the other categories." : `Browse items in ${categoryName}.`}</p>
        </div>
      </div>

      <div className="listing-filters">
        <PriceRangeFields {...{ minimumPrice, maximumPrice, priceError, onMinimumPriceChange, onMaximumPriceChange }} />
        {(minimumPrice || maximumPrice) && <button type="button" className="secondary-button" onClick={() => { onMinimumPriceChange(""); onMaximumPriceChange(""); }}>Clear Prices</button>}
      </div>

      {priceError ? null : listings.length ? (
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
