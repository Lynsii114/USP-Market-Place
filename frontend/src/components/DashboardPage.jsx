import React from "react";

function DashboardPage({ currentUser, myListings, purchases, sellerOrders, isLoading, onBack, onManageListings }) {
  if (!currentUser) {
    return null;
  }

  const activeListings = myListings.filter((listing) => listing.status !== "sold" && Number(listing.stock) > 0);
  const formatDate = (value) =>
    value
      ? new Date(value).toLocaleString([], {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "Date unavailable";

  return (
    <main className="account-page dashboard-page">
      <div className="cart-header">
        <div className="section-heading">
          <span className="section-kicker">My Activity</span>
          <h2>My Dashboard</h2>
          <p>Your listings, purchases, and orders from other users.</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onBack} aria-label="Back to marketplace">
          x
        </button>
      </div>

      <div className="dashboard-summary">
        <div className="dashboard-summary-card">
          <span>Active Listings</span>
          <strong>{activeListings.length}</strong>
        </div>
        <div className="dashboard-summary-card">
          <span>My Purchases</span>
          <strong>{purchases.length}</strong>
        </div>
        <div className="dashboard-summary-card">
          <span>Orders on My Listings</span>
          <strong>{sellerOrders.length}</strong>
        </div>
      </div>

      {isLoading && <p className="dashboard-loading">Loading your activity...</p>}

      <section className="dashboard-section">
        <div className="dashboard-section-heading">
          <h3>My Listings</h3>
          <button type="button" className="secondary-button" onClick={onManageListings}>
            Manage Listings
          </button>
        </div>
        {myListings.length ? (
          <div className="dashboard-activity-list">
            {myListings.map((listing) => (
              <div className="dashboard-activity-row" key={listing.id}>
                <div>
                  <strong>{listing.name}</strong>
                  <span>{listing.category} · ${Number(listing.price).toFixed(2)}</span>
                </div>
                <span className="dashboard-activity-status">
                  {listing.status === "sold" || Number(listing.stock) <= 0 ? "Sold out" : `${listing.stock} in stock`}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">{isLoading ? "Loading listings..." : "You have not listed any items yet."}</p>
        )}
      </section>

      <section className="dashboard-section">
        <h3>Orders on My Listings</h3>
        {sellerOrders.length ? (
          <div className="dashboard-activity-list">
            {sellerOrders.map((order) => (
              <div className="dashboard-activity-row" key={order.id}>
                <div>
                  <strong>{order.item_name}</strong>
                  <span>Buyer: {order.buyer_username} · Qty {order.quantity || 1}</span>
                </div>
                <div className="dashboard-activity-meta">
                  <strong>${Number(order.total_amount || order.price).toFixed(2)}</strong>
                  <time dateTime={order.purchased_at}>{formatDate(order.purchased_at)}</time>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">{isLoading ? "Loading orders..." : "There are no orders on your listings yet."}</p>
        )}
      </section>

      <section className="dashboard-section">
        <h3>My Purchases</h3>
        {purchases.length ? (
          <div className="dashboard-activity-list">
            {purchases.map((purchase) => (
              <div className="dashboard-activity-row" key={purchase.id}>
                <div>
                  <strong>{purchase.item_name}</strong>
                  <span>Seller: {purchase.seller_username} · Qty {purchase.quantity || 1}</span>
                </div>
                <div className="dashboard-activity-meta">
                  <strong>${Number(purchase.total_amount || purchase.price).toFixed(2)}</strong>
                  <time dateTime={purchase.purchased_at}>{formatDate(purchase.purchased_at)}</time>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">{isLoading ? "Loading purchases..." : "You have not made any purchases yet."}</p>
        )}
      </section>
    </main>
  );
}

export default DashboardPage;
