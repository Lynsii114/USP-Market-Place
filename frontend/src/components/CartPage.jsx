import React, { useState } from "react";

function CartPage({
  cartItems,
  cartTotal,
  currentUser,
  receipt,
  onCheckout,
  onClearReceipt,
  onClose,
  onRemove,
  isSubmitting,
}) {
  const [checkoutStep, setCheckoutStep] = useState("cart");
  const [deliveryMethod, setDeliveryMethod] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const deliveryOptions = [
    { value: "self_pickup", label: "Self Pickup", detail: "FREE", fee: 0 },
    { value: "delivery", label: "Delivery", detail: "Delivery fee applies", fee: 5 },
  ];
  const paymentOptions = [
    { value: "mycash", label: "MyCash" },
    { value: "mpaisa", label: "M-PAiSA" },
    { value: "cash", label: "Cash" },
    { value: "visa", label: "Visa Card" },
  ];
  const itemCount = cartItems.length;
  const availableItems = cartItems.filter(
    (item) =>
      item.status !== "sold" &&
      Number(item.stock) > 0 &&
      (item.status !== "reserved" || item.reserved_buyer_id === currentUser?.id)
  );
  const hasAvailableItems = availableItems.length > 0;
  const itemsSubtotal = availableItems.reduce((total, item) => total + Number(item.price), 0);
  const selectedDeliveryOption = deliveryOptions.find((option) => option.value === deliveryMethod);
  const deliveryFee = selectedDeliveryOption?.fee ?? 0;
  const includedTaxAmount = itemsSubtotal * 12 / 112;
  const finalTotal = itemsSubtotal + deliveryFee;
  const checkoutSummary = {
    delivery_method: deliveryMethod,
    delivery_fee: deliveryFee,
    subtotal: itemsSubtotal,
    included_tax_amount: includedTaxAmount,
    final_total: finalTotal,
    item_count: availableItems.length,
  };
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
          {receipt.paymentMethod && (
            <div className="receipt-total">
              <span>Payment Method</span>
              <strong>{receipt.paymentMethod}</strong>
            </div>
          )}

          <button
            type="button"
            className="auth-submit"
            onClick={() => {
              setCheckoutStep("cart");
              setDeliveryMethod("");
              setPaymentMethod("");
              onClearReceipt();
              onClose();
            }}
          >
            Continue Shopping
          </button>
        </div>
      ) : checkoutStep === "delivery" ? (
        <div className="checkout-confirmation">
          <div className="receipt-header">
            <div>
              <span className="section-kicker">Delivery Method</span>
              <h3>Choose How You Receive Your Order</h3>
              <p>Select one option before reviewing checkout costs.</p>
            </div>
            <span>
              {availableItems.length} {availableItems.length === 1 ? "item" : "items"}
            </span>
          </div>

          <div className="payment-method-panel">
            <span>Delivery Method</span>
            <div className="delivery-method-options">
              {deliveryOptions.map((option) => (
                <label className={deliveryMethod === option.value ? "payment-option selected" : "payment-option"} key={option.value}>
                  <input
                    type="radio"
                    name="delivery_method"
                    value={option.value}
                    checked={deliveryMethod === option.value}
                    onChange={(event) => setDeliveryMethod(event.target.value)}
                  />
                  <span>
                    <strong>{option.label}</strong>
                    <small>{option.detail}</small>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="checkout-actions">
            <button type="button" className="secondary-button" onClick={() => setCheckoutStep("cart")}>
              Back to Cart
            </button>
            <button type="button" className="auth-submit" onClick={() => setCheckoutStep("confirm")} disabled={!deliveryMethod}>
              Continue to Confirm Checkout
            </button>
          </div>
        </div>
      ) : checkoutStep === "confirm" ? (
        <div className="checkout-confirmation">
          <div className="receipt-header">
            <div>
              <span className="section-kicker">Confirm Checkout</span>
              <h3>Review Costs Before Payment</h3>
              <p>Prices include 12% tax.</p>
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
                  <span>Qty 1</span>
                  <small>Quantity</small>
                </div>
                <div>
                  <span>${Number(item.price).toFixed(2)}</span>
                  <small>Item price</small>
                </div>
              </div>
            ))}
          </div>

          <div className="receipt-total">
            <span>Items Subtotal</span>
            <strong>${itemsSubtotal.toFixed(2)}</strong>
          </div>
          <div className="receipt-total subtle-total">
            <span>12% Tax Included in Item Prices</span>
            <strong>${includedTaxAmount.toFixed(2)}</strong>
          </div>
          <div className="receipt-total subtle-total">
            <span>Selected Delivery Method</span>
            <strong>{selectedDeliveryOption?.label}</strong>
          </div>
          <div className="receipt-total subtle-total">
            <span>Delivery Fee</span>
            <strong>{deliveryFee > 0 ? `$${deliveryFee.toFixed(2)}` : "FREE"}</strong>
          </div>
          <div className="receipt-total final-total">
            <span>Final Total</span>
            <strong>${finalTotal.toFixed(2)}</strong>
          </div>

          <div className="payment-method-panel">
            <span>Payment Method</span>
            <div className="payment-method-options">
              {paymentOptions.map((option) => (
                <label className={paymentMethod === option.value ? "payment-option selected" : "payment-option"} key={option.value}>
                  <input
                    type="radio"
                    name="payment_method"
                    value={option.value}
                    checked={paymentMethod === option.value}
                    onChange={(event) => setPaymentMethod(event.target.value)}
                  />
                  <strong>{option.label}</strong>
                </label>
              ))}
            </div>
          </div>

          <div className="checkout-actions">
            <button type="button" className="secondary-button" onClick={() => setCheckoutStep("delivery")}>
              Back
            </button>
            <button type="button" className="auth-submit" onClick={() => onCheckout(paymentMethod, checkoutSummary)} disabled={isSubmitting || !paymentMethod}>
              {isSubmitting ? "Processing..." : "Confirm & Pay"}
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
              onClick={() => setCheckoutStep("delivery")}
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
