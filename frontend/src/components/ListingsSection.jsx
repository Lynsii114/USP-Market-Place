import React from "react";
import ProductCard from "./ProductCard";
import PriceRangeFields from "./PriceRangeFields";

function ListingsSection({
  categories,
  filteredListings,
  isLoadingListings,
  searchQuery,
  onSearchChange,
  selectedCategory,
  sortOption,
  minimumPrice,
  maximumPrice,
  priceError,
  onMinimumPriceChange,
  onMaximumPriceChange,
  title = "Recent Listings",
  description = "",
  onClearFilters,
  onSelectCategory,
  onSelectListing,
  onViewSeller,
  onSortChange,
  preview = false,
  onViewAll,
}) {
  return (
    <section className="listings" id="listings">
      <div className="section-heading">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : !preview && selectedCategory !== "All" && <p>{`Showing products listed under ${selectedCategory}.`}</p>}
        {preview && <button type="button" className="secondary-button" onClick={onViewAll}>View all listings</button>}
      </div>

      {!preview && <div className="listing-filters">
        <label>Search Items
          <input type="search" value={searchQuery} placeholder="Item, category or seller" onChange={(event) => onSearchChange(event.target.value)} />
        </label>
        <label>
          Category
          <select value={selectedCategory} onChange={(event) => onSelectCategory(event.target.value)}>
            <option value="All">All Categories</option>
            {categories.map((category) => (
              <option value={category.name} key={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Sort By
          <select value={sortOption} onChange={(event) => onSortChange(event.target.value)}>
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="name-asc">Name A to Z</option>
            <option value="name-desc">Name Z to A</option>
            <option value="price-asc">Lowest Price</option>
            <option value="price-desc">Highest Price</option>
          </select>
        </label>

        <PriceRangeFields {...{ minimumPrice, maximumPrice, priceError, onMinimumPriceChange, onMaximumPriceChange }} />

        {(searchQuery || selectedCategory !== "All" || sortOption !== "newest" || minimumPrice || maximumPrice) && (
          <button type="button" className="secondary-button" onClick={onClearFilters}>
            Clear Filters
          </button>
        )}
      </div>}

      {!preview && priceError ? null : isLoadingListings ? (
        <p className="empty-state">Loading listings...</p>
      ) : filteredListings.length ? (
        <div className="product-container">
          {filteredListings.map((listing) => (
            <ProductCard listing={listing} showPrice onSelect={onSelectListing} onViewSeller={onViewSeller} key={listing.id} />
          ))}
        </div>
      ) : (
        <p className="empty-state">{preview ? "No listings available yet." : "No listings match your filters."}</p>
      )}
    </section>
  );
}

export default ListingsSection;
