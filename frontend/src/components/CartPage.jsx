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
  onQuantityChange,
  onViewSeller,
  isSubmitting,
}) {
  const [checkoutStep, setCheckoutStep] = useState("cart");
  const [deliveryMethod, setDeliveryMethod] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [paymentDetails, setPaymentDetails] = useState({});
  const [forceFailure, setForceFailure] = useState(false);
  const [paymentError, setPaymentError] = useState("");
  const deliveryOptions = [
    { value: "self_pickup", label: "Self Pickup", detail: "FREE", fee: 0 },
    { value: "delivery", label: "Delivery", detail: "Delivery fee applies", fee: 5 },
  ];
  const paymentOptions = [
    { value: "mpaisa", label: "M-PAiSA", icon: "M", detail: "Mobile money (demo)" },
    { value: "mycash", label: "MyCash", icon: "C", detail: "Mobile money (demo)" },
    { value: "visa", label: "VISA", icon: "V", detail: "Card (demo)" },
    { value: "cash", label: "Cash", icon: "$", detail: "Cash on handoff (demo)" },
  ];
  const quantityFor = (item) => Math.min(Math.max(Number(item.quantity || 1), 1), Math.max(Number(item.stock) || 1, 1));
  const lineTotalFor = (item) => Number(item.price) * quantityFor(item);
  const itemCount = cartItems.reduce((total, item) => total + quantityFor(item), 0);
  const availableItems = cartItems.filter(
    (item) =>
      item.status !== "sold" &&
      Number(item.stock) > 0 &&
      (item.status !== "reserved" || item.reserved_buyer_id === currentUser?.id)
  );
  const hasAvailableItems = availableItems.length > 0;
  const itemsSubtotal = availableItems.reduce((total, item) => total + lineTotalFor(item), 0);
  const selectedDeliveryOption = deliveryOptions.find((option) => option.value === deliveryMethod);
  const deliveryFee = selectedDeliveryOption?.fee ?? 0;
  const finalTotal = itemsSubtotal + deliveryFee;
  const checkoutSummary = {
    delivery_method: deliveryMethod,
    delivery_fee: deliveryFee,
    subtotal: itemsSubtotal,
    final_total: finalTotal,
    item_count: itemCount,
  };
  const paymentDetailsComplete =
    paymentMethod === "cash" ||
    (paymentMethod === "visa"
      ? paymentDetails.cardholder_name && paymentDetails.card_number && paymentDetails.expiry && paymentDetails.security_code
      : paymentDetails.phone_number && paymentDetails.authorization_code);
  const handleCheckout = async () => {
    setPaymentError("");
    try {
      await onCheckout(paymentMethod, checkoutSummary, paymentDetails, forceFailure);
    } catch (error) {
      setPaymentError(error instanceof Error ? error.message : "Unable to process simulated payment");
    }
  };

  return (
    <section className="cart-section cart-page" id="cart">
      <div className="cart-header">
        <div className="section-heading">
          <span className="section-kicker">Saved Items</span>
          <h2>Your Cart</h2>
          <p>Select a payment method to complete this simulated checkout.</p>
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
              <h3>Payment Successful</h3>
              <p>{receipt.id}</p>
            </div>
            <span>{receipt.purchasedAt}</span>
          </div>

          <div className="receipt-list">
            {receipt.items.map((item) => (
              <div className="receipt-item" key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <small>Order #{item.id}</small>
                  <small>
                    Seller:{" "}
                    <button type="button" className="seller-inline-link" onClick={() => onViewSeller?.(item)}>
                      {item.seller_username}
                    </button>
                  </small>
                </div>
                <div>
                  <span>${Number(item.total_amount || item.price * item.quantity).toFixed(2)}</span>
                  <small>Qty {item.quantity}</small>
                  <small>${Number(item.price).toFixed(2)} each</small>
                </div>
              </div>
            ))}
          </div>

          <div className="receipt-total">
            <span>Total Paid (Simulated)</span>
            <strong>${Number(receipt.total).toFixed(2)}</strong>
          </div>
          <div className="receipt-total">
            <span>Payment Method</span>
            <strong>{receipt.paymentMethod}</strong>
          </div>
          {receipt.paymentReference && (
            <div className="receipt-total">
              <span>Payment Reference</span>
              <strong>{receipt.paymentReference}</strong>
            </div>
          )}
          <p className="auth-subtitle">Payment recorded. Contact the seller to arrange meetup/collection.</p>
          <p className="auth-subtitle">This is a simulated transaction; no real money was moved.</p>

          <button
            type="button"
            className="auth-submit"
            onClick={() => {
              setCheckoutStep("cart");
              setDeliveryMethod("");
              setPaymentMethod("");
              setPaymentDetails({});
              setForceFailure(false);
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
              {itemCount} {itemCount === 1 ? "item" : "items"}
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
              <h3>Review Costs and Choose Payment</h3>
            </div>
            <span>
              {itemCount} {itemCount === 1 ? "item" : "items"}
            </span>
          </div>

          <div className="receipt-list">
            {availableItems.map((item) => (
              <div className="receipt-item" key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <small>
                    Seller:{" "}
                    <button type="button" className="seller-inline-link" onClick={() => onViewSeller?.(item)}>
                      {item.seller_username}
                    </button>
                  </small>
                </div>
                <div>
                  <span>Qty {quantityFor(item)}</span>
                  <small>Quantity</small>
                </div>
                <div>
                  <span>${lineTotalFor(item).toFixed(2)}</span>
                  <small>${Number(item.price).toFixed(2)} each</small>
                </div>
              </div>
            ))}
          </div>

          <div className="receipt-total">
            <span>Items Subtotal</span>
            <strong>${itemsSubtotal.toFixed(2)}</strong>
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
                    onChange={(event) => {
                      setPaymentMethod(event.target.value);
                      setPaymentDetails({});
                      setPaymentError("");
                    }}
                  />
                  <span className="payment-option-icon" aria-hidden="true">{option.icon}</span>
                  <span>
                    <strong>{option.label}</strong>
                    <small>{option.detail}</small>
                  </span>
                </label>
              ))}
            </div>

            {paymentMethod === "visa" && (
              <div className="payment-demo-details">
                <p>VISA demo checkout. Use only the demo numbers below; never enter a real card.</p>
                <label>
                  Cardholder name
                  <input
                    type="text"
                    autoComplete="off"
                    value={paymentDetails.cardholder_name || ""}
                    onChange={(event) => setPaymentDetails((details) => ({ ...details, cardholder_name: event.target.value }))}
                  />
                </label>
                <label>
                  Demo card number
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="4242 4242 4242 4242"
                    value={paymentDetails.card_number || ""}
                    onChange={(event) => setPaymentDetails((details) => ({ ...details, card_number: event.target.value }))}
                  />
                </label>
                <div className="payment-demo-inline-fields">
                  <label>
                    Expiry (MM/YY)
                    <input
                      type="text"
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="12/30"
                      value={paymentDetails.expiry || ""}
                      onChange={(event) => setPaymentDetails((details) => ({ ...details, expiry: event.target.value }))}
                    />
                  </label>
                  <label>
                    Demo security code
                    <input
                      type="password"
                      inputMode="numeric"
                      autoComplete="off"
                      maxLength={3}
                      value={paymentDetails.security_code || ""}
                      onChange={(event) => setPaymentDetails((details) => ({ ...details, security_code: event.target.value }))}
                    />
                  </label>
                </div>
                <small>Success: 4242 4242 4242 4242 · Insufficient funds: 4000 0000 0000 9995 · Use any future expiry and 3-digit code.</small>
              </div>
            )}

            {(paymentMethod === "mycash" || paymentMethod === "mpaisa") && (
              <div className="payment-demo-details">
                <p>{paymentMethod === "mycash" ? "MyCash" : "M-PAiSA"} demo authorization; do not use a real PIN or one-time code.</p>
                <label>
                  Demo mobile number
                  <input
                    type="tel"
                    autoComplete="off"
                    placeholder="+679 9000000"
                    value={paymentDetails.phone_number || ""}
                    onChange={(event) => setPaymentDetails((details) => ({ ...details, phone_number: event.target.value }))}
                  />
                </label>
                <label>
                  Demo authorization code
                  <input
                    type="password"
                    inputMode="numeric"
                    autoComplete="off"
                    maxLength={6}
                    value={paymentDetails.authorization_code || ""}
                    onChange={(event) => setPaymentDetails((details) => ({ ...details, authorization_code: event.target.value }))}
                  />
                </label>
                <small>Success code: 123456 · Insufficient funds: 000000.</small>
              </div>
            )}

            {paymentMethod === "cash" && (
              <p className="auth-subtitle">This demo records a successful cash-on-handoff order. No real payment is taken.</p>
            )}

            <label className="payment-failure-toggle">
              <input
                type="checkbox"
                checked={forceFailure}
                onChange={(event) => {
                  setForceFailure(event.target.checked);
                  setPaymentError("");
                }}
              />
              <span>
                <strong>Force payment failure</strong>
                <small>Demo testing only — order will not be created and stock will not change.</small>
              </span>
            </label>
          </div>

          {paymentError && <p className="auth-message" role="alert">{paymentError}</p>}
          <div className="checkout-actions">
            <button type="button" className="secondary-button" onClick={() => setCheckoutStep("delivery")}>
              Back
            </button>
            <button type="button" className="auth-submit" onClick={handleCheckout} disabled={isSubmitting || !paymentMethod || !paymentDetailsComplete}>
              {isSubmitting ? "Processing payment..." : "Pay Now"}
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
              <span>Ready to reserve</span>
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
                    <button type="button" className="seller-inline-link" onClick={() => onViewSeller?.(item)}>
                      {item.seller_username}
                    </button>
                  </div>
                </div>
                <div className="cart-item-action">
                  <span>${Number(item.price).toFixed(2)}</span>
                  <small>{Number(item.stock) > 0 ? `${item.stock} in stock` : "Sold"}</small>
                  {Number(item.stock) > 1 && (
                    <div className="cart-quantity-control" aria-label={`Quantity for ${item.name}`}>
                      <button
                        type="button"
                        onClick={() => onQuantityChange(item.id, quantityFor(item) - 1)}
                        disabled={quantityFor(item) <= 1}
                        aria-label={`Decrease quantity for ${item.name}`}
                      >
                        -
                      </button>
                      <strong>{quantityFor(item)}</strong>
                      <button
                        type="button"
                        onClick={() => onQuantityChange(item.id, quantityFor(item) + 1)}
                        disabled={quantityFor(item) >= Number(item.stock)}
                        aria-label={`Increase quantity for ${item.name}`}
                      >
                        +
                      </button>
                    </div>
                  )}
                  {Number(item.stock) > 1 && <small>Line total ${lineTotalFor(item).toFixed(2)}</small>}
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
