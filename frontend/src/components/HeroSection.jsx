import React from "react";
import SearchInput from "./SearchInput";

function HeroSection({ searchQuery, suggestions, onSearchChange, onSearchSubmit, onSuggestionSelect }) {
  return (
    <section className="hero" id="home">
      <h1>Buy and Sell With USP Students</h1>
      <p>A simple marketplace for USP students to buy and sell items within the university community.</p>

      <form className="search-bar" onSubmit={onSearchSubmit}>
        <SearchInput id="marketplace-search" value={searchQuery} onChange={onSearchChange} label="Search listings" placeholder="Item, category, seller or listing ID" />
        <button type="submit">Search</button>
      </form>

      {suggestions.length > 0 && (
        <div className="search-suggestions">
          {suggestions.map((listing) => (
            <button type="button" key={listing.id} onClick={() => onSuggestionSelect(listing)}>
              <span>{listing.name}</span>
              <small>{listing.category}</small>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export default HeroSection;
