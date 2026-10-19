import React, { useEffect, useState } from "react";
import SearchInput from "./SearchInput";
import { searchRecords } from "../utils/search.mjs";
import ProductCard from "./ProductCard";
import PriceRangeFields from "./PriceRangeFields";

function CategoryPage({ categoryName, listings, onBack, onSelectListing, onViewSeller, minimumPrice, maximumPrice, priceError, onMinimumPriceChange, onMaximumPriceChange }) {
  const [query, setQuery] = useState("");
  useEffect(() => setQuery(""), [categoryName]);
  const results = searchRecords(listings, query, (listing) => [listing.name, listing.id, listing.description, listing.seller_username]);
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
        <label>Search this category<SearchInput value={query} onChange={setQuery} label="Search this category" placeholder="Item, seller or listing ID" /></label>
        <PriceRangeFields {...{ minimumPrice, maximumPrice, priceError, onMinimumPriceChange, onMaximumPriceChange }} />
        {(minimumPrice || maximumPrice) && <button type="button" className="secondary-button" onClick={() => { onMinimumPriceChange(""); onMaximumPriceChange(""); }}>Clear Prices</button>}
      </div>

      {!priceError && <p className="search-result-count" role="status">{results.length} matching listings</p>}
      {priceError ? null : results.length ? (
        <div className="product-container">
          {results.map((listing) => (
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
