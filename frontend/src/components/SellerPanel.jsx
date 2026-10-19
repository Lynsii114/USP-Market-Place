import ContextHelp from "./ContextHelp";
import React, { useEffect, useState } from "react";
import OrderProgressTracker from "./OrderProgressTracker";
import { LISTING_PHOTO_ACCEPT } from "../utils/listingPhoto";
import ListingActionsMenu from "./ListingActionsMenu";
import { inventorySummary, sellerListingStatus, availableStock } from "../utils/inventory.mjs";

function SellerPanel({
  onOpenHelp,
  activeSellerTab,
  categories,
  currentUser,
  editingListingId,
  isSubmitting,
  isProcessingPhoto,
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
  onCloseMenu,
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
  onConfirmPaymentReceived,
  onCancelOrder,
}) {
  const activeSellerOrders = sellerOrders.filter(
    (order) => !["completed", "cancelled", "canceled"].includes(order.order_stage || order.status)
  );
  const deliveryMethodLabel = (method) => (method === "delivery" ? "Delivery" : "Self Pickup");
  const [reservationListing, setReservationListing] = useState(null);
  const [reservationBuyers, setReservationBuyers] = useState([]);
  const [selectedReservationBuyer, setSelectedReservationBuyer] = useState("");
  const [isLoadingReservationBuyers, setIsLoadingReservationBuyers] = useState(false);
  const [inventorySearch, setInventorySearch] = useState("");
  const [inventoryStatus, setInventoryStatus] = useState("all");
  const [inventoryPage, setInventoryPage] = useState(1);
  const summary = inventorySummary(myListings);
  const search = inventorySearch.trim().toLowerCase();
  const matchingListings = myListings.filter((listing) =>
    (!search || `${listing.name} ${listing.description} ${listing.category}`.toLowerCase().includes(search)) &&
    (inventoryStatus === "all" || sellerListingStatus(listing) === inventoryStatus)
  );
  const pageSize = 10;
  const pageCount = Math.max(1, Math.ceil(matchingListings.length / pageSize));
  const currentPage = Math.min(inventoryPage, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const visibleListings = matchingListings.slice(pageStart, pageStart + pageSize);
  const pageNumbers = [...new Set([1, currentPage - 1, currentPage, currentPage + 1, pageCount])]
    .filter((page) => page >= 1 && page <= pageCount).sort((a, b) => a - b);

  useEffect(() => { setInventoryPage(1); }, [currentUser?.id]);
  useEffect(() => { setInventoryPage((page) => Math.min(page, pageCount)); }, [pageCount]);

  const changeInventoryPage = (page) => {
    setInventoryPage(page);
    onCloseMenu();
    document.getElementById("inventory-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

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
              <div className="listing-photo-field">
                <label>
                  Item Photo (required)
                  <input type="file" accept={LISTING_PHOTO_ACCEPT} onChange={onPhotoChange} aria-describedby="listing-photo-help" />
                </label>
                <p className="listing-photo-help" id="listing-photo-help">JPEG, PNG, WebP or AVIF. Max 5 MB.</p>
                {isProcessingPhoto && <p role="status">Preparing photo previewâ€¦</p>}
              </div>

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
                    <span>Review Photo</span>
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
                  maxLength={256}
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
                  min="0.01"
                  max="999999999.99"
                  step="0.01"
                  required
                />
              </label>

              <div className="listing-quantity">
                <div className="field-label-row"><label className="multiple-units-toggle">
                  <input
                    type="checkbox"
                    name="multiple_units"
                    checked={Boolean(listingForm.multiple_units)}
                    onChange={onFieldChange}
                  />
                  Multiple units
                </label>
                <ContextHelp label="Help with multiple units" topic="listing" onOpenHelp={onOpenHelp}>Enable this for several identical items at the same price per unit. Leave it unchecked to sell one item. The available quantity decreases as units are bought or reserved.</ContextHelp></div>
                {listingForm.multiple_units ? (
                  <label>
                    Quantity available
                    <input
                      className="listing-stock-input"
                      type="number"
                      name="stock"
                      value={listingForm.stock}
                      onChange={onFieldChange}
                      min="1"
                      step="1"
                      max="2147483647"
                      required
                    />
                  </label>
                ) : (
                  <small>{Number(listingForm.stock) === 0 ? "Sold out. Enable multiple units to enter a restock quantity." : "One item will be listed."}</small>
                )}
              </div>

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
                  maxLength={128}
                  required
                />
              </label>

              <label>
                Preferred Payment Method
                <select name="payment_method" value={listingForm.payment_method} onChange={onFieldChange} required>
                  <option value="cash">Cash</option>
                  <option value="mpaisa">M-PAiSA</option>
                  <option value="mycash">MyCash</option>
                </select>
              </label>

              {["mpaisa", "mycash"].includes(listingForm.payment_method) && (
                <label>
                  {listingForm.payment_method === "mpaisa" ? "M-PAiSA" : "MyCash"} Receiving Number
                  <input
                    type="tel"
                    name="payment_number"
                    value={listingForm.payment_number}
                    onChange={onFieldChange}
                    placeholder="e.g. +679 9000000"
                    autoComplete="tel"
                    required
                  />
                </label>
              )}

              <label className="listing-description">
                Description
                <textarea
                  name="description"
                  value={listingForm.description}
                  onChange={onFieldChange}
                  placeholder="Condition, pickup location, or extra details"
                  rows="4"
                  maxLength={1000}
                  required
                />
              </label>

              <div className="listing-actions">
                <button type="submit" className="auth-submit" disabled={isSubmitting || isProcessingPhoto}>
                  {isProcessingPhoto ? "Preparing photo..." : isSubmitting ? "Saving..." : editingListingId ? "Update Listing" : "Add Listing"}
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
              <div className="inventory-toolbar">
                <div className="inventory-overview" aria-label="Inventory summary">
                  <span><strong>{summary.total}</strong> {summary.total === 1 ? "listing" : "listings"}</span>
                  <span><strong>{summary.units}</strong> {summary.units === 1 ? "unit" : "units"} available</span>
                </div>
                <label className="inventory-search">
                  <span className="sr-only">Search My Listings</span>
                  <input type="search" placeholder="Search your listings" value={inventorySearch} onChange={(event) => { setInventorySearch(event.target.value); setInventoryPage(1); onCloseMenu(); }} />
                </label>
                {(inventorySearch || inventoryStatus !== "all") && <button type="button" className="inventory-clear" onClick={() => { setInventorySearch(""); setInventoryStatus("all"); setInventoryPage(1); onCloseMenu(); }}>Clear filters</button>}
              </div>
              <div className="inventory-status-filters" role="group" aria-label="Filter listings by status">
                {[["all", "All", summary.total], ["available", "Available", summary.available], ["reserved", "Reserved", summary.reserved], ["sold", "Sold", summary.sold], ["inactive", "Inactive", summary.inactive]].map(([value, label, count]) => (
                  <button key={value} type="button" aria-pressed={inventoryStatus === value} onClick={() => { setInventoryStatus(value); setInventoryPage(1); onCloseMenu(); }}>
                    {label}<span className="inventory-status-count">{count}</span>
                  </button>
                ))}
              </div>
              <p className="inventory-result-count" id="inventory-results" role="status">
                {matchingListings.length ? `Showing ${pageStart + 1}â€“${pageStart + visibleListings.length} of ${matchingListings.length} listings` : "Showing 0 listings"}
                {(inventorySearch || inventoryStatus !== "all") && ` (${myListings.length} total)`}
              </p>
              {matchingListings.length ? (
                <div className="seller-list">
                  {visibleListings.map((listing) => {
                    const pendingPaymentOrder = sellerOrders.find(
                      (order) =>
                        order.item_id === listing.id &&
                        order.payment_status === "pending",
                    );
                    return (
                    <div className="seller-list-item" key={listing.id}>
                      <div className="seller-list-details">
                        <strong>{listing.name}</strong>
                        <span>
                          ${Number(listing.price).toFixed(2)} - {listing.category} -{" "}
                          {listing.admin_restricted
                            ? "Hidden by administrator"
                            : listing.status === "hidden"
                              ? "Inactive"
                              : listing.status === "reserved"
                                ? `Reserved for ${listing.reserved_buyer_username || "buyer"}`
                                : listing.status === "sold" || Number(listing.stock) <= 0
                                  ? "Sold"
                                  : `${availableStock(listing)} available${listing.reserved_stock ? `, ${listing.reserved_stock} reserved` : ""}`}
                        </span>
                      </div>
                      {listing.admin_restricted && <p>{listing.removed_reason || "Contact an administrator to restore this listing."}</p>}
                      <ListingActionsMenu listing={listing} isOpen={openListingMenuId === listing.id} onToggle={() => onMenuToggle(listing.id)} onClose={onCloseMenu}>
                            <button type="button" onClick={() => onViewListing(listing)}>
                              View Listing
                            </button>
                            <button type="button" disabled={listing.admin_restricted || isSubmitting} onClick={() => onEditListing(listing)}>
                              Edit
                            </button>
                            {listing.status === "reserved" || pendingPaymentOrder || listing.manual_reserved_stock > 0 ? (
                              <button
                                type="button"
                                onClick={() =>
                                  listing.manual_reserved_stock > 0
                                    ? onUpdateListingStatus(listing, "available")
                                    : pendingPaymentOrder
                                      ? onCancelOrder(pendingPaymentOrder)
                                      : onUpdateListingStatus(listing, "available")
                                }
                              >
                                {pendingPaymentOrder && !listing.manual_reserved_stock ? "Release Unpaid Order" : "Cancel Reservation"}
                              </button>
                            ) : (
                              <button type="button" onClick={() => openReservationModal(listing)} disabled={listing.admin_restricted || listing.status === "hidden" || listing.status === "sold" || Number(listing.stock) <= 0 || isSubmitting}>
                                Reserve One Unit
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => onUpdateListingStatus(listing, "sold")}
                              disabled={listing.admin_restricted || listing.status === "sold" || Boolean(pendingPaymentOrder) || isSubmitting}
                            >
                              Mark as Sold
                            </button>
                            <div className="admin-action-divider" />
                            <button type="button" disabled={listing.admin_restricted || Boolean(pendingPaymentOrder) || isSubmitting || (listing.status === "hidden" && Number(listing.stock) <= 0)} className="danger-action" onClick={() => onUpdateListingStatus(listing, listing.status === "hidden" ? "available" : "hidden")}>
                              {listing.status === "hidden" ? "Reactivate" : "Deactivate"}
                            </button>
                      </ListingActionsMenu>
                    </div>
                    );
                  })}
                </div>
              ) : (
                <p className="empty-state">{myListings.length ? "No listings match your filters." : "You have not listed any items yet."}</p>
              )}
              {pageCount > 1 && (
                <nav className="inventory-pagination" aria-label="My Listings pages">
                  <button type="button" className="secondary-button" disabled={currentPage === 1} onClick={() => changeInventoryPage(currentPage - 1)}>Previous</button>
                  {pageNumbers.map((page, index) => (
                    <React.Fragment key={page}>
                      {index > 0 && page - pageNumbers[index - 1] > 1 && <span aria-hidden="true">â€¦</span>}
                      <button type="button" className="secondary-button" aria-label={`Page ${page}`} aria-current={page === currentPage ? "page" : undefined} onClick={() => changeInventoryPage(page)}>{page}</button>
                    </React.Fragment>
                  ))}
                  <button type="button" className="secondary-button" disabled={currentPage === pageCount} onClick={() => changeInventoryPage(currentPage + 1)}>Next</button>
                </nav>
              )}
              <div className="seller-orders-panel">
                <div className="field-label-row"><h3>Active Order Progress</h3><ContextHelp label="Help with order progress" topic="orders" onOpenHelp={onOpenHelp}>Track payment, preparation and handoff separately. A reservation holds stock while payment is pending. Sold out describes the listing’s remaining stock, rather than the order’s delivery progress.</ContextHelp></div>
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
                            <span>
                              Payment: {order.payment_method === "mpaisa" ? "M-PAiSA" : order.payment_method === "mycash" ? "MyCash" : order.payment_method === "visa" ? "VISA" : "Cash"} -{" "}
                              {order.payment_status === "paid"
                                ? "Seller confirmed received"
                                : order.payment_status === "approved"
                                  ? "Approved (demo)"
                                  : order.payment_status === "cancelled"
                                    ? "Cancelled"
                                    : "Awaiting payment"}
                            </span>
                            {order.payment_reference && <span>Payment reference: {order.payment_reference}</span>}
                          </div>
                          <strong>${Number(order.total_amount || order.price).toFixed(2)}</strong>
                        </div>
                        {order.payment_status === "pending" && (
                          <p className="seller-order-payment-note">
                            The ordered units are reserved. Confirm cash only after you receive it at delivery or pickup, or release the reservation if the buyer cancels.
                          </p>
                        )}
                        <OrderProgressTracker stage={order.order_stage} />
                        <div className="seller-order-actions">
                          {order.payment_status === "pending" && (
                            <button
                              type="button"
                              className="auth-submit"
                              onClick={() => onConfirmPaymentReceived(order)}
                              disabled={isSubmitting}
                            >
                              {order.payment_method === "cash" ? "Confirm Cash Received" : "Confirm Payment Received"}
                            </button>
                          )}
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => onUpdateOrderStage(order, "preparing_item")}
                            disabled={
                              order.payment_status === "pending" ||
                              ["preparing_item", "ready_for_collection", "completed"].includes(order.order_stage)
                            }
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
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => onCancelOrder(order)}
                            disabled={isSubmitting}
                          >
                            {order.payment_status === "pending"
                              ? "Release Reservation"
                              : "Cancel Order"}
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
