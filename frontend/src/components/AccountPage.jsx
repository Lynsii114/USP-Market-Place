import React, { useEffect, useState } from "react";

function AccountPage({
  page,
  currentUser,
  myListings,
  purchaseHistory,
  sellerOrders = [],
  activeSalesView = "active",
  conversations = [],
  activeConversationId,
  messageDraft,
  onConversationSelect,
  onViewConversationListing,
  onMessageDraftChange,
  onSendMessage,
  onBack,
}) {
  const [salesFilter, setSalesFilter] = useState("active");

  useEffect(() => {
    if (page === "sales") {
      setSalesFilter(activeSalesView);
    }
  }, [activeSalesView, page]);

  if (!page || !currentUser) {
    return null;
  }

  const soldListings = myListings.filter((listing) => listing.status === "sold" || Number(listing.stock) <= 0);
  const activeListings = myListings.filter((listing) => listing.status !== "sold" && Number(listing.stock) > 0);
  const salesHistory = sellerOrders;

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
        ["Active Listings", activeListings.length, "active"],
        ["Sold Out Listings", soldListings.length, "sold"],
        ["Sales History", salesHistory.length, "history"],
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

  if (!pageContent && page !== "messages") {
    return null;
  }

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) || conversations[0];
  const selectedSalesListings = salesFilter === "sold" ? soldListings : activeListings;
  const formatOrderDate = (value) => {
    if (!value) {
      return "Date unavailable";
    }
    return new Date(value).toLocaleString();
  };
  const handleMessageKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (messageDraft.trim()) {
        onSendMessage();
      }
    }
  };

  if (page === "messages") {
    return (
      <section className="account-page messages-page">
        <div className="cart-header">
          <div className="section-heading">
            <h2>Messages</h2>
          </div>
          <button type="button" className="close-panel-button" onClick={onBack} aria-label="Close messages">
            x
          </button>
        </div>

        {conversations.length ? (
          <div className="messages-layout">
            <div className="conversation-list">
              {conversations.map((conversation) => (
                <button
                  type="button"
                  className={activeConversation?.id === conversation.id ? "conversation-card active" : "conversation-card"}
                  onClick={() => onConversationSelect(conversation.id)}
                  key={conversation.id}
                >
                  <strong>{conversation.item?.name || "Listing"}</strong>
                  <span>
                    {conversation.buyer_id === currentUser.id
                      ? conversation.seller_username
                      : conversation.buyer_username}
                  </span>
                  {conversation.unread_count > 0 && <small>{conversation.unread_count} unread</small>}
                </button>
              ))}
            </div>

            {activeConversation && (
              <div className="conversation-thread">
                <div className="conversation-product">
                  <div className="conversation-product-image">
                    {activeConversation.item?.photo ? (
                      <img src={activeConversation.item.photo} alt={activeConversation.item.name} />
                    ) : (
                      <span>{activeConversation.item?.category || "Item"}</span>
                    )}
                  </div>
                  <div>
                    <strong>{activeConversation.item?.name}</strong>
                    <span>${Number(activeConversation.item?.price || 0).toFixed(2)}</span>
                    <small>{activeConversation.item?.status || "available"}</small>
                  </div>
                  <button type="button" className="text-link-button" onClick={() => onViewConversationListing(activeConversation.item)}>
                    View Listing
                  </button>
                </div>

                <div className="message-history">
                  {activeConversation.messages.length ? (
                    activeConversation.messages.map((message) => {
                      const isMine = message.sender_id === currentUser.id;
                      const senderName =
                        message.sender_id === activeConversation.buyer_id
                          ? activeConversation.buyer_username
                          : activeConversation.seller_username;
                      const receiverName =
                        message.receiver_id === activeConversation.buyer_id
                          ? activeConversation.buyer_username
                          : activeConversation.seller_username;
                      return (
                        <div className={isMine ? "message-bubble mine" : "message-bubble"} key={message.id}>
                          <strong>
                            {isMine ? "You" : senderName} to {message.receiver_id === currentUser.id ? "you" : receiverName}
                          </strong>
                          <p>{message.body}</p>
                          <small>
                            {new Date(message.created_at).toLocaleString()} - {message.is_read ? "Read" : "Unread"}
                          </small>
                        </div>
                      );
                    })
                  ) : null}
                </div>

                <div className="message-composer">
                  <textarea
                    value={messageDraft}
                    onChange={(event) => onMessageDraftChange(event.target.value)}
                    onKeyDown={handleMessageKeyDown}
                    placeholder="Write a message about this item"
                    rows="3"
                  />
                  <button type="button" className="auth-submit" onClick={onSendMessage} disabled={!messageDraft.trim()}>
                    Send Message
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="empty-state">No product conversations yet.</p>
        )}
      </section>
    );
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
        {pageContent.rows.map(([label, value, target]) =>
          page === "sales" ? (
            <button
              type="button"
              className={salesFilter === target ? "account-info-row account-info-button active" : "account-info-row account-info-button"}
              onClick={() => setSalesFilter(target)}
              key={label}
            >
              <span>{label}</span>
              <strong>{value}</strong>
            </button>
          ) : (
            <div className="account-info-row" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          )
        )}
      </div>

      {page === "sales" && (
        <div className="sales-list-panel">
          <h3>
            {salesFilter === "history"
              ? "Sales History"
              : salesFilter === "sold"
                ? "Sold Out Listings"
                : "Active Listings"}
          </h3>
          {salesFilter === "history" ? (
            salesHistory.length ? (
              <div className="sales-list">
                {salesHistory.map((order) => (
                  <div className="sales-list-item sales-history-item" key={order.id}>
                    <div>
                      <strong>{order.item_name}</strong>
                      <span>
                        Buyer: {order.buyer_username} - {order.quantity || 1} sold
                      </span>
                    </div>
                    <div>
                      <strong>${Number(order.total_amount || order.price).toFixed(2)}</strong>
                      <span>{formatOrderDate(order.purchased_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">No sales history yet.</p>
            )
          ) : selectedSalesListings.length ? (
            <div className="sales-list">
              {selectedSalesListings.map((listing) => (
                <button type="button" className="sales-list-item" onClick={() => onViewConversationListing(listing)} key={listing.id}>
                  <div>
                    <strong>{listing.name}</strong>
                    <span>{listing.category}</span>
                  </div>
                  <div>
                    <strong>${Number(listing.price).toFixed(2)}</strong>
                    <span>{listing.status === "sold" || Number(listing.stock) <= 0 ? "Sold out" : `${listing.stock} in stock`}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="empty-state">No {salesFilter === "sold" ? "sold out" : "active"} listings found.</p>
          )}
        </div>
      )}
    </section>
  );
}

export default AccountPage;
