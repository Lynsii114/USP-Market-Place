import React, { useState } from "react";

function CartPage({
  cartItems,
  cartTotal,
  receipt,
  onCheckout,
  onClearReceipt,
  onClose,
  onRemove,
  isSubmitting,
}) {
  const [isConfirmingCheckout, setIsConfirmingCheckout] = useState(false);
  const itemCount = cartItems.length;
  const availableItems = cartItems.filter((item) => item.status !== "sold" && Number(item.stock) > 0);
  const hasAvailableItems = availableItems.length > 0;
  const confirmationTotal = availableItems.reduce((total, item) => total + Number(item.price), 0);
  return (
    <section className="cart-section cart-page" id="cart">
      <div className="cart-header">
        <div className="section-heading">
          <span className="section-kicker">Saved Items</span>
          <h2>Your Cart</h2>
          <p>Review selected marketplace items before contacting each seller.</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onClose} aria-label="Close cart">
          x
        </button>
      </div>

      {receipt ? (
        <div className="receipt-panel">
          <div className="receipt-header">
            <div>
              <span className="section-kicker">Receipt</span>
              <h3>Checkout Successful</h3>
              <p>{receipt.id}</p>
            </div>
            <span>{receipt.purchasedAt}</span>
          </div>

          <div className="receipt-list">
            {receipt.items.map((item) => (
              <div className="receipt-item" key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <small>Seller: {item.seller_username}</small>
                </div>
                <div>
                  <span>${Number(item.price).toFixed(2)}</span>
                  <small>{item.status === "sold" || Number(item.stock) <= 0 ? "Sold" : `${item.stock} left`}</small>
                </div>
              </div>
            ))}
          </div>

          <div className="receipt-total">
            <span>Total Paid</span>
            <strong>${Number(receipt.total).toFixed(2)}</strong>
          </div>

          <button
            type="button"
            className="auth-submit"
            onClick={() => {
              setIsConfirmingCheckout(false);
              onClearReceipt();
              onClose();
            }}
          >
            Continue Shopping
          </button>
        </div>
      ) : isConfirmingCheckout ? (
        <div className="checkout-confirmation">
          <div className="receipt-header">
            <div>
              <span className="section-kicker">Confirm Order</span>
              <h3>Review Your Order</h3>
              <p>Please confirm these items before checkout.</p>
            </div>
            <span>
              {availableItems.length} {availableItems.length === 1 ? "item" : "items"}
            </span>
          </div>

          <div className="receipt-list">
            {availableItems.map((item) => (
              <div className="receipt-item" key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <small>Seller: {item.seller_username}</small>
                </div>
                <div>
                  <span>${Number(item.price).toFixed(2)}</span>
                  <small>{item.stock} in stock</small>
                </div>
              </div>
            ))}
          </div>

          <div className="receipt-total">
            <span>Total</span>
            <strong>${confirmationTotal.toFixed(2)}</strong>
          </div>

          <div className="checkout-actions">
            <button type="button" className="secondary-button" onClick={() => setIsConfirmingCheckout(false)}>
              Back to Cart
            </button>
            <button type="button" className="auth-submit" onClick={onCheckout} disabled={isSubmitting}>
              {isSubmitting ? "Checking Out..." : "Confirm Checkout"}
            </button>
          </div>
        </div>
      ) : cartItems.length ? (
        <div className="cart-layout">
          <div className="cart-list">
            <div className="cart-list-heading">
              <strong>
                {itemCount} {itemCount === 1 ? "item" : "items"}
              </strong>
              <span>Ready for seller contact</span>
            </div>
            {cartItems.map((item) => (
              <div className="cart-item" key={item.id}>
                <div className="cart-item-image">
                  {item.photo ? <img src={item.photo} alt={item.name} /> : <span>{item.category}</span>}
                </div>
                <div className="cart-item-details">
                  <div>
                    <strong>{item.name}</strong>
                    <small>{item.category}</small>
                  </div>
                  <div className="cart-seller">
                    <span>Seller</span>
                    <strong>{item.seller_username}</strong>
                  </div>
                </div>
                <div className="cart-item-action">
                  <span>${Number(item.price).toFixed(2)}</span>
                  <small>{Number(item.stock) > 0 ? `${item.stock} in stock` : "Sold"}</small>
                  <button type="button" className="secondary-button" onClick={() => onRemove(item.id)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="cart-summary">
            <div>
              <span>Cart Total</span>
              <strong>${cartTotal.toFixed(2)}</strong>
            </div>
            <button
              type="button"
              className="auth-submit"
              onClick={() => setIsConfirmingCheckout(true)}
              disabled={isSubmitting || !hasAvailableItems}
            >
              Checkout
            </button>
          </div>
        </div>
      ) : (
        <div className="cart-empty">
          <strong>Your cart is empty.</strong>
          <p>Add items from recent listings or categories to keep them here.</p>
          <button type="button" className="auth-submit" onClick={onClose}>
            Browse Items
          </button>
        </div>
      )}

    </section>
  );
}

export default CartPage;
