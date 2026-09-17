import React, { useEffect, useState } from "react";

function AccountPage({ page, currentUser, myListings, purchaseHistory, isSubmitting, onBack, onUpdateName }) {
  const [name, setName] = useState("");

  useEffect(() => {
    setName(currentUser?.name || "");
  }, [currentUser]);

  if (!page || !currentUser) {
    return null;
  }

  const soldListings = myListings.filter((listing) => listing.status === "sold" || Number(listing.stock) <= 0);

  const content = {
    profile: {
      kicker: "Profile",
      title: "My Profile",
      rows: [
        ["Name", currentUser.name || "Not set"],
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

      {page === "settings" && (
        <form
          className="account-settings-form"
          onSubmit={(event) => {
            event.preventDefault();
            onUpdateName(name);
          }}
        >
          <label>
            Name
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter your name"
              required
            />
          </label>
          <button type="submit" className="auth-submit" disabled={isSubmitting || name.trim() === currentUser.name}>
            {isSubmitting ? "Saving..." : "Save Name"}
          </button>
        </form>
      )}
    </section>
  );
}

export default AccountPage;
