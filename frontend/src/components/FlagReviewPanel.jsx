import SearchInput from "./SearchInput";
import { searchRecords } from "../utils/search.mjs";
import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const statuses = { open: "Pending", warned: "Warning issued", deleted: "Listing deleted" };
const statusKey = (report) => report.status === "warned" || report.status === "deleted" ? report.status : "open";
const suggestions = {
  warning: ["Please correct misleading information in your listing.", "Please use appropriate language and communicate respectfully.", "Please review the marketplace rules before continuing to sell.", "Please provide accurate photos and a clear item description."],
  delete: ["This listing contains a prohibited or restricted item.", "This listing contains fraudulent or misleading information.", "This listing contains inappropriate content.", "This listing is a duplicate or spam advertisement."],
};
const date = (value) => value ? new Date(value).toLocaleString() : "Not recorded";

function ListingPhoto({ photo, name }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [photo]);
  return photo && !failed
    ? <img src={photo} alt={name || "Flagged listing"} loading="lazy" onError={() => setFailed(true)} />
    : <div className="flag-photo-placeholder">{failed ? "Photo unavailable" : "No photo recorded"}</div>;
}

function ReviewDialog({ report, onClose, onSave, onViewUser }) {
  const dialogRef = useRef(null);
  const busyRef = useRef(false);
  const [action, setAction] = useState("");
  const [reason, setReason] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const snapshot = report.listing_snapshot?.id ? report.listing_snapshot : null;
  const listing = snapshot || report.target_item;
  const photo = listing?.photo || report.target_item?.photo;
  const canWarn = report.email_status !== "pending" && Boolean(report.seller?.email) && !["warned", "deleted"].includes(report.status);
  const canDelete = report.email_status !== "pending" && Boolean(report.seller?.email && report.target_item) && report.target_item.status !== "removed" && report.status !== "deleted";

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog.showModal();
    return () => { dialog.close(); if (previousFocus?.isConnected) previousFocus.focus(); };
  }, []);

  const save = async (event) => {
    event.preventDefault();
    if (busyRef.current) return;
    if (!confirming) { setConfirming(true); return; }
    busyRef.current = true;
    setSaving(true);
    setError("");
    try {
      const data = await onSave(report, { action, reason: reason.trim(), expected_status: report.status });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to complete this action.");
    } finally { busyRef.current = false; setSaving(false); }
  };

  const viewUser = (user) => { onClose(); onViewUser(user); };
  return createPortal(
    <dialog ref={dialogRef} className="flag-review-dialog" aria-labelledby="flag-review-title" onCancel={(event) => { event.preventDefault(); if (!busyRef.current) onClose(); }}>
      <div className="flag-review-heading">
        <div><span className="section-kicker">Report #{report.id} · {report.target_type === "user" ? "Seller concern" : "Listing concern"}</span><h3 id="flag-review-title">Review flagged {report.target_type === "user" ? "seller" : "listing"}</h3></div>
        <button type="button" className="secondary-button" autoFocus disabled={saving} onClick={onClose}>Close</button>
      </div>
      <div className="flag-review-body">
      {confirming || result ? <div className="flag-confirm-listing"><ListingPhoto photo={photo} name={listing?.name} /><div><strong>{listing?.name || report.target_label}</strong><p>Report #{report.id}{report.listing_id ? ` · Listing #${report.listing_id}` : ""}</p><span>Seller: {report.seller?.username || listing?.seller_username || "Unavailable"}</span></div></div> : <div className="flag-review-overview">
      <section className="flag-review-section flag-submitted-report">
        <h4>Submitted report</h4>
        <dl className="flag-review-meta">
          <dt>Reporter</dt><dd>{report.reporter ? <button type="button" className="profile-name-button" disabled={saving} onClick={() => viewUser(report.reporter)}>{report.reporter.username} · View profile</button> : `${report.reporter_username} (account unavailable)`}</dd>
          <dt>Reported on</dt><dd>{date(report.created_at)}</dd>
          <dt>Reason</dt><dd className="flag-report-reason">{report.reason}</dd>
          <dt>Seller</dt><dd>{report.seller ? <button type="button" className="profile-name-button" disabled={saving} onClick={() => viewUser(report.seller)}>{report.seller.username} · View profile</button> : listing?.seller_username || report.target_label || "Account unavailable"}</dd>
        </dl>
      </section>
      <section className="flag-review-section">
        <h4>{snapshot ? "Listing at the time of report" : "Linked listing"}</h4>
        {listing ? <>
          <div className="flag-listing-evidence">
            <ListingPhoto photo={photo} name={listing.name} />
            <div><strong>{listing.name}</strong><p>Listing #{report.listing_id || listing.id} · {listing.category}</p><p>${Number(listing.price).toFixed(2)} · {listing.stock} in stock</p><p className="flag-preserve-lines">{listing.description}</p></div>
          </div>
          {!snapshot && <p className="flag-review-note">This older report has no saved snapshot. These are the listing’s current details.</p>}
          {snapshot && !snapshot.photo && report.target_item?.photo && <p className="flag-review-note">No original photo was recorded; showing the current listing photo.</p>}
          <p className="flag-review-note">{report.target_item?.status === "removed" ? "This listing has been deleted from the marketplace. Saved evidence remains available." : report.target_item ? `Current listing status: ${report.target_item.status}.` : "The listing is no longer available. Saved evidence remains available."}</p>
        </> : <p className="flag-review-note">{report.listing_id ? `Listing #${report.listing_id} is no longer available and no snapshot was saved for this older report.` : "No listing was linked to this older seller report. Review the submitted reason and seller profile."}</p>}
      </section>
      </div>}
      {result ? <section className="flag-review-section">
        <h4>{action === "delete" ? "Listing deleted" : "Warning issued"}</h4>
        <p role="status" className={result.email_status === "failed" ? "student-action-error" : ""}>{result.message}</p>
        <button type="button" className="secondary-button" onClick={onClose}>Done</button>
      </section> : <form onSubmit={save} className="flag-review-form">
        <h4>{confirming ? "Confirm action" : "Choose an action"}</h4>
        {report.reviewed_at && <p className="flag-review-note">Last action by {report.reviewed_by_username || "an administrator"} on {date(report.reviewed_at)}. {report.review_notes ? `Reason: ${report.review_notes}` : ""}{report.email_status ? ` Email: ${report.email_status}.` : ""}</p>}
        {confirming ? <>
          <p><strong>{action === "delete" ? "Delete listing" : "Send warning"}</strong> for {listing?.name || report.target_label}.</p>
          <p className="flag-preserve-lines">{reason}</p>
          <p className="flag-review-note">The message will be emailed to <strong>{report.seller?.email}</strong>. {action === "delete" ? "The listing will be removed from the marketplace. Report evidence and existing order records are kept." : "The listing will remain available."}</p>
        </> : <>
          <div className="flag-action-options" role="group" aria-label="Flag action">
            <button type="button" aria-pressed={action === "warning"} disabled={saving || !canWarn} onClick={() => { setAction("warning"); setReason(""); setSuggestion(""); }}><strong>Send warning</strong><span>Email the seller a warning. Keep the listing.</span></button>
            <button type="button" aria-pressed={action === "delete"} disabled={saving || !canDelete} onClick={() => { setAction("delete"); setReason(""); setSuggestion(""); }}><strong>Delete listing</strong><span>Remove the listing and email the seller.</span></button>
          </div>
          {!report.seller?.email && <p className="flag-review-note">The seller account is unavailable, so an email action cannot be performed.</p>}
          {report.email_status === "pending" && <p className="flag-review-note">An email action is still processing. Close this panel and refresh the flags before taking another action.</p>}
          {report.status === "warned" && <p className="flag-review-note">A warning has already been issued. You can delete the listing if further action is needed.</p>}
          {(!report.target_item || report.target_item.status === "removed" || report.status === "deleted") && <p className="flag-review-note">This listing is unavailable or already deleted. It cannot be deleted again.</p>}
          {action && <>
            <label>Suggested reason<select value={suggestion} disabled={saving} onChange={(event) => { setSuggestion(event.target.value); setReason(event.target.value === "Other" ? "" : event.target.value); }}><option value="">Choose a reason</option>{suggestions[action].map((value) => <option key={value}>{value}</option>)}<option>Other</option></select></label>
            <label>Message sent to the seller<textarea rows={3} maxLength={500} minLength={10} required value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} placeholder="Explain the reason clearly (10-500 characters)." /></label>
            <p className="flag-review-note">This message will be included in the seller's email and in-app notification.</p>
          </>}
        </>}
        {error && <p role="alert" className="student-action-error">{error}</p>}
        <div className="notification-dismiss-actions"><button type="button" className="secondary-button" disabled={saving} onClick={() => confirming ? setConfirming(false) : onClose()}>{confirming ? "Back" : "Cancel"}</button><button type="submit" className={action === "delete" ? "danger-outline-button" : "auth-submit"} disabled={saving || !action || reason.trim().length < 10}>{saving ? "Processing..." : confirming ? (action === "delete" ? "Confirm deletion" : "Confirm warning") : "Review action"}</button></div>
      </form>}

      </div>

    </dialog>, document.body
  );
}

export default function FlagReviewPanel({ reports, onSave, onViewUser, onRefresh }) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState("");
  const filtered = searchRecords(reports, query, (record) => [record.listing_snapshot?.name, record.target_item?.name, record.target_label, record.id, record.listing_id, record.reporter_username, record.seller?.username, record.reason, statuses[statusKey(record)]]).filter((record) => filter === "all" || statusKey(record) === filter);

  return <div className="admin-table-card flag-review-panel">
    <div className="admin-section-toolbar"><div><p className="flag-review-note">Review the listing and report, then send a warning or delete the listing.</p></div><button type="button" className="secondary-button" disabled={refreshing} onClick={async () => { setRefreshing(true); setRefreshError(""); try { await onRefresh(); } catch (err) { setRefreshError(err.message || "Unable to refresh reports."); } finally { setRefreshing(false); } }}>{refreshing ? "Refreshing…" : "Refresh"}</button></div>
    <div className="flag-summary">{Object.entries(statuses).map(([key, label]) => <button type="button" key={key} aria-pressed={filter === key} onClick={() => { setFilter(filter === key ? "all" : key); }}><strong>{reports.filter((r) => statusKey(r) === key).length}</strong><span>{label}</span></button>)}</div>
    <div className="flag-filters"><label>Search reports<SearchInput value={query} onChange={(value) => { setQuery(value); }} label="Search flags" placeholder="Listing, ID, reporter, seller or reason" /></label><label>Status<select value={filter} onChange={(event) => { setFilter(event.target.value); }}><option value="all">All statuses</option>{Object.entries(statuses).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label></div>
    {refreshError && <p role="alert" className="student-action-error">{refreshError}</p>}
    <p className="flag-results-status" role="status">Showing all {filtered.length} matching {filtered.length === 1 ? "report" : "reports"}</p>
    <div className="flag-report-list">{filtered.length ? filtered.map((record) => {
      const listing = record.listing_snapshot?.id ? record.listing_snapshot : record.target_item;
      return <article className="flag-report-card" key={record.id}>
        <ListingPhoto photo={listing?.photo || record.target_item?.photo} name={listing?.name} />
        <div className="flag-report-card-content">
          <div className="flag-card-title"><strong>{listing?.name || record.target_label}</strong><span className={`status-pill ${statusKey(record)}`}>{statuses[statusKey(record)]}</span></div>
          <p className="flag-review-note">Report #{record.id}{record.listing_id ? ` | Listing #${record.listing_id}` : ""}</p>
          <dl className="flag-card-accounts">
            <dt>Seller</dt><dd>{record.seller ? <button type="button" className="profile-name-button" onClick={() => onViewUser(record.seller)}>{record.seller.username}</button> : listing?.seller_username || "Unavailable"}</dd>
            <dt>Reporter</dt><dd>{record.reporter ? <button type="button" className="profile-name-button" onClick={() => onViewUser(record.reporter)}>{record.reporter.username}</button> : record.reporter_username}</dd>
          </dl>
          <p className="flag-reason-preview">{record.reason}</p>
          <p className="flag-review-note">{date(record.created_at)}</p>
          {record.email_status && <p className={record.email_status === "failed" ? "student-action-error" : "flag-review-note"}>Email: {record.email_status === "sent" ? "accepted by provider" : record.email_status === "console" ? "local preview only" : record.email_status}</p>}
        </div>
        <button type="button" className="secondary-button flag-details-button" aria-label={`View details for report ${record.id}: ${listing?.name || record.target_label}`} onClick={() => setSelected(record)}>View report details <span aria-hidden="true">&rarr;</span></button>
      </article>;
    }) : <p className="empty-state">{reports.length ? "No reports match these filters." : "No flagged listings or sellers yet."}</p>}</div>

    {selected && <ReviewDialog report={selected} onClose={() => setSelected(null)} onSave={onSave} onViewUser={onViewUser} />}
  </div>;
}
