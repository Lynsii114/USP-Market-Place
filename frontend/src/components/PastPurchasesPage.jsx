import React from "react";

function PastPurchasesPage({ currentUser, purchases, onBack, onLogin }) {
  const totalSpent = purchases.reduce((total, purchase) => total + Number(purchase.price), 0);
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
            <div className="purchase-report-table-head">
              <span>Item</span>
              <span>Unit Cost</span>
              <span>Date &amp; Time</span>
            </div>
            <div className="purchase-report-list">
              {purchases.map((purchase) => (
                <div className="purchase-report-item" key={purchase.id}>
                  <div>
                    <strong>{purchase.item_name}</strong>
                    <small>{purchase.category}</small>
                  </div>
                  <div>
                    <span>${Number(purchase.price).toFixed(2)}</span>
                    <small>Seller: {purchase.seller_username}</small>
                  </div>
                  <time dateTime={purchase.purchased_at}>{formatPurchaseDate(purchase.purchased_at)}</time>
                </div>
              ))}
            </div>

            <div className="purchase-total-card">
              <div>
                <span>Total Amount</span>
                <strong>${totalSpent.toFixed(2)}</strong>
              </div>
            </div>
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
