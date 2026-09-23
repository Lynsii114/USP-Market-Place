import React from "react";

function SellerPanel({
  activeSellerTab,
  categories,
  currentUser,
  editingListingId,
  isSubmitting,
  listingForm,
  myListings,
  openListingMenuId,
  pendingPhoto,
  onClose,
  onDeleteListing,
  onEditListing,
  onFieldChange,
  onLogin,
  onMenuToggle,
  onViewListing,
  onPhotoChange,
  onPhotoConfirm,
  onPhotoRemove,
  onResetForm,
  onSubmit,
}) {
  return (
    <section className="seller-section" id="seller-listings">
      <div className="seller-panel-header">
        <div className="section-heading">
          <h2>{activeSellerTab === "add-listing" ? "Add Listing" : "My Listings"}</h2>
          <p>{activeSellerTab === "add-listing" ? "Create a new item for sale." : "Manage the items you want to sell."}</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onClose} aria-label="Close seller panel">
          x
        </button>
      </div>

      {currentUser ? (
        <>
          {activeSellerTab === "add-listing" ? (
            <form className="listing-form" onSubmit={onSubmit}>
              <label>
                JPG Photo
                <input type="file" accept=".jpg,.jpeg,image/jpeg" onChange={onPhotoChange} />
              </label>

              {listingForm.photo && (
                <div className="confirmed-photo">
                  <div className="photo-preview">
                    <img src={listingForm.photo} alt="Confirmed listing" />
                  </div>
                  <div>
                    <strong>Photo ready</strong>
                    <p>This photo will be saved with the listing.</p>
                    <button type="button" className="secondary-button" onClick={onPhotoRemove}>
                      Remove Photo
                    </button>
                  </div>
                </div>
              )}

              {pendingPhoto && (
                <div className="photo-review">
                  <div className="photo-preview">
                    <img src={pendingPhoto.dataUrl} alt="Photo selected for review" />
                  </div>
                  <div className="photo-review-details">
                    <span>Review JPG Photo</span>
                    <strong>{pendingPhoto.name}</strong>
                    <p>Check the image before attaching it to your listing.</p>
                    <div className="photo-review-actions">
                      <button type="button" className="auth-submit" onClick={onPhotoConfirm}>
                        Use This Photo
                      </button>
                      <button type="button" className="secondary-button" onClick={onPhotoRemove}>
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <label>
                Item Name
                <input
                  type="text"
                  name="name"
                  value={listingForm.name}
                  onChange={onFieldChange}
                  placeholder="Computer Science Textbook"
                  required
                />
              </label>

              <label>
                Price
                <input
                  type="number"
                  name="price"
                  value={listingForm.price}
                  onChange={onFieldChange}
                  min="0"
                  step="0.01"
                  placeholder="30.00"
                  required
                />
              </label>

              <label>
                Units in Stock
                <input
                  type="number"
                  name="stock"
                  value={listingForm.stock}
                  onChange={onFieldChange}
                  min="0"
                  step="1"
                  placeholder="1"
                  required
                />
              </label>

              <label>
                Category
                <select name="category" value={listingForm.category} onChange={onFieldChange} required>
                  {categories.map((category) => (
                    <option value={category.name} key={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Contact
                <input
                  type="text"
                  name="contact"
                  value={listingForm.contact}
                  onChange={onFieldChange}
                  placeholder="Phone, email, or preferred contact"
                  required
                />
              </label>

              <label className="listing-description">
                Description
                <textarea
                  name="description"
                  value={listingForm.description}
                  onChange={onFieldChange}
                  placeholder="Condition, pickup location, or extra details"
                  rows="4"
                  required
                />
              </label>

              <div className="listing-actions">
                <button type="submit" className="auth-submit" disabled={isSubmitting}>
                  {isSubmitting ? "Saving..." : editingListingId ? "Update Listing" : "Add Listing"}
                </button>
                {editingListingId && (
                  <button type="button" className="secondary-button" onClick={onResetForm}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          ) : (
            <div className="my-listings">
              <h3>My Listings</h3>
              {myListings.length ? (
                <div className="seller-list">
                  {myListings.map((listing) => (
                    <div className="seller-list-item" key={listing.id}>
                      <div className="seller-list-details">
                        <strong>{listing.name}</strong>
                        <span>
                          ${Number(listing.price).toFixed(2)} - {listing.category} -{" "}
                          {listing.status === "sold" || Number(listing.stock) <= 0 ? "Sold" : `${listing.stock} in stock`}
                        </span>
                      </div>
                      <div className="admin-action-dropdown">
                        <button
                          type="button"
                          className="admin-action-trigger"
                          aria-label={`Open actions for ${listing.name}`}
                          aria-expanded={openListingMenuId === listing.id}
                          onClick={() => onMenuToggle(listing.id)}
                        >
                          Actions
                        </button>
                        {openListingMenuId === listing.id && (
                          <div className="admin-action-menu">
                            <button type="button" onClick={() => onViewListing(listing)}>
                              View Listing
                            </button>
                            <button type="button" onClick={() => onEditListing(listing)}>
                              Edit Listing
                            </button>
                            <div className="admin-action-divider" />
                            <button type="button" className="danger-action" onClick={() => onDeleteListing(listing.id)}>
                              Remove Listing
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">You have not listed any items yet.</p>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="signin-prompt">
          <p>Login or sign up to create and manage your item listings.</p>
          <button type="button" className="auth-submit" onClick={onLogin}>
            Login to Sell
          </button>
        </div>
      )}
    </section>
  );
}

export default SellerPanel;
