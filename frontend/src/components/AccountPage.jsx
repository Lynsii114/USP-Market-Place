import React from "react";

function AccountPage({ page, currentUser, myListings, purchaseHistory, onBack }) {
  if (!page || !currentUser) {
    return null;
  }

  const soldListings = myListings.filter((listing) => listing.status === "sold" || Number(listing.stock) <= 0);

  const content = {
    profile: {
      kicker: "Profile",
      title: "My Profile",
      rows: [
        ["Username", currentUser.username],
        ["USP Email", currentUser.email],
      ],
    },
    sales: {
      kicker: "Seller Report",
      title: "My Sales",
      rows: [
        ["Active Listings", myListings.filter((listing) => listing.status !== "sold" && Number(listing.stock) > 0).length],
        ["Sold Out Listings", soldListings.length],
      ],
    },
    settings: {
      kicker: "Account",
      title: "Settings",
      rows: [
        ["Account Type", "USP Student"],
        ["Purchase Records", `${purchaseHistory.length} saved`],
      ],
    },
  };
  const pageContent = content[page];

  if (!pageContent) {
    return null;
  }

  return (
    <section className="account-page">
      <div className="cart-header">
        <div className="section-heading">
          <span className="section-kicker">{pageContent.kicker}</span>
          <h2>{pageContent.title}</h2>
          <p>Account information for your USP Buy & Sell activity.</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onBack} aria-label="Close account page">
          x
        </button>
      </div>

      <div className="account-info-card">
        {pageContent.rows.map(([label, value]) => (
          <div className="account-info-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export default AccountPage;
