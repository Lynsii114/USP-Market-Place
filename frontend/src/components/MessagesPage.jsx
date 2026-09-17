import React, { useEffect, useMemo, useState } from "react";

function MessagesPage({
  conversations,
  currentUser,
  activeConversation,
  draftMessage,
  isLoading,
  isSubmitting,
  onBack,
  onLogin,
  onOpenConversation,
  onDraftChange,
  onSendMessage,
}) {
  const [search, setSearch] = useState("");

  const initialsFor = (name = "") =>
    name
      .split(/[\s_.-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("") || "?";

  const formatMessageTime = (value) => {
    if (!value) {
      return "";
    }

    return new Date(value).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const otherUserNameFor = (conversation) =>
    currentUser?.id === conversation.buyer_id
      ? conversation.seller_name || conversation.seller_username
      : conversation.buyer_name || conversation.buyer_username;

  const handleComposeKeyDown = (event) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    if (!isSubmitting && draftMessage.trim()) {
      event.currentTarget.form?.requestSubmit();
    }
  };

  useEffect(() => {
    if (!activeConversation && conversations.length) {
      onOpenConversation(conversations[0].id);
    }
  }, [activeConversation, conversations, onOpenConversation]);

  const filteredConversations = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return conversations;
    }

    return conversations.filter((conversation) => {
      const otherUser = otherUserNameFor(conversation);
      return (
        otherUser.toLowerCase().includes(query) ||
        (conversation.item_name || "General chat").toLowerCase().includes(query)
      );
    });
  }, [conversations, currentUser, search]);

  if (!currentUser) {
    return (
      <section className="messages-page" id="messages">
        <div className="messages-empty-panel">
          <span className="section-kicker">Messages</span>
          <h2>Login to view your chats</h2>
          <p>Buyers and sellers can message each other after signing in.</p>
          <button type="button" className="auth-submit" onClick={onLogin}>
            Login
          </button>
        </div>
      </section>
    );
  }

  const activeOtherUser =
    activeConversation && currentUser.id === activeConversation.buyer_id
      ? activeConversation.seller_name || activeConversation.seller_username
      : activeConversation?.buyer_name || activeConversation?.buyer_username;

  return (
    <section className="messages-page" id="messages">
      <div className="messages-header">
        <div className="section-heading">
          <span className="section-kicker">Messages</span>
          <h2>Chats</h2>
          <p>{conversations.length} {conversations.length === 1 ? "conversation" : "conversations"}</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onBack} aria-label="Close messages">
          x
        </button>
      </div>

      <div className="messages-shell">
        <aside className="conversation-list" aria-label="Conversation list">
          <div className="conversation-list-header">
            <strong>Inbox</strong>
            <span>{conversations.reduce((total, conversation) => total + Number(conversation.unread_count || 0), 0)} unread</span>
          </div>
          <label className="conversation-search">
            <span aria-hidden="true">&#128269;</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search chats"
              aria-label="Search chats"
            />
          </label>

          {isLoading ? (
            <p className="empty-state">Loading messages...</p>
          ) : filteredConversations.length ? (
            filteredConversations.map((conversation) => {
              const otherUser = otherUserNameFor(conversation);
              const isActive = activeConversation?.id === conversation.id;
              return (
                <button
                  type="button"
                  className={[
                    "conversation-item",
                    isActive ? "active" : "",
                    conversation.unread_count ? "unread" : "",
                  ].filter(Boolean).join(" ")}
                  key={conversation.id}
                  onClick={() => onOpenConversation(conversation.id)}
                >
                  <span className="conversation-avatar" aria-hidden="true">
                    {initialsFor(otherUser)}
                  </span>
                  <span className="conversation-preview">
                    <span className="conversation-topline">
                      <strong>{otherUser}</strong>
                      {conversation.latest_message?.created_at && (
                        <time>{formatMessageTime(conversation.latest_message.created_at)}</time>
                      )}
                    </span>
                    <span className="conversation-item-name">{conversation.item_name || "General chat"}</span>
                    <small>{conversation.latest_message?.body || "No messages yet"}</small>
                  </span>
                  {conversation.unread_count ? (
                    <span className="conversation-unread-count">{conversation.unread_count}</span>
                  ) : null}
                </button>
              );
            })
          ) : (
            <p className="empty-state">No chats yet.</p>
          )}
        </aside>

        <div className="message-thread">
          {activeConversation ? (
            <>
              <div className="thread-header">
                <span className="thread-avatar" aria-hidden="true">
                  {initialsFor(activeOtherUser)}
                </span>
                <div>
                  <strong>{activeOtherUser}</strong>
                  <span>{activeConversation.item_name || "General chat"}</span>
                </div>
              </div>

              <div className="thread-messages">
                {activeConversation.messages?.length ? (
                  activeConversation.messages.map((message) => (
                    <div
                      className={message.sender_id === currentUser.id ? "message-bubble mine" : "message-bubble"}
                      key={message.id}
                    >
                      <span className="message-meta">
                        <strong>{message.sender_name || message.sender_username}</strong>
                        <time>{formatMessageTime(message.created_at)}</time>
                      </span>
                      <p>{message.body}</p>
                      {message.sender_id === currentUser.id && (
                        <span
                          className={message.is_seen_by_recipient ? "message-status seen" : "message-status"}
                          aria-label={message.is_seen_by_recipient ? "Seen" : "Sent"}
                          title={message.is_seen_by_recipient ? "Seen" : "Sent"}
                        >
                          &#10003;&#10003;
                        </span>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="empty-state">Start the conversation with a message.</p>
                )}
              </div>

              <form className="message-compose" onSubmit={onSendMessage}>
                <textarea
                  value={draftMessage}
                  onChange={(event) => onDraftChange(event.target.value)}
                  onKeyDown={handleComposeKeyDown}
                  placeholder="Type your message"
                  rows="3"
                  maxLength="1000"
                  required
                />
                <div className="compose-actions">
                  <span>{draftMessage.length}/1000</span>
                  <button type="submit" className="auth-submit" disabled={isSubmitting || !draftMessage.trim()}>
                    {isSubmitting ? "Sending..." : "Send"}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <div className="messages-empty-panel">
              <span className="section-kicker">Inbox</span>
              <h2>Select a chat</h2>
              <p>Your buyer and seller messages will appear here.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default MessagesPage;
