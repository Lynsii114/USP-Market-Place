import React, { useState } from "react";
import OrderProgressTracker from "./OrderProgressTracker";

function PastPurchasesPage({ currentUser, purchases, initialTab = "track", onBack, onLogin, onConfirmReceived, onSubmitReview, isSubmitting }) {
  const [reviewingPurchase, setReviewingPurchase] = useState(null);
  const [reviewForm, setReviewForm] = useState({ rating: "5", review: "" });
  const isActiveOrder = (purchase) => !["completed", "cancelled", "canceled"].includes(purchase.order_stage || purchase.status);
  const activeOrders = purchases.filter(isActiveOrder);
  const orderHistory = purchases.filter((purchase) => !isActiveOrder(purchase));
  const activeOrdersTotal = activeOrders.reduce((total, purchase) => total + Number(purchase.total_amount || purchase.price), 0);
  const orderHistoryTotal = orderHistory.reduce((total, purchase) => total + Number(purchase.total_amount || purchase.price), 0);
  const deliveryMethodLabel = (method) => (method === "delivery" ? "Delivery" : "Self Pickup");

  const formatPurchaseDate = (value) =>
    new Date(value).toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  return (
    <section className="purchase-page" id="past-purchases">
      <div className="cart-header">
        <div className="section-heading">
          <span className="section-kicker">Report</span>
          <p>Items you have checked out, including purchase date and time.</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onBack} aria-label="Close past purchases">
          x
        </button>
      </div>

      {currentUser ? (
        purchases.length ? (
          <>
            {initialTab === "track" && (
              <div className="orders-section">
              <div className="orders-section-header">
                <h3>Track Orders</h3>
                <span>{activeOrders.length} active</span>
              </div>
              {activeOrders.length ? (
                <div className="purchase-report-list">
                  {activeOrders.map((purchase) => (
                    <div className="purchase-report-item" key={purchase.id}>
                      <div>
                        <strong>{purchase.item_name}</strong>
                        <small>{purchase.category}</small>
                      </div>
                      <div>
                        <span>${Number(purchase.total_amount || purchase.price).toFixed(2)}</span>
                        <small>
                          {deliveryMethodLabel(purchase.delivery_method)}
                          {Number(purchase.delivery_fee || 0) > 0 ? ` + $${Number(purchase.delivery_fee).toFixed(2)} delivery` : " - FREE"}
                        </small>
                      </div>
                      <time dateTime={purchase.purchased_at}>{formatPurchaseDate(purchase.purchased_at)}</time>
                      <div className="purchase-order-progress">
                        <OrderProgressTracker stage={purchase.order_stage} />
                        <div className="purchase-order-actions">
                          {purchase.order_stage === "ready_for_collection" && (
                            <button
                              type="button"
                              className="auth-submit"
                              onClick={() => onConfirmReceived(purchase)}
                              disabled={isSubmitting}
                            >
                              Confirm Item Received
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">No active orders to track.</p>
              )}
              <div className="purchase-total-card">
                <div>
                  <span>Active Orders Total</span>
                  <strong>${activeOrdersTotal.toFixed(2)}</strong>
                </div>
              </div>
              </div>
            )}

            {initialTab === "history" && (
              <div className="orders-section">
              <div className="orders-section-header">
                <h3>My Purchases</h3>
                <span>{orderHistory.length} saved</span>
              </div>
              <div className="purchase-report-table-head">
                <span>Item</span>
                <span>Unit Cost</span>
                <span>Date &amp; Time</span>
              </div>
              {orderHistory.length ? (
                <div className="purchase-report-list">
                  {orderHistory.map((purchase) => (
                    <div className="purchase-report-item" key={purchase.id}>
                      <div>
                        <strong>{purchase.item_name}</strong>
                        <small>{purchase.category}</small>
                      </div>
                      <div>
                        <span>${Number(purchase.total_amount || purchase.price).toFixed(2)}</span>
                        <small>
                          {deliveryMethodLabel(purchase.delivery_method)}
                          {Number(purchase.delivery_fee || 0) > 0 ? ` + $${Number(purchase.delivery_fee).toFixed(2)} delivery` : " - FREE"}
                        </small>
                      </div>
                      <time dateTime={purchase.purchased_at}>{formatPurchaseDate(purchase.purchased_at)}</time>
                      <div className="purchase-order-progress">
                        <div className="purchase-order-actions">
                          {purchase.order_stage === "completed" && !purchase.has_review && (
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={() => {
                                setReviewingPurchase(purchase);
                                setReviewForm({ rating: "5", review: "" });
                              }}
                            >
                              Rate & Review
                            </button>
                          )}
                          {purchase.has_review && <span className="review-submitted-label">Review submitted</span>}
                          {["cancelled", "canceled"].includes(purchase.order_stage || purchase.status) && (
                            <span className="review-submitted-label cancelled">Cancelled</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">Completed and cancelled orders will appear here.</p>
              )}
              <div className="purchase-total-card">
                <div>
                  <span>Order History Total</span>
                  <strong>${orderHistoryTotal.toFixed(2)}</strong>
                </div>
              </div>
              </div>
            )}

            {reviewingPurchase && (
              <div className="auth-modal-backdrop" onClick={() => setReviewingPurchase(null)}>
                <div className="checkout-review-modal" onClick={(event) => event.stopPropagation()}>
                  <div className="auth-header">
                    <div>
                      <span className="section-kicker">Rate & Review</span>
                      <h2>{reviewingPurchase.item_name}</h2>
                    </div>
                    <button type="button" className="close-button" onClick={() => setReviewingPurchase(null)} aria-label="Close">
                      x
                    </button>
                  </div>
                  <div className="feedback-block checkout-review-form">
                    <strong>Rating</strong>
                    <div className="rating-control" aria-label="Rating">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          type="button"
                          className={Number(reviewForm.rating) >= value ? "active" : ""}
                          onClick={() => setReviewForm((form) => ({ ...form, rating: String(value) }))}
                          key={value}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                    <textarea
                      value={reviewForm.review}
                      onChange={(event) => setReviewForm((form) => ({ ...form, review: event.target.value }))}
                      placeholder="Share a short review"
                      rows="4"
                    />
                    <div className="checkout-review-actions">
                      <button type="button" className="secondary-button" onClick={() => setReviewingPurchase(null)}>
                        Cancel
                      </button>
                      <button
                        type="button"
                        className="auth-submit"
                        onClick={async () => {
                          const saved = await onSubmitReview(reviewingPurchase, Number(reviewForm.rating), reviewForm.review);
                          if (saved) {
                            setReviewingPurchase(null);
                          }
                        }}
                        disabled={isSubmitting}
                      >
                        Submit Review
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="empty-state">No past purchases yet.</p>
        )
      ) : (
        <div className="signin-prompt">
          <p>Login to view your past purchases.</p>
          <button type="button" className="auth-submit" onClick={onLogin}>
            Login
          </button>
        </div>
      )}
    </section>
  );
}

export default PastPurchasesPage;
