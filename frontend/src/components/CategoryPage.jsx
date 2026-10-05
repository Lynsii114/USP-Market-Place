import React from "react";
import ProductCard from "./ProductCard";

function CategoryPage({ categoryName, listings, onBack, onSelectListing, onViewSeller }) {
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

      {categoryName === "Other" && !listings.length ? (
        <p className="empty-state">More services coming soon.</p>
      ) : listings.length ? (
        <div className="product-container">
          {listings.map((listing) => (
            <ProductCard listing={listing} showPrice onSelect={onSelectListing} onViewSeller={onViewSeller} key={listing.id} />
          ))}
        </div>
      ) : (
        <p className="empty-state">No items listed in {categoryName} yet.</p>
      )}
    </section>
  );
}

export default CategoryPage;
