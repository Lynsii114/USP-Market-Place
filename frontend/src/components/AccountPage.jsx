import React from "react";

function AccountPage({
  page,
  currentUser,
  myListings,
  purchaseHistory,
  conversations = [],
  activeConversationId,
  messageDraft,
  onConversationSelect,
  onViewConversationListing,
  onMessageDraftChange,
  onSendMessage,
  onBack,
}) {
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

  if (!pageContent && page !== "messages") {
    return null;
  }

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) || conversations[0];

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
