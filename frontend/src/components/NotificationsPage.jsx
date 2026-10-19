import React, { useEffect, useState } from "react";

const PAGE_SIZE = 10;

export default function NotificationsPage({ notifications = [], onBack, onOpen, onRemove }) {
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(1);
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;
  const matching = filter === "unread"
    ? notifications.filter((notification) => !notification.is_read)
    : notifications;
  const pageCount = Math.max(1, Math.ceil(matching.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const firstIndex = (currentPage - 1) * PAGE_SIZE;
  const visible = matching.slice(firstIndex, firstIndex + PAGE_SIZE);
  const pageNumbers = [...new Set([1, currentPage - 1, currentPage, currentPage + 1, pageCount])]
    .filter((number) => number >= 1 && number <= pageCount)
    .sort((a, b) => a - b);

  useEffect(() => { setPage(1); }, [filter]);
  useEffect(() => { setPage((value) => Math.min(value, pageCount)); }, [pageCount]);

  return (
    <section className="notifications-page" aria-labelledby="notifications-heading">
      <div className="cart-header">
        <div className="section-heading">
          <h2 id="notifications-heading">Notifications</h2>
          <p>{unreadCount ? `${unreadCount} unread` : "You're all caught up"}</p>
        </div>
        {onBack && <button type="button" className="close-panel-button" onClick={onBack} aria-label="Close notifications">x</button>}
      </div>

      <div className="notification-page-toolbar">
        <div className="inventory-status-filters" role="group" aria-label="Filter notifications">
          <button type="button" className={filter === "all" ? "active" : ""} aria-pressed={filter === "all"} onClick={() => setFilter("all")}>All ({notifications.length})</button>
          <button type="button" className={filter === "unread" ? "active" : ""} aria-pressed={filter === "unread"} onClick={() => setFilter("unread")}>Unread ({unreadCount})</button>
        </div>
        {matching.length > 0 && <span className="notification-range">Showing {firstIndex + 1}–{Math.min(firstIndex + PAGE_SIZE, matching.length)} of {matching.length}</span>}
      </div>

      {visible.length ? (
        <div className="notification-page-list">
          {visible.map((notification) => (
            <article className={notification.is_read ? "notification-page-row viewed" : "notification-page-row unread"} key={notification.id}>
              <button type="button" className="notification-page-item" onClick={() => onOpen(notification)}>
                <span className="notification-page-title"><strong>{notification.title}</strong><small>{notification.is_read ? "Viewed" : "New"}</small></span>
                <span>{notification.message}</span>
                {notification.created_at && <time dateTime={notification.created_at}>{new Date(notification.created_at).toLocaleString()}</time>}
              </button>
              <button type="button" className="notification-remove-button" onClick={() => onRemove(notification.id)} aria-label={`Remove notification: ${notification.title}`}>x</button>
            </article>
          ))}
        </div>
      ) : <p className="empty-state">{filter === "unread" ? "No unread notifications." : "No notifications yet."}</p>}

      {pageCount > 1 && (
        <nav className="inventory-pagination" aria-label="Notification pages">
          <button type="button" className="secondary-button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Previous</button>
          {pageNumbers.map((number) => <button type="button" className="secondary-button" key={number} aria-label={`Page ${number}`} aria-current={number === currentPage ? "page" : undefined} onClick={() => setPage(number)}>{number}</button>)}
          <button type="button" className="secondary-button" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>Next</button>
        </nav>
      )}
    </section>
  );
}
