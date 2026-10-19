import React from "react";
import SearchInput from "./SearchInput";

function HeroSection({ searchQuery, suggestions, suggestionCount, onSearchChange, onSearchSubmit, onSuggestionSelect, onViewAllResults }) {
  return (
    <section className="hero" id="home">
      <h1>Buy and Sell With USP Students</h1>
      <p>A simple marketplace for USP students to buy and sell items within the university community.</p>

      <form className="search-bar" onSubmit={onSearchSubmit}>
        <SearchInput id="marketplace-search" value={searchQuery} onChange={onSearchChange} label="Search listings" placeholder="Search listings" />
        <button type="submit">Search</button>
      </form>

      {suggestions.length > 0 && (
        <div className="search-suggestions" aria-label="Search suggestions">
          <p className="search-suggestions-heading">Suggested listings</p>
          <div className="search-suggestion-list">
            {suggestions.map((listing) => (
              <button type="button" className="search-suggestion-item" key={listing.id} onClick={() => onSuggestionSelect(listing)}>
                <span className="search-suggestion-name">{listing.name}</span>
                <small>{listing.category}</small>
              </button>
            ))}
          </div>
          <button type="button" className="search-view-all" onClick={onViewAllResults}
            aria-label={`View all ${suggestionCount} ${suggestionCount === 1 ? "result" : "results"} in Shop`}>
            <span>View all {suggestionCount} {suggestionCount === 1 ? "result" : "results"}</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>
      )}
    </section>
  );
}

export default HeroSection;
