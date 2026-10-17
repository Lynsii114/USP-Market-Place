import React, { useEffect, useState } from "react";
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
  const [page, setPage] = useState(1);
  const pageSize = 12;
  const pageCount = Math.max(1, Math.ceil(filteredListings.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const start = (currentPage - 1) * pageSize;
  const visibleListings = preview ? filteredListings : filteredListings.slice(start, start + pageSize);
  const pageNumbers = [...new Set([1, currentPage - 1, currentPage, currentPage + 1, pageCount])]
    .filter((number) => number >= 1 && number <= pageCount).sort((a, b) => a - b);
  useEffect(() => { setPage(1); }, [searchQuery, selectedCategory, sortOption, minimumPrice, maximumPrice, preview]);
  useEffect(() => { setPage((number) => Math.min(number, pageCount)); }, [pageCount]);
  const changePage = (number) => {
    setPage(number);
    document.getElementById("shop-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
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

      {!preview && !priceError && !isLoadingListings && (
        <p className="inventory-result-count" id="shop-results" role="status">
          {filteredListings.length ? `Showing ${start + 1}–${start + visibleListings.length} of ${filteredListings.length} listings` : "Showing 0 listings"}
        </p>
      )}

      {!preview && priceError ? null : isLoadingListings ? (
        <p className="empty-state">Loading listings...</p>
      ) : filteredListings.length ? (
        <div className="product-container">
          {visibleListings.map((listing) => (
            <ProductCard listing={listing} showPrice onSelect={onSelectListing} onViewSeller={onViewSeller} key={listing.id} />
          ))}
        </div>
      ) : (
        <p className="empty-state">{preview ? "No listings available yet." : "No listings match your filters."}</p>
      )}
      {!preview && !priceError && !isLoadingListings && pageCount > 1 && (
        <nav className="inventory-pagination" aria-label="Shop pages">
          <button type="button" className="secondary-button" disabled={currentPage === 1} onClick={() => changePage(currentPage - 1)}>Previous</button>
          {pageNumbers.map((number, index) => (
            <React.Fragment key={number}>
              {index > 0 && number - pageNumbers[index - 1] > 1 && <span aria-hidden="true">…</span>}
              <button type="button" className="secondary-button" aria-label={`Page ${number}`} aria-current={number === currentPage ? "page" : undefined} onClick={() => changePage(number)}>{number}</button>
            </React.Fragment>
          ))}
          <button type="button" className="secondary-button" disabled={currentPage === pageCount} onClick={() => changePage(currentPage + 1)}>Next</button>
        </nav>
      )}
    </section>
  );
}

export default ListingsSection;
