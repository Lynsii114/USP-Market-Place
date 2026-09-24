import React, { useState } from "react";
import OrderProgressTracker from "./OrderProgressTracker";

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
  sellerOrders,
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
  onLoadReservationBuyers,
  onReserveListing,
  onUpdateListingStatus,
  onUpdateOrderStage,
}) {
  const activeSellerOrders = sellerOrders.filter((order) => order.order_stage !== "completed" && order.status !== "completed");
  const deliveryMethodLabel = (method) => (method === "delivery" ? "Delivery" : "Self Pickup");
  const [reservationListing, setReservationListing] = useState(null);
  const [reservationBuyers, setReservationBuyers] = useState([]);
  const [selectedReservationBuyer, setSelectedReservationBuyer] = useState("");
  const [isLoadingReservationBuyers, setIsLoadingReservationBuyers] = useState(false);

  const openReservationModal = async (listing) => {
    setReservationListing(listing);
    setReservationBuyers([]);
    setSelectedReservationBuyer("");
    setIsLoadingReservationBuyers(true);
    const buyers = await onLoadReservationBuyers(listing);
    setReservationBuyers(buyers);
    setSelectedReservationBuyer(buyers[0]?.id ? String(buyers[0].id) : "");
    setIsLoadingReservationBuyers(false);
  };

  const confirmReservation = async () => {
    if (!reservationListing || !selectedReservationBuyer) {
      return;
    }
    const buyer = reservationBuyers.find((item) => String(item.id) === selectedReservationBuyer);
    if (!window.confirm(`Reserve ${reservationListing.name} for ${buyer?.username || "this buyer"}?`)) {
      return;
    }
    const saved = await onReserveListing(reservationListing, Number(selectedReservationBuyer));
    if (saved) {
      setReservationListing(null);
    }
  };

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
                          {listing.status === "reserved"
                            ? `Reserved for ${listing.reserved_buyer_username || "buyer"}`
                            : listing.status === "sold" || Number(listing.stock) <= 0
                              ? "Sold"
                              : listing.status === "hidden"
                                ? "Inactive"
                                : `${listing.stock} in stock`}
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
                              Edit
                            </button>
                            {listing.status === "reserved" ? (
                              <button type="button" onClick={() => onUpdateListingStatus(listing, "available")}>
                                Cancel Reservation
                              </button>
                            ) : (
                              <button type="button" onClick={() => openReservationModal(listing)} disabled={listing.status === "sold" || Number(listing.stock) <= 0}>
                                Mark as Reserved
                              </button>
                            )}
                            <button type="button" onClick={() => onUpdateListingStatus(listing, "sold")} disabled={listing.status === "sold"}>
                              Mark as Sold
                            </button>
                            <div className="admin-action-divider" />
                            <button type="button" className="danger-action" onClick={() => onUpdateListingStatus(listing, "hidden")}>
                              Deactivate
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
              <div className="seller-orders-panel">
                <h3>Active Order Progress</h3>
                {activeSellerOrders.length ? (
                  <div className="seller-order-list">
                    {activeSellerOrders.map((order) => (
                      <div className="seller-order-card" key={order.id}>
                        <div className="seller-order-header">
                          <div>
                            <strong>{order.item_name}</strong>
                            <span>
                              Buyer: {order.buyer_username} - {deliveryMethodLabel(order.delivery_method)}
                            </span>
                          </div>
                          <strong>${Number(order.total_amount || order.price).toFixed(2)}</strong>
                        </div>
                        <OrderProgressTracker stage={order.order_stage} />
                        <div className="seller-order-actions">
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => onUpdateOrderStage(order, "preparing_item")}
                            disabled={["preparing_item", "ready_for_collection", "completed"].includes(order.order_stage)}
                          >
                            Preparing Item
                          </button>
                          <button
                            type="button"
                            className="auth-submit"
                            onClick={() => onUpdateOrderStage(order, "ready_for_collection")}
                            disabled={order.order_stage !== "preparing_item"}
                          >
                            On the Way
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">No buyer orders for your listings yet.</p>
                )}
              </div>
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
      {reservationListing && (
        <div className="nested-modal-backdrop" onClick={() => setReservationListing(null)}>
          <div className="report-modal" onClick={(event) => event.stopPropagation()}>
            <div className="auth-header">
              <div>
                <span className="section-kicker">Reserve Item</span>
                <h3>{reservationListing.name}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setReservationListing(null)} aria-label="Close">
                x
              </button>
            </div>
            <div className="feedback-block">
              {isLoadingReservationBuyers ? (
                <p className="empty-state">Loading buyers...</p>
              ) : reservationBuyers.length ? (
                <>
                  <label>
                    Buyer who messaged about this item
                    <select value={selectedReservationBuyer} onChange={(event) => setSelectedReservationBuyer(event.target.value)}>
                      {reservationBuyers.map((buyer) => (
                        <option value={buyer.id} key={buyer.id}>
                          {buyer.username}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="feedback-actions">
                    <button type="button" className="secondary-button" onClick={() => setReservationListing(null)}>
                      Cancel
                    </button>
                    <button type="button" className="auth-submit" onClick={confirmReservation} disabled={!selectedReservationBuyer}>
                      Confirm Reservation
                    </button>
                  </div>
                </>
              ) : (
                <p className="empty-state">No buyers have messaged about this item yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default SellerPanel;
