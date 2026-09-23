import React from "react";
import ProductCard from "./ProductCard";

function ListingsSection({
  categories,
  filteredListings,
  isLoadingListings,
  searchQuery,
  selectedCategory,
  sortOption,
  onClearFilters,
  onSelectCategory,
  onSelectListing,
  onViewSeller,
  onSortChange,
}) {
  return (
    <section className="listings" id="listings">
      <div className="section-heading">
        <h2>Recent Listings</h2>
        {selectedCategory !== "All" && <p>{`Showing products listed under ${selectedCategory}.`}</p>}
      </div>

      <div className="listing-filters">
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

        {(searchQuery || selectedCategory !== "All" || sortOption !== "newest") && (
          <button type="button" className="secondary-button" onClick={onClearFilters}>
            Clear Filters
          </button>
        )}
      </div>

      {isLoadingListings ? (
        <p className="empty-state">Loading listings...</p>
      ) : filteredListings.length ? (
        <div className="product-container">
          {filteredListings.map((listing) => (
            <ProductCard listing={listing} showPrice onSelect={onSelectListing} onViewSeller={onViewSeller} key={listing.id} />
          ))}
        </div>
      ) : (
        <p className="empty-state">No listings match your search or selected category.</p>
      )}
    </section>
  );
}

export default ListingsSection;
