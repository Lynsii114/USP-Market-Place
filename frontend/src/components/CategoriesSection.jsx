import React from "react";

function CategoriesSection({ categories, selectedCategory, onChooseCategory }) {
  return (
    <section className="categories" id="categories">
      <div className="section-heading">
        <h2>Categories</h2>
        <p>Find what you're looking for</p>
      </div>

      <div className="category-container">
        {categories.map((category) => (
          <button
            type="button"
            className={selectedCategory === category.name ? "category-card active" : "category-card"}
            key={category.id}
            onClick={() => onChooseCategory(category.name)}
          >
            <div className="category-image">
              {category.image ? <img src={category.image} alt={category.name} /> : <span>{category.icon}</span>}
            </div>
            <h3>{category.name}</h3>
          </button>
        ))}
      </div>
    </section>
  );
}

export default CategoriesSection;
