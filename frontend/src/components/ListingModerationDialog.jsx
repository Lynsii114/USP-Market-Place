import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const reasons = {
  hide: [
    "The listing requires an administrative review before it can remain visible.",
    "The item description is incomplete or unclear. Please update the listing.",
    "The listing photos do not clearly show the item. Please provide accurate photos.",
    "A concern has been reported about this listing and is being investigated.",
  ],
  warn: [
    "The listing description contains incomplete or misleading information. Please correct it.",
    "The listing photos do not clearly represent the item. Please provide accurate photos.",
    "The listing contains inappropriate language. Please revise the wording.",
    "The listing appears to duplicate another advertisement. Please remove duplicate entries.",
  ],
  remove: [
    "The listing offers a prohibited or restricted item.",
    "The listing contains fraudulent or misleading information.",
    "The listing contains inappropriate or offensive content.",
    "The listing is a duplicate or spam advertisement.",
  ],
};

export default function ListingModerationDialog({ listing, action, onConfirm, onClose }) {
  const dialogRef = useRef(null);
  const reasonRef = useRef(null);
  const busyRef = useRef(false);
  const [suggestion, setSuggestion] = useState("");
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const removing = action === "remove";
  const hiding = action === "hide";
  const reasonLimit = hiding ? 255 : 500;
  const sellerEmail = listing.seller?.email;

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog.showModal();
    return () => { dialog.close(); if (previousFocus?.isConnected) previousFocus.focus(); };
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    if (busyRef.current || result) return;
    const cleanReason = reason.trim();
    if (cleanReason.length < 10 || cleanReason.length > reasonLimit) {
      setError(`Enter a reason between 10 and ${reasonLimit} characters.`);
      reasonRef.current?.focus();
      return;
    }
    if (!confirming) { setError(""); setConfirming(true); return; }
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      setResult(await onConfirm({ reason: cleanReason, confirmed: true, expected_status: listing.status }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to complete this listing action.");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  return createPortal(
    <dialog ref={dialogRef} className="student-action-dialog" aria-labelledby="listing-moderation-title" onCancel={(event) => { event.preventDefault(); if (!busyRef.current) onClose(); }}>
      <span className="section-kicker">Listing #{listing.id}</span>
      <h3 id="listing-moderation-title">{hiding ? (result ? "Listing hidden" : confirming ? "Confirm hiding this listing" : "Hide listing") : result ? (removing ? "Listing removal confirmed" : "Seller warning recorded") : confirming ? (removing ? "Confirm listing removal" : "Confirm seller warning") : (removing ? "Remove listing" : "Warn seller")}</h3>
      <p><strong>{listing.name}</strong><br />Seller: {listing.seller_username}</p>
      {result ? <>
        <p role="status">{hiding ? "The listing is hidden from other customers and cannot be purchased. An administrator can restore it after the concern has been resolved." : removing ? "The listing has been permanently deleted and cannot be restored. Existing order records have been retained." : "A formal warning has been recorded for this listing. Its availability has not changed."}</p>
        {!hiding && <p role={result.email_status === "failed" ? "alert" : "status"} className={result.email_status === "failed" ? "student-action-error" : "student-action-note"}>
          {result.email_status === "sent" ? `The formal email has been submitted for delivery to ${sellerEmail}.` : result.email_status === "console" ? "Email delivery is disabled in this environment. No email was sent to the seller." : result.email_status === "failed" ? "The action is complete, but the email could not be sent. Please contact the seller separately." : "Email delivery status is unavailable. Please verify before contacting the seller."}
        </p>}
        <button type="button" className="secondary-button" onClick={onClose}>Done</button>
      </> : <form onSubmit={submit} noValidate>
        <p>{hiding ? "Temporarily hide this listing from other customers and prevent purchases until an administrator restores it." : removing ? "Permanently delete this listing from the database. This cannot be undone. Existing order records will be retained." : "Send the seller a formal warning about this item. This action does not remove or hide the listing."}</p>
        {confirming ? <>
          <div className="student-action-note"><strong>{hiding ? "Reason for hiding this listing" : "Reason to include in the email"}</strong><p className="listing-moderation-reason">{reason.trim()}</p></div>
          {hiding ? <p>The seller will receive an in-app notification explaining your reason after you confirm.</p> : <p>A formal email identifying this listing and your reason will be sent to <strong>{sellerEmail}</strong> only after you confirm.</p>}
        </> : <>
          <label>Suggested reason
            <select autoFocus value={suggestion} onChange={(event) => { setSuggestion(event.target.value); setReason(event.target.value === "Other" ? "" : event.target.value); setError(""); }}>
              <option value="">Choose a suggested reason</option>
              {reasons[action].map((value) => <option key={value}>{value}</option>)}
              <option>Other</option>
            </select>
          </label>
          <label>Reason for {hiding ? "hiding the listing" : removing ? "removal" : "warning"} (required)
            <textarea ref={reasonRef} rows={4} minLength={10} maxLength={reasonLimit} required value={reason} onChange={(event) => { setReason(event.target.value); setError(""); }} aria-invalid={Boolean(error)} aria-describedby={error ? "listing-moderation-error" : "listing-moderation-help"} placeholder={hiding ? "Enter or edit the reason for hiding this listing." : "Enter or edit the reason to include in the seller's email."} />
          </label>
          <p id="listing-moderation-help" className="student-action-note">Use 10–{reasonLimit} characters. You can edit any suggested reason before continuing.</p>
        </>}
        {!hiding && !sellerEmail && <p role="alert" className="student-action-error">The seller's email address is unavailable. This action cannot be completed.</p>}
        {error && <p id="listing-moderation-error" role="alert" className="student-action-error">{error}</p>}
        <div className="notification-dismiss-actions">
          <button type="button" className="secondary-button" disabled={busy} onClick={() => confirming ? (setConfirming(false), setError("")) : onClose()}>{confirming ? "Back" : "Cancel"}</button>
          <button type="submit" className={removing ? "danger-outline-button" : "auth-submit"} disabled={busy || (!hiding && !sellerEmail)}>{busy ? "Processing…" : confirming ? (hiding ? "Confirm hide listing" : removing ? "Confirm permanent deletion and send email" : "Confirm warning and send email") : "Review confirmation"}</button>
        </div>
      </form>}
    </dialog>, document.body,
  );
}
